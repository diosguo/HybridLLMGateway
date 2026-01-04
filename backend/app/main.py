from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.db.database import get_db, engine
from app.db import models
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.api_key_auth import APIKeyAuthMiddleware

# 创建数据库表
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Hybrid LLM Gateway",
    description="企业级大模型调用网关，支持离线在线请求整合",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加限流中间件
app.add_middleware(RateLimitMiddleware)

# 添加API密钥认证中间件
app.add_middleware(APIKeyAuthMiddleware)

# 导入路由
from app.api import auth, model, request, admin

app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(model.router, prefix="/api/model", tags=["模型管理"])
app.include_router(request.router, prefix="/api/request", tags=["请求处理"])
app.include_router(admin.router, prefix="/api/admin", tags=["管理端"])

@app.get("/")
async def root():
    return {"message": "Hybrid LLM Gateway is running"}

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    return {"status": "healthy", "database": "connected"}
