# config.py
from gevent import monkey

monkey.patch_all()  # python 网络接口多进程处理包

# 最大挂起连接数 64-2048
backlog = 1024
# 并行工作线程数
workers = 4
# 最大并发客户端数
worker_connections = 1000
# 监听内网端口5000【按需要更改】
bind = '0.0.0.0:5100'
# 设置守护进程【关闭连接时，程序仍在运行】
daemon = False
# 设置超时时间360s，默认为30s。按自己的需求进行设置
timeout = 360
# 设置访问日志和错误信息日志路径
errorlog = '-'
accesslog = '-'

disable_existing_loggers = False
# accesslog = './logs/gunicorn.access.log'
# errorlog = './logs/gunicorn.error.log'
# logconfig_dict = {
#     'version':1,
#     'disable_existing_loggers': False,
#     'loggers':{
#         "gunicorn.error": {
#             "level": "DEBUG",# 打日志的等级可以换的，下面的同理
#             "handlers": ["error_file"], # 对应下面的键
#             "propagate": 1,
#             "qualname": "gunicorn.error"
#         },

#         "gunicorn.access": {
#             "level": "DEBUG",
#             "handlers": ["access_file"],
#             "propagate": 0,
#             "qualname": "gunicorn.access"
#         } 
#     },
#     'handlers':{
#         "error_file": {
#             "class": "logging.handlers.RotatingFileHandler",
#             "maxBytes": 1024*1024*1024,# 打日志的大小，我这种写法是1个G
#             "backupCount": 1,# 备份多少份，经过测试，最少也要写1，不然控制不住大小
#             "formatter": "generic",# 对应下面的键
#             # 'mode': 'w+',
#             "filename": "/midware/logs/equityschemepy/gunicorn.error.log"# 打日志的路径
#         },
#         "access_file": {
#             "class": "logging.handlers.RotatingFileHandler",
#             "maxBytes": 1024*1024*1024,
#             "backupCount": 1,
#             "formatter": "generic",
#             "filename": "/midware/logs/equityschemepy/gunicorn.access.log",
#         }
#     },
#     'formatters':{
#         "generic": {
#             "format": "'[%(process)d] [%(asctime)s] %(levelname)s [%(filename)s:%(lineno)s] %(message)s'", # 打日志的格式
#             "datefmt": "[%Y-%m-%d %H:%M:%S %z]",# 时间显示方法
#             "class": "logging.Formatter"
#         },
#         "access": {
#             "format": "'[%(process)d] [%(asctime)s] %(levelname)s [%(filename)s:%(lineno)s] %(message)s'",
#             "class": "logging.Formatter"
#         }
#     }
# }
threads = 16  # 单个进程开启处理的线程数,若 程序运行过载会导致服务重启
worker_class = 'gevent'  # sync, gevent,meinheld
proc_name = './logs/http.pid'
pidfile = './logs/gunicorn.pid'
loglevel = 'info'
