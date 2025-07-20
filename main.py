import logging
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from config import settings, engine
from i18n import i18n, init_i18n
from review_manager import ReviewManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            'app.log', maxBytes=10*1024*1024, backupCount=5
        )
    ]
)
logger = logging.getLogger(__name__)


def filter_transactions(event, _):
    """Filtering
    """
    url_string = event["request"]["url"]
    parsed_url = urlparse(url_string)
    filter_path = (
        '/health/'
    )

    if parsed_url.path in filter_path:
        return None

    return event


# 初始化国际化
init_i18n()
i18n.set_locale(settings.locale)

# 初始化增强审查管理器
review_manager = ReviewManager()


@asynccontextmanager
async def lifespan(_):
    """生命周期事件
    """
    if not settings.debug:
        await review_manager.check()
        # Mysql
        from sqlalchemy.exc import OperationalError
        try:
            connect = engine.connect()
        except OperationalError as e:
            raise e
        else:
            connect.close()
    yield


app = FastAPI(
    lifespan=lifespan
)


@app.post('/')
async def system_hooks(request: Request, background_tasks: BackgroundTasks):
    """
    处理系统钩子事件
    :param request:
    :param background_tasks:
    :return:
    """
    try:
        # 解析JSON数据
        event_data = await request.json()

        # 获取事件类型
        object_kind = event_data.get('object_kind', '')

        # 处理合并请求事件
        if object_kind == "merge_request":
            background_tasks.add_task(review_manager.process_merge_request_event, event_data)
            return JSONResponse({
                "status": i18n.t('status.accepted'),
                "message": i18n.t('response.merge_request_queued')
            })
        else:
            logger.info(f"{i18n.t('log.ignore_event_type')} {object_kind}")
            return JSONResponse({
                "status": i18n.t('status.ignored'),
                "message": i18n.t('response.event_not_handled', event_type=object_kind)
            })

    except Exception as e:
        logger.error(f"{i18n.t('log.webhook_processing_failed')}: {e}")
        raise HTTPException(status_code=500, detail=f"{i18n.t('response.internal_server_error')}: {str(e)}")


@app.head("/health/")
async def health_check(): return
