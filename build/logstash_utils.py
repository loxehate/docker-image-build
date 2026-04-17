"""logstash定义类"""

import logging

import logstash

from resource.appSource import config

LogDict = {'INFO': logging.INFO}


class LogstashConstants:
    """logstash涉及常量"""

    def __init__(self):
        self.host = config.get_profile_config('logstash.host')
        self.port = int(config.get_profile_config('logstash.port'))
        self.level = config.get_profile_config('logstash.level')
        self.tag = config.get_profile_config('logstash.tag')
        self.program = config.get_profile_config('logstash.program')


log = LogstashConstants()


class Logger:
    """日志类"""

    def __init__(self, logger_name):
        self.logger_level = LogDict.get(log.level)
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(self.logger_level)

        # logstash日志
        _config = self.get_config()
        logstash_handler = logstash.TCPLogstashHandler(**_config)
        logstash_handler.setLevel(self.logger_level)

        # console日志
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.logger_level)

        self.logger.addHandler(logstash_handler)
        self.logger.addHandler(console_handler)

        # logstash program
        self._extra = {'program': log.program}

    @staticmethod
    def get_config():
        """配置logstash服务器参数
        :return:
        """
        _config = {'host': log.host, 'port': log.port, 'tags': [log.tag], 'version': 1}

        return _config

    def debug(self, msg: str):
        """封装logger.debug方法
        :param msg:消息体
        :return:
        """
        self.logger.debug(msg, extra=self._extra)

    def info(self, msg: str):
        """封装logger.info方法
        :param msg:消息体
        :return:
        """
        self.logger.info(msg, extra=self._extra)

    def warning(self, msg: str):
        """封装logger.warning方法
        :param msg:消息体
        :return:
        """
        self.logger.warning(msg, extra=self._extra)

    def error(self, msg: str):
        """封装logger.error方法
        :param msg:消息体
        :return:
        """
        self.logger.error(msg, extra=self._extra)
