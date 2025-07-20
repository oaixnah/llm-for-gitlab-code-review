import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()


class Settings(BaseSettings):
    # GitLab配置
    gitlab_url: str = os.getenv("GITLAB_URL", "")
    gitlab_token: str = os.getenv("GITLAB_TOKEN", "")
    gitlab_webhook_secret: str = os.getenv("GITLAB_WEBHOOK_SECRET", "")
    gitlab_bot_username: str = os.getenv("GITLAB_BOT_USERNAME", "")

    # MySQL配置
    mysql_host: str = os.getenv("MYSQL_HOST", "")
    mysql_port: int = int(os.getenv("MYSQL_PORT", ""))
    mysql_database: str = os.getenv("MYSQL_DATABASE", "")
    mysql_user: str = os.getenv("MYSQL_USER", "")
    mysql_passwd: str = os.getenv("MYSQL_PASSWD", "")

    # LLM配置
    llm_api_url: str = os.getenv("LLM_API_URL", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_api_type: str = os.getenv("LLM_API_TYPE", "")
    llm_model: str = os.getenv("LLM_MODEL", "")

    # 国际化配置
    locale: str = os.getenv("LOCALE", "zh_CN")

    debug: bool = os.getenv("DEBUG", "False").lower() == "true"

    def on_modified(self, event):
        if event.src_path.endswith('.env'):
            # 重新加载配置
            load_dotenv(override=True)
            logger.info("配置已重新加载")


settings = Settings()


def engine_url():
    """创建数据库引擎url
    """
    return URL.create(
        drivername='mysql+pymysql',
        username=settings.mysql_user,
        password=settings.mysql_passwd,
        host=settings.mysql_host,
        port=settings.mysql_port,
        database=settings.mysql_database
    )


def engine_config():
    return {
        "pool_recycle": 3600,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "echo": settings.debug,
        "pool_size": 10,  # 增加连接池大小
        "pool_timeout": 30,  # 添加超时设置
        "connect_args": {
            'connect_timeout': 3,
            'charset': 'utf8mb4',  # 支持完整的 UTF-8
            'autocommit': True
        }
    }


engine = create_engine(engine_url(), **engine_config())
# 默认session
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
