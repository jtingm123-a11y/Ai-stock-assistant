from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
DATABASE_PATH = DATA_DIR / "stock_assistant.db"
REPORT_EXPORT_DIR = DATA_DIR / "exports"

DEFAULT_HISTORY_START = "20200101"
DEFAULT_ADJUST = "qfq"
APP_NAME = "个人股票研究助手 V1"
