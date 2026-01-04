import redis
import time
from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.db.database import settings

class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""
    
    def __init__(self, app, redis_url=settings.REDIS_URL):
        super().__init__(app)
        self.redis = redis.from_url(redis_url)
        
    async def dispatch(self, request: Request, call_next):
        # 获取客户端IP
        client_ip = request.client.host
        
        # 构建限流键
        rate_limit_key = f"rate_limit:{client_ip}"
        
        # 设置限流参数：100次请求/分钟
        max_requests = 100
        window_seconds = 60
        
        try:
            # 获取当前请求数
            current = self.redis.get(rate_limit_key)
            
            if current:
                current = int(current)
                if current >= max_requests:
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded. Please try again later."
                    )
                # 增加请求数
                self.redis.incr(rate_limit_key)
            else:
                # 设置初始值和过期时间
                self.redis.setex(rate_limit_key, window_seconds, 1)
        except Exception as e:
            # 如果Redis连接失败，记录日志并继续处理请求
            print(f"Rate limit error: {e}")
        
        response = await call_next(request)
        return response
