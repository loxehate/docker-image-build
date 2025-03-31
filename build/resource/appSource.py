import configparser
import os

profileDict = {'dev': '开发环境', 'prod': '生产环境'}


# 读取配置文件
class ReadConfig:

    # 加载配置文件
    def __init__(self):
        self.config = configparser.ConfigParser()
        path = os.path.join(os.path.split(os.path.realpath(__file__))[0], 'application.ini')
        self.config.read(path, encoding='utf-8')
        self._profile = os.getenv("profile")
        if self._profile is None:
            self._profile = self.get_config("app", "profile")
        print()

    # 读取配置项
    def get_config(self, section, key):
        return self.config.get(section, key)

    # 读取环境配置
    def get_profile_config(self, key):
        return self.config.get(self._profile, key)

    # 取得配置环境
    def get_profile(self):
        return self._profile


# 单例模式
config = ReadConfig()
print()
