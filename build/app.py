# -*- coding: utf-8 -*-
# Auther : di.liu
# Date : 2023/1/11 上午10:14
# File : cal_app.py.py

from flask import Flask, request
from resource.appSource import config
app = Flask(__name__)



@app.route('/', methods=['get'])
def calculate():
    return ('当前环境：{}'.format(config._profile))

@app.route('/api', methods=['get'])
def api_response():
    return ('当前api环境：{}'.format(config._profile))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
