import io
import time

from flask import Flask, request, send_file
from werkzeug.utils import secure_filename
import logging
import makedoc
import utility
from disable_logging import disable_logging

app = Flask(__name__)


@app.route("/makeDoc", methods=['POST'])
@disable_logging
def tpl_test():
    start = time.clock()
    utility.keep_dir("temp")
    """
    模板生成接口
    :return: file stream —— word
    """

    # 接收提交的文件
    file_obj = request.files.get('file')
    if file_obj:
        # 获取文件名
        src_name = secure_filename(file_obj.filename)
        if len(src_name) == 0:
            utility.write_log("File_Error", "File Name Unsecure", 500, request, start)
            return utility.make_response(False, "File_Error", "文件名不合理"), 500
        elif not src_name.endswith('.zip'):
            utility.write_log("File_Error", "File Type Error", 500, request, start)
            return utility.make_response(False, "File_Error", "文件类型错误"), 500
        # log
        # app.logger.info("get file " + src_name)
        # 目标存储路径(临时文件夹下)
        dest_path = "temp/" + src_name
        # 保存目标文件
        file_obj.save(dest_path)
        # 获取文件名
        dest_name = utility.get_file_name(dest_path)
        # 解压文件
        unzip_res = utility.unzip(dest_path, "temp/")
        if unzip_res == "false":
            # E 解压失败
            utility.clean_field(dest_path)
            utility.write_log("Unzip_Error", "File Unzip Error", 500, request, start)
            return utility.make_response(False, "Unzip_Error", "文件解压失败"), 500
        else:
            # 确认解压成功,获取模板文件位置
            unpack_dir = dest_name
            template_dir = unpack_dir + "/template/"
            template_list = utility.get_files_in_dir(template_dir)
            for t_item in template_list:
                if t_item[0:1] == "~$":
                    template_list.remove(t_item)
            if len(template_list) >= 1:
                # 判断模板文件是否存在
                template_name = template_list[0]
                template_path = template_dir + template_name
                output_path = io.BytesIO()
                # 这里面将 输出文件设置为文件流
                data_path = unpack_dir + "/data.json"
                if utility.file_exist(data_path):
                    pic_path = unpack_dir + "/img/"
                    rank_sum = utility.make_random()
                    output_name = rank_sum+".docx"
                    # temp_path 获取临时路径（测试代码）
                    # 判断数据文件是否存在
                    build_data = utility.read_file_to_json(data_path)
                    # 缓存模板数据
                    # utility.keep_dir("output")
                    # output_data = rank_sum + ".json"
                    # output_data_path = "output/" + output_data
                    # data_path = utility.save_json(output_data_path, build_data)
                    # app.logger.info("Data cached to " + data_path)
                    # app.logger.info(build_data)
                    # 开始模板编译
                    tpl = makedoc.WordMaker(template_path, build_data, output_path, pic_path)
                    res = tpl.make_doc()
                    # 编译后
                    if res != "true":
                        # 若模板生成不成功，则 清理缓存
                        utility.clean_field(dest_path, unpack_dir)
                        # app.logger.error(res)
                        utility.write_log("File_Output_Error", "File Output Error："+res, 500, request, start)
                        return utility.make_response(False, "File_Output_Error", res), 500
                    else:
                        # 缓存生成的模板（测试代码）
                        # output_tmp_path = "output/" + output_name
                        # tmp_path = utility.save_bytes_io(output_tmp_path,output_path)
                        # app.logger.info("File output " + output_name)
                        # 清理缓存
                        utility.clean_field(dest_path, unpack_dir)
                        # 输出word文件流指向0，避免输出有问题
                        output_path.seek(0)
                        #lg = logger.Logger(logger.get_profile_config("kibana.logger_name"))
                        #lg.info('build success'.encode('utf8'))
                        #utility.make_response(True, "build_success", "生成成功")
                        #elapsed = (time.clock() - start)
                        #app.logger.info("Time used:", elapsed)
                        # 对外输出(二进制)文件流，并设定文件名称
                        utility.write_log("Build_Success", "Build Success", 200, request, start)
                        return send_file(output_path, as_attachment=True, attachment_filename=output_name)
                else:
                    utility.clean_field(dest_path, unpack_dir)
                    utility.write_log("Data_File_NotFound", "Data File NotFound", 500, request, start)
                    return utility.make_response(False, "Data_File_NotFound", "数据文件不存在"), 500
            else:
                utility.clean_field(dest_path, unpack_dir)
                utility.write_log("Template_File_NotFound", "Template File NotFound", 500, request, start)
                return utility.make_response(False, "Template_File_NotFound", "模板文件不存在"), 500
    else:
        utility.write_log("error.10002", "Non-legal Request", 500, request, start)
        return utility.make_response(False, "error.10002", "非法调用"), 500


@app.route("/")
@disable_logging
def index():
    utility.keep_dir("temp")
    return "<h1 style='color:red'>Hello World</h1>"


if __name__ == '__main__':
    app.run()

if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)