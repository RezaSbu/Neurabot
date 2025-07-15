from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api import router
from app.config import settings
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import structlog

logger = structlog.get_logger()

app = FastAPI()

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda request, exc: {"error": "Rate limit exceeded"})
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(router)

@app.head('/health')
@app.get('/health')
@limiter.limit("10/minute")  # Rate limit example
def health_check(request: Request):  # اضافه کردن request
    logger.info("Health check called")
    return 'ok'