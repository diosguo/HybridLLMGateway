from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.db import models
from app.api.auth import get_current_active_user
from pydantic import BaseModel

router = APIRouter()

class ModelConfigCreate(BaseModel):
    provider: str
    model_name: str
    api_key: str
    base_url: str = None
    max_tokens: int = 4096
    temperature: float = 0.7

class ModelConfigUpdate(BaseModel):
    api_key: str = None
    base_url: str = None
    max_tokens: int = None
    temperature: float = None
    is_active: bool = None

class ModelConfigResponse(BaseModel):
    id: int
    provider: str
    model_name: str
    base_url: str = None
    max_tokens: int
    temperature: float
    is_active: bool

    class Config:
        from_attributes = True

# 获取所有模型配置
@router.get("/", response_model=List[ModelConfigResponse])
async def get_model_configs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    model_configs = db.query(models.ModelConfig).offset(skip).limit(limit).all()
    return model_configs

# 获取单个模型配置
@router.get("/{model_id}", response_model=ModelConfigResponse)
async def get_model_config(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    model_config = db.query(models.ModelConfig).filter(models.ModelConfig.id == model_id).first()
    if not model_config:
        raise HTTPException(status_code=404, detail="Model config not found")
    return model_config

# 创建模型配置
@router.post("/", response_model=ModelConfigResponse)
async def create_model_config(
    model_config: ModelConfigCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    db_model_config = models.ModelConfig(
        provider=model_config.provider,
        model_name=model_config.model_name,
        api_key=model_config.api_key,
        base_url=model_config.base_url,
        max_tokens=model_config.max_tokens,
        temperature=model_config.temperature
    )
    
    db.add(db_model_config)
    db.commit()
    db.refresh(db_model_config)
    return db_model_config

# 更新模型配置
@router.put("/{model_id}", response_model=ModelConfigResponse)
async def update_model_config(
    model_id: int,
    model_config: ModelConfigUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    db_model_config = db.query(models.ModelConfig).filter(models.ModelConfig.id == model_id).first()
    if not db_model_config:
        raise HTTPException(status_code=404, detail="Model config not found")
    
    update_data = model_config.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_model_config, field, value)
    
    db.commit()
    db.refresh(db_model_config)
    return db_model_config

# 删除模型配置
@router.delete("/{model_id}")
async def delete_model_config(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    db_model_config = db.query(models.ModelConfig).filter(models.ModelConfig.id == model_id).first()
    if not db_model_config:
        raise HTTPException(status_code=404, detail="Model config not found")
    
    db.delete(db_model_config)
    db.commit()
    return {"message": "Model config deleted successfully"}
