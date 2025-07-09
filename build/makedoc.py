import json
import os
import traceback
import utility
import jinja2
from docxtpl import DocxTemplate, InlineImage
# for height and width you have to use millimeters (Mm), inches or points(Pt) class :
from docx.shared import Mm, Inches, Pt
from outFilter import outFilters


# filter - 放在外面


def add_jinja2_filters(env_jinja):
    """
    将自定义filter载入jinja环境
    :param env_jinja:
    :return:
    """
    for item in outFilters:
        env_jinja.filters[item['name']] = item['filterfunction']


class WordMaker(object):
    """定义一个文档生成实例"""

    def __init__(self, template_path, data, output_path, pic_path=""):
        """
        类初始化
        :param self: 实例本身
        :param template_path: 模板路径
        :param data: 模板数据
        :param output_path: 文件生成路径/流
        :return:
        """
        self.template_path = template_path
        self.data = data
        self.output_path = output_path
        # 工作文件夹(图片所在文件夹 = 目标生成文件所在文件夹)
        self.pic_dir = pic_path
        # 实例化模板操作对象
        self.doc = DocxTemplate(self.template_path)

    # return value * by

    def make_doc(self):
        """
        根据模板及数据生成文件
        :param self: 该实体类本身
        :return: 执行结果，若正常生成则返回"true",不正常则返回其他错误信息
        """

        # doc.replace_pic('dummy_header_pic.jpg', 'header_pic_i_want.jpg') 替换现有图片
        # my_image = InlineImage(doc, 'test_files/python_logo.png', width=Mm(20)) 指定变量替换为图片(来源，宽度)
        try:
            jinja_env = jinja2.Environment()
            add_jinja2_filters(jinja_env)
            self.recurse(self.data)  # 结构重组
            self.doc.render(self.data, jinja_env)  # 填充数据

            self.doc.save(self.output_path)  # 保存目标文件
        except BaseException as E:
            # 注 详细的异常信息 - 包括 trace 的异常信息 可通过以下方法获取为字符串格式
            return repr(E)
        else:
            return "true"

    def recurse(self, data):
        """
        辅助函数1 - json结构值遍历
        :param data: json结构 dict
        :return: 调整值后的结构
        """
        # json 从根节点 data 遍历 子项 element
        for element in data:
            if type(data) is list and (type(element) is not list or type(element) is not dict):
                # 对于 data 为 list，子项 为 非列表 list or dict 的情况做单独处理
                # like ["a","b","c"]，赋值模式切换为 下标模式 0,1,2,3
                # 获取对应值的下标，通过下标对值进行重组
                index = data.index(element)
                if type(data[index]) is list or type(data[index]) is dict:
                    # 若可遍历 则进行 值的 递归遍历
                    self.recurse(data[index])
                else:
                    # 否则 直接进行值重组
                    data[index] = self.json_revalue(data[index])
            else:
                # 若不需要单独处理，则继续判断键对应值的类型 是不是 list or dict
                if type(data[element]) is list or type(data[element]) is dict:
                    # 若可遍历 则进行 值的 递归遍历
                    self.recurse(data[element])
                else:
                    # 否则 直接进行值重组
                    data[element] = self.json_revalue(data[element])

    def json_revalue(self, param):
        """
        辅助结构2 - 值重组
        将特定结构的值转换为特定对象，其他结构不调整
        已实现的转换
        "#图片|图片名_扩展名 file_name|高度 h|宽度 w"（单位为"Mm"）->InlineImage
        示例
        #图片|a2_png|40
        解释
        #图片|图片名_扩展名|高度|宽度
        #图片| - 特定表示字符串 保留
        图片名_扩展名 - 图片文件的文件名，带扩展名，点 用 _ 替代
        高度 - 图片的高度 可选，请设置
        宽度 - 图片的宽度 可选
        :param param: 字符串
        :return: 重组后的结构
        """
        if isinstance(param, str):
            # 判断 当前 value 是否是 str 类型
            param_str = str(param)
            if param_str.startswith("#图片|"):
                param_list = param_str.replace("#图片|", "").split("|")
                param_length = len(param_list)
                if param_length == 0:
                    # 图片名称未指定
                    return ""
                else:
                    # 当前模板实例 tpl
                    new_tpl = self.doc
                    # 当前图片位置 image_descriptor
                    new_image_descriptor = self.pic_dir + param_list[0].replace("_", ".")
                    # 待传递新图片实例 (必须参数为 模板实例及图片位置)
                    est = os.path.exists(new_image_descriptor)
                    # 判断指定位置的图片是否存在，不存在则直接设定为空
                    if not est:
                        # 文件不存在 则返回空字符串
                        return ""
                    else:
                        # 若存在，则设定图片实例
                        new_param = InlineImage(new_tpl, new_image_descriptor)
                        if param_length > 1:
                            # 高度 height = 单位预设为Mm
                            new_param.height = Mm(int(param_list[1]))
                        elif param_length > 2:
                            # 宽度 width = 单位预设为Mm
                            new_param.width = Mm(int(param_list[2]))
                        # 返回 图片实例
                    return new_param
            else:
                return param
        else:
            return param
