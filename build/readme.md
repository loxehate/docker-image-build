#### YDWordMaker：易董股东大会Word生成
##### Server Project 服务器版

---
项目依赖
* flask - web接口
* gunicorn - 托管 flask 多线程
* docxtpl - 业务相关，word生成
> 基于：Python 3.6.x (win 3.6.8 / linux 3.6.11)
<br> 开发使用：Pycharm
<br> 主程序：app.py
---
部署

> 注：如果您只安装了 python 3.6，那么可以直接 执行 pip 指令；
如果您的机器上面有 vue/node 项目，那么在装 py 3.6时不要执行全局安装，不过py快捷指令可以装，否则其他项目的调试打包操作会不成功。 

1.本地开发按照依赖配置安装

`python 3.6 所在路径\Scripts\pip install -r requirements.txt`

2.生成 依赖配置

`python 3.6 所在路径\Scripts\pip freeze>requirements.txt`

3.服务器部署(Linux)

`项目所在路径\deploy.sh`

*.本地运行原始参数

`python.exe -m flask run --host=0.0.0.0 --port=5000`

---
运行后访问说明

| 环境 | 端口 | 备注 |
| ------ | ------ | -----|
| 本机 - localhost | 5000 | 1.请在 pycharm 右上角 **WordMaker** 下拉框 中 的 "Edit Config..." 中修改端口 <br>2.5000端口需要到Windows防火墙高级设置中开启 <br>3.实际访问IP为本电脑的IP|
| 服务器 | 5100 | 1.请在 gunicorn.conf.py 中修改端口 <br>2.请在config.ini 中 修改日志上报配置
---
接口调用说明

| 地址 | /makedoc |
| ------ | ------ | 
| 调用模式 | POST |
| 参数 | file **数据包,zip格式** |

---
数据包数据结构

     └─pack -> 此处命名需与zip文件名保持一致
        │  data.json -> 模板数据文件
        │
        ├─img
        │      a.png -> 需插入的图片文件
        │
        └─template
                template.docx -> 要使用的模板文件

---
返回值说明

| 状态码 | 返回值 | 说明 |
| ---- | ---- | ---- |
| 200 | 文件流，名称为定义好的生成文件名称 | 文件生成成功(生成成功返回) |
| 500 | (False, "error.10002", "非法调用") | 未获取数据包（请求方式不对，参数不对） |
| 500 | (False, "Template_File_NotFound", "模板文件不存在") | 模板文件不存在 |
| 500 | (False, "Data_File_NotFound", "数据文件不存在") | 数据文件不存在 |
| 500 | (False, "File_Output_Error", Word错误信息...) | 模板文件有问题 |

---
对插入图片的辅助支持

    #图片|图片名_扩展名 file_name|高度 h|宽度 w"（单位为"Mm"）->InlineImage
    示例
    #图片|a2_png|40
    解释
    #图片|图片名_扩展名|高度|宽度
    #图片| - 特定表示字符串 保留
    图片名_扩展名 - 图片文件的文件名，带扩展名，点 用 _ 替代
    高度 - 图片的高度 可选，请设置
    宽度 - 图片的宽度 可选，不填写则根据设定的高度进行等比缩放
    
---
建议：配置全局pypl镜像

在C盘用户文件夹里面当前用户文件夹下创建 pip 文件夹，在里面创建 pip.ini
将内容设置为以下内容并保存，下次安装依赖包时将获得速度增益

    [global]
    index-url = http://pypi.douban.com/simple
    [install]
    trusted-host = pypi.douban.com