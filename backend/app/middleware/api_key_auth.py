from fastapi import HTTPException, Request, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db import models
from typing import Optional

class APIKeyAuthMiddleware:
    """API密钥认证中间件"""
    
    async def __call__(self, request: Request, call_next):
        # 跳过认证的路径
        skip_paths = [
            "/",
            "/health",
            "/api/auth/register",
            "/api/auth/token"
        ]
        
        if request.url.path in skip_paths:
            return await call_next(request)
        
        # 获取API密钥
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            # 尝试从查询参数中获取
            api_key = request.query_params.get("api_key")
        
        if not api_key:
            raise HTTPException(
                status_code=401,
                detail="API key is required"
            )
        
        # 验证API密钥
        db = next(get_db())
        db_api_key = db.query(models.APIKey).filter(
            models.APIKey.key == api_key,
            models.APIKey.is_active == True
        ).first()
        
        if not db_api_key:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired API key"
            )
        
        # 将用户ID添加到请求状态中，供后续使用
        request.state.user_id = db_api_key.user_id
        
        response = await call_next(request)
        return response
