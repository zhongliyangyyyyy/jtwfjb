from pydantic_settings import BaseSettings
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # 数据库
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR}/data/violations.db"

    # 文件存储
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    DATA_DIR: Path = BASE_DIR / "data"
    CLIPS_DIR: Path = BASE_DIR / "data" / "clips"
    FRAMES_DIR: Path = BASE_DIR / "data" / "frames"
    THUMBNAILS_DIR: Path = BASE_DIR / "data" / "thumbnails"
    REPORTS_DIR: Path = BASE_DIR / "data" / "reports"

    # API配置
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "车辆违法行为举报系统"

    # 上传配置
    MAX_UPLOAD_SIZE: int = 500 * 1024 * 1024  # 500MB
    CHUNK_SIZE: int = 5 * 1024 * 1024  # 5MB

    # AI模型配置
    VEHICLE_CONFIDENCE_THRESHOLD: float = 0.5
    PLATE_CONFIDENCE_THRESHOLD: float = 0.6

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

# 确保目录存在
for dir_path in [settings.UPLOAD_DIR, settings.DATA_DIR, settings.CLIPS_DIR,
                 settings.FRAMES_DIR, settings.THUMBNAILS_DIR, settings.REPORTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)
