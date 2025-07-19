from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.api import router
from app.auth import auth_router
from app.config import settings

app = FastAPI()

# تنظیم Limiter برای rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# اضافه کردن exception handler برای rate limit
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # دامنه Vite
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(router)
app.include_router(auth_router)

@app.head('/health')
@app.get('/health')
def health_check():
    return 'ok'