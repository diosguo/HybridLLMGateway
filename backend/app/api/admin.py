from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db import models
from app.api.auth import get_current_active_user
from pydantic import BaseModel

router = APIRouter()

class SystemStatsResponse(BaseModel):
    timestamp: str
    active_realtime_requests: int
    active_task_requests: int
    queue_length: int
    avg_latency: float
    throughput: float

class UserListResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    created_at: str

# 获取系统统计信息
@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # 获取最新的系统统计
    latest_stats = db.query(models.SystemStats).order_by(
        models.SystemStats.timestamp.desc()
    ).first()
    
    if not latest_stats:
        # 如果没有统计数据，返回默认值
        return {
            "timestamp": "N/A",
            "active_realtime_requests": 0,
            "active_task_requests": 0,
            "queue_length": 0,
            "avg_latency": 0.0,
            "throughput": 0.0
        }
    
    return {
        "timestamp": latest_stats.timestamp.isoformat(),
        "active_realtime_requests": latest_stats.active_realtime_requests,
        "active_task_requests": latest_stats.active_task_requests,
        "queue_length": latest_stats.queue_length,
        "avg_latency": latest_stats.avg_latency,
        "throughput": latest_stats.throughput
    }

# 获取所有用户
@router.get("/users", response_model=List[UserListResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    users = db.query(models.User).offset(skip).limit(limit).all()
    
    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at.isoformat()
        }
        for user in users
    ]

# 获取系统总请求数
@router.get("/requests/total")
async def get_total_requests(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    total_realtime = db.query(models.Request).filter(
        models.Request.request_type == models.RequestType.REALTIME
    ).count()
    
    total_task = db.query(models.Request).filter(
        models.Request.request_type == models.RequestType.TASK
    ).count()
    
    total_completed = db.query(models.Request).filter(
        models.Request.status == "completed"
    ).count()
    
    return {
        "total_realtime": total_realtime,
        "total_task": total_task,
        "total_completed": total_completed,
        "total_all": total_realtime + total_task
    }

# 获取活跃模型配置
@router.get("/models/active")
async def get_active_models(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    active_models = db.query(models.ModelConfig).filter(
        models.ModelConfig.is_active == True
    ).all()
    
    return {
        "count": len(active_models),
        "models": [
            {
                "id": model.id,
                "provider": model.provider,
                "model_name": model.model_name
            }
            for model in active_models
        ]
    }
