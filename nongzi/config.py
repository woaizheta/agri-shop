# 农资店管理系统 - 配置文件
import os, sys


def _get_data_dir() -> str:
    """数据目录：AGRISHOP_DATA_DIR 环境变量优先，否则用应用目录"""
    env_dir = os.environ.get("AGRISHOP_DATA_DIR")
    if env_dir:
        return env_dir
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _get_app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "nongzi")
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = _get_app_dir()
DATA_DIR = _get_data_dir()
DATABASE_PATH = os.path.join(DATA_DIR, "nongzi.db")
EXPORTS_DIR = os.path.join(DATA_DIR, "exports")
BACKUPS_DIR = os.path.join(DATA_DIR, "backups")

# 店铺信息
STORE_NAME = "丰收农资店"
STORE_ADDRESS = "XX省XX市XX区XX路XX号"
STORE_PHONE = "138-0000-0000"

# 数据库配置
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# 版本号
VERSION = "1.0.0"
BUILD_DATE = "2026-06-29"