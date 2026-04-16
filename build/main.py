from fastapi import FastAPI, File, UploadFile, HTTPException
import onnxruntime as ort
import time
import cv2
import numpy as np
import base64
import httpx  # 使用 httpx 替代默认的 openai 同步调用
import os
from logstash_utils import Logger
logger = Logger(__name__)

app = FastAPI()

# ---------------------------------------------------------
# 1. 模型加载优化：开启 CUDA 显存管理
# ---------------------------------------------------------
# os.environ["CUDA_VISIBLE_DEVICES"] = "1"


def get_session():
    # 限制显存，防止 OOM
    cuda_options = {
        "device_id": 0,
        "gpu_mem_limit": 1 * 1024 * 1024 * 1024,  # 限制为 1GB
        "arena_extend_strategy": "kSameAsRequested",
    }

    # 开启推理并行优化
    options = ort.SessionOptions()
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    options.intra_op_num_threads = 4  # 调整为核心数的一半左右

    try:
        # 优先使用 CUDA，失败则回退 CPU
        sess = ort.InferenceSession(
            "east_model.onnx",
            sess_options=options,
            providers=[("CUDAExecutionProvider", cuda_options), "CPUExecutionProvider"]
        )
        return sess
    except Exception as e:
        logger.error(f"CUDA 加载失败，回退 CPU: {e}")
        return ort.InferenceSession("east_model.onnx", sess_options=options, providers=["CPUExecutionProvider"])


session = get_session()
input_name = session.get_inputs()[0].name

# ---------------------------------------------------------
# 2. 异步 API 调用 (避免阻塞)
# ---------------------------------------------------------
# 使用异步 Client 提升并发处理能力
import openai

async_client = openai.AsyncOpenAI(
    api_key="null",
    base_url="http://192.168.1.193:8118/v1"
)


async def response_paddleocrvl_async(image_b64, filename):
    try:
        response = await async_client.chat.completions.create(
            model="PaddleOCR-VL-1.5-0.9B",
            messages=[{
                'role': 'user',
                'content': [
                    {'type': 'image_url', 'image_url': {'url': f"data:image/jpeg;base64,{image_b64}"}},
                    {'type': 'text', 'text': 'OCR:请逐行识别图片中的文字'}
                ]
            }],
            temperature=0,
            max_tokens=512,
            frequency_penalty=0.1,
            top_p=0.9,
            stop=['根据图像内容', '请提供源文件图像', '根据图片内容', '根据图片中的文字', '识别后', '识别结果', '识别文字后'],
        )
        content = response.choices[0].message.content
        finish_reason = response.choices[0].finish_reason
        if finish_reason == 'length':
            logger.info("image:{},content:{}".format(filename, content))
        elif finish_reason == "abort":
            logger.error("image:{},content:abort".format(filename))
        return {"content": content}
    except Exception as e:
        logger.error(f"API Error: {e}")
        return {"content": "", "error": str(e)}


# ---------------------------------------------------------
# 3. 极速推理路由
# ---------------------------------------------------------
@app.post("/ocr_pipeline")
async def detect_text(file: UploadFile = File(...)):
    start_time = time.perf_counter()
    filename = file.filename
    try:
        # A. 快速读取与预处理
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image")

        # B. 减少内存拷贝的预处理
        # 直接使用 blobFromImage 的底层实现，避免多次 transpose
        blob = cv2.dnn.blobFromImage(img, 1.0, (640, 640), (123.68, 116.78, 103.94), swapRB=True)
        # 针对 TF 模型的 NHWC 格式：
        blob = np.transpose(blob, (0, 2, 3, 1)).astype(np.float32)

        # C. 执行推理
        outputs = session.run(None, {input_name: blob})

        # D. 判定逻辑优化 (不转置整个 geometry 图，只拿 scores)
        # scores 形状一般是 [1, 160, 160, 1]
        score_map = outputs[0][0, :, :, 0]

        # 使用 numpy 原生加速判定
        # has_text = np.any(score_map > 0.5)  # 只要存在高置信度区域即判定为有文字
        text_pixel_count = int(np.count_nonzero(score_map > 0.5))

        has_text = text_pixel_count > 50

        latency_ms = (time.perf_counter() - start_time) * 1000
        # logger.info(f"EAST 推理耗时: {latency_ms:.2f}ms, 是否有文字: {has_text}")

        if has_text:
            file_data = base64.b64encode(contents).decode("ascii")
            return await response_paddleocrvl_async(file_data,filename)

        logger.info("image:{},content:{}".format(filename, has_text))
        return {"content": ""}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    # 注意：使用 GPU 推理时，workers 建议设为 1，利用异步处理并发
    uvicorn.run(app, host="0.0.0.0", port=8082, workers=1)