from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.db.database import get_db, engine, settings
from app.db import models
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.api_key_auth import APIKeyAuthMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.request_scheduler import RequestScheduler
from app.api.request import request_scheduler

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

# 初始化定时任务调度器
scheduler = AsyncIOScheduler()

# 添加定时任务：每5秒更新一次系统统计
@scheduler.scheduled_job('interval', seconds=5)
async def update_system_stats_job():
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        await request_scheduler.update_system_stats(db)
    finally:
        db.close()

# 启动定时任务
@app.on_event("startup")
async def startup_event():
    scheduler.start()

# 关闭定时任务
@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
