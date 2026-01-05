from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import uuid
from datetime import datetime
from app.db.database import get_db, settings
from app.db import models
from app.api.auth import get_current_active_user
from app.services.model_provider import ModelProviderService
from app.services.request_scheduler import RequestScheduler
from pydantic import BaseModel

router = APIRouter()

# 初始化服务
model_provider_service = ModelProviderService()
request_scheduler = RequestScheduler(settings)

class LLMRequest(BaseModel):
    model_config_id: int
    prompt: str
    request_type: str  # "realtime" or "task"
    params: dict = {}

class RequestResponse(BaseModel):
    request_id: str
    status: str
    message: str
    response: str = None

class RequestStatusResponse(BaseModel):
    request_id: str
    status: str
    response: str = None
    error: str = None
    created_at: datetime
    updated_at: datetime

# 创建LLM请求
@router.post("/", response_model=RequestResponse)
async def create_llm_request(
    llm_request: LLMRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # 验证请求类型
    if llm_request.request_type not in [models.RequestType.REALTIME, models.RequestType.TASK]:
        raise HTTPException(status_code=400, detail="Invalid request type")
    
    # 验证模型配置
    model_config = db.query(models.ModelConfig).filter(
        models.ModelConfig.id == llm_request.model_config_id,
        models.ModelConfig.is_active == True
    ).first()
    
    if not model_config:
        raise HTTPException(status_code=404, detail="Model config not found or inactive")
    
    # 生成请求ID
    request_id = str(uuid.uuid4())
    
    # 保存请求到数据库
    db_request = models.Request(
        request_id=request_id,
        user_id=current_user.id,
        model_config_id=llm_request.model_config_id,
        request_type=llm_request.request_type,
        prompt=llm_request.prompt,
        params=str(llm_request.params),
        status="pending"
    )
    
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    
    # 处理请求
    if llm_request.request_type == models.RequestType.REALTIME:
        # 实时请求，立即处理
        try:
            response = await request_scheduler.handle_realtime_request(
                db_request,
                model_provider_service,
                db
            )
            return {
                "request_id": request_id,
                "status": "completed",
                "message": "Request processed successfully",
                "response": response
            }
        except Exception as e:
            # 更新请求状态为失败
            db_request.status = "failed"
            db_request.error = str(e)
            db.commit()
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # 任务型请求，添加到后台队列
        background_tasks.add_task(
            request_scheduler.handle_task_request,
            db_request,
            model_provider_service,
            db
        )
        return {
            "request_id": request_id,
            "status": "pending",
            "message": "Request added to queue"
        }

# 获取请求状态
@router.get("/{request_id}", response_model=RequestStatusResponse)
async def get_request_status(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_request = db.query(models.Request).filter(
        models.Request.request_id == request_id,
        models.Request.user_id == current_user.id
    ).first()
    
    if not db_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    return {
        "request_id": db_request.request_id,
        "status": db_request.status,
        "response": db_request.response,
        "error": db_request.error,
        "created_at": db_request.created_at,
        "updated_at": db_request.updated_at
    }

# 获取用户请求历史
@router.get("/history/user", response_model=List[RequestStatusResponse])
async def get_user_request_history(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    requests = db.query(models.Request).filter(
        models.Request.user_id == current_user.id
    ).order_by(
        models.Request.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return [
        {
            "request_id": req.request_id,
            "status": req.status,
            "response": req.response,
            "error": req.error,
            "created_at": req.created_at,
            "updated_at": req.updated_at
        }
        for req in requests
    ]
