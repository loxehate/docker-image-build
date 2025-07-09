import html
import json
import os
import stat
import time
import logger
from zipfile import ZipFile


def keep_dir(path_dir):
    """
    检测文件夹存在并自动创建文件夹 -- pass
    :param path_dir: 路径
    """
    path_exist = os.path.exists(path_dir)
    path_is_dir = os.path.isdir(path_dir)
    if not path_exist:
        # path_exist == False
        os.makedirs(path_dir)
    elif not path_is_dir:
        os.remove(path_dir)
        os.makedirs(path_dir)


def make_random():
    """
    生成基于时间戳的字符串 -- pass
    :return: 字符串
    """
    time_num = time.time()
    time_str = str(time_num).replace('.', '_')
    return time_str


def make_response(success=True, error_code="", error_msg=""):
    """
    生成接口返回值结构
    :param success: 是否成功(True/False)
    :param error_code: 错误代码
    :param error_msg: 错误详情
    :return: json 字符串
    """
    dic = dict(success=success, errorCode=error_code, errorMsg=error_msg)
    return dic
    # return json.dumps(dic, ensure_ascii=False)


def clean_field(dest_path, unpack_dir=""):
    """
    打扫战场
    :param dest_path: zip包
    :param unpack_dir: 文件夹
    :return:
    """
    if unpack_dir.strip():
        rmtree(unpack_dir)
    os.remove(dest_path)


def rmtree(top):
    """
    删除非空文件夹 - 确认
    :param top:
    :return:
    """
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            filename = os.path.join(root, name)
            os.chmod(filename, stat.S_IWUSR)
            os.remove(filename)
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(top)


def unzip(src, dest):
    """
    解压zip包 -- pass 2.27mb in 0.034
    :param src: 原位置(全路径)
    :param dest: 目标位置(全路径)
    :return: 解压结果(true/false)
    """
    global zf
    try:
        zf = ZipFile(src, 'r')
        zf.extractall(dest)
    except IOError:
        zf.close()
        return "false"
    else:
        zf.close()
        return "true"


def file_extension(path):
    """
    获取文件扩展名 -- pass
    :param path: 文件全路径
    :return: 带点的扩展名（如 .docx）
    """
    return os.path.splitext(path)[1]


def get_file_name(path):
    return os.path.splitext(path)[0]


def file_exist(path):
    return os.path.exists(path)


def get_files_in_dir(path):
    """
    取得文件夹下所有的文件（过滤子文件夹）
    :param path: 全路径
    :return: 子文件列表,如["123.jpg"]
    """
    item_list = os.listdir(path)
    for item in item_list:
        if os.path.isdir(item):
            item_list.remove(item)
    return item_list


def read_file_to_json(file_name):
    """
    读取数据文本文件，并转换为JSON对象
    :param file_name: 全路径
    :return: JSON对象(dict)
    """
    context_object = {}
    exists = os.path.exists(file_name)  # 文件是否存在
    if exists is True:
        fd = os.open(file_name, os.O_RDONLY)
        ret = os.read(fd, 1024)
        data_bytes = bytearray(ret)

        while len(ret) > 0:
            ret = os.read(fd, 1024)
            data_bytes[len(data_bytes):len(ret)] = bytearray(ret)
        # print(data_bytes.decode('utf8'))
        os.close(fd)
        context_object = json.loads(data_bytes)
        temp_str = json.dumps(context_object)
        temp_str = html.escape(temp_str, False)
        context_object = json.loads(temp_str)
    return context_object


def save_bytes_io(dest, bytes_io):
    """
    将 bytes_io(文件流)保存为指定路径文件
    :param dest: 指定目标输出路径
    :param bytes_io: 文件流
    :return: 目标输出路径
    """
    file_obj = open(dest, 'wb')
    file_obj.write(bytes_io.getvalue())
    file_obj.close()
    return dest


def save_str(dest, string):
    """
    将字符串保存为指定路径文件
    :param dest: 指定目标输出路径
    :param string: 字符串
    :return: 目标输出路径
    """
    file_obj = open(dest, 'wb')
    file_obj.write(string.encode('utf-8'))
    file_obj.close()
    return dest


def save_json(dest, dict_val):
    """
    将字典/json保存为指定路径文件

    :param dest: 指定目标输出路径
    :param dict_val: 字典类型
    :return: 目标输出路径
    """
    file_obj = open(dest, 'wb')
    file_obj.write(bytes(json.dumps(dict_val).encode('utf-8')))
    file_obj.close()
    return dest


def to_pdf(src, dest):
    """
    [停用]
    调用PDF转换功能 -- pass 847kb in 8-9s for 461kb
    :param src: 原文档全路径
    :param dest: 目标文档全路径
    :return: 转换处理结果
    """
    return "false"


def recurse(data):
    """
    测试 - 工具类 ，json(dist) 值过滤器 -- pass
    会打印 每对Key和Value
    :param data: json / dist
    :return: 无返
    """
    for element in data:
        if type(element) is list or type(element) is dict:
            recurse(element)
        else:
            if type(data[element]) is list or type(data[element]) is dict:
                recurse(data[element])
            else:
                print(element + "__" + data[element])
        pass

def write_log(error_code, error_msg, status_code, request, start):
    """
    输出日志
    :param error_code: 错误码
    :param error_msg: 错误信息
    :param status_code: 状态码
    :param request: 请求对象
    :param start: 开始时间
    """
    elapsed = (time.clock() - start)  # 间隔秒数
    elapsed_ms = f"{int(elapsed * 1000)}ms"

    lg = logger.LoggerModule('general').get_logger()
    lg.info("{0} - {1}".format(error_code, error_msg))
    # 代码 - 信息
    la = logger.LoggerModule('access').get_logger()
    la.info("remote_addr:{0};request:{1} {2};request_time:{3};status:{4};"
            .format(request.remote_addr, request.method, request.path, elapsed_ms, status_code)
            )
    # remote_addr:{请求IP};request:{请求方式} {访问路径};request_time:{处理耗时}ms;status:{状态码};
