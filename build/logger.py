import logging
import os
import configparser
from datetime import datetime


class LoggerModule:

    def __init__(self, handler_type):
        self.config = configparser.ConfigParser()
        self.handler_type = handler_type
        self.section_name = f'{self.handler_type}_handler'
        self.config.read(os.path.join(os.path.dirname(os.path.realpath(__file__)),"config.ini"))
        # os.path.dirname(os.path.realpath(__file__)) + "/config.ini"
        self.logger = self.setup_logger()

    def get_logger(self):
        return self.logger

    def setup_logger(self):
        # Read configuration for the given handler type
        # if not self.config.has_section(self.section_name):
            # raise ValueError(f"Configuration for handler '{self.handler_type}' not found.")

        basepath = self.get_local_basepath()
        filename = self.get_local_filename()
        log_level = self.get_local_level()
        log_format = self.get_local_formatter()
        fullname = datetime.now().strftime(os.path.join(basepath, filename))

        # Ensure the basepath directory exists
        os.makedirs(basepath, exist_ok=True)

        # Create and configure logger
        logger = logging.getLogger(self.section_name)
        logger.setLevel(log_level)  # or another level of your choice

        # Create file handler and set format
        file_handler = logging.FileHandler(fullname)
        formatter = logging.Formatter(log_format)
        file_handler.setFormatter(formatter)

        # Add the handler to the logger
        logger.addHandler(file_handler)

        return logger

    def get_local_basepath(self):
        content = str(self.get_profile_config(self.section_name+ '.basepath'))
        content = content if content != "" else os.path.join(os.path.dirname(os.path.realpath(__file__)),"logs")
        return content

    def get_local_filename(self):
        content = str(self.get_profile_config(self.section_name+ '.filename'))
        content = content if content != "" else "%%Y-%%m-%%d.log"
        return content

    def get_local_formatter(self):
        content = str(self.get_profile_config(self.section_name+ '.format'))
        content = content if content != "" else "%(asctime)s [%(levelname)s] %(message)s"
        return content

    def get_local_level(self):
        level_dic = {"DEBUG": logging.DEBUG, "INFO": logging.INFO, "WARNING": logging.WARNING, "ERROR": logging.ERROR}
        content = str(self.get_profile_config(self.section_name+ '.level')).upper()
        content = content if content != "" else "INFO"
        content = level_dic[content]
        return content

    def get_profile_config(self,section_key):
        res = ""
        try:
            sk_list = str(section_key).split(".")
            section = sk_list[0]
            key = sk_list[1]
            res = self.config.get(section, key)
        except BaseException as E:
            return res
        else:
            return res