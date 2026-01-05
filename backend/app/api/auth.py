from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import bcrypt
from jose import JWTError, jwt
from datetime import datetime, timedelta
from app.db.database import get_db, settings
from app.db import models
from pydantic import BaseModel

router = APIRouter()

# OAuth2密码Bearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# Pydantic模型
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str

    class Config:
        from_attributes = True

# API密钥Pydantic模型
class APIKeyCreate(BaseModel):
    name: str
    expires_at: datetime = None

class APIKeyResponse(BaseModel):
    id: int
    key: str
    name: str
    is_active: bool
    created_at: datetime
    expires_at: datetime = None

    class Config:
        from_attributes = True

class APIKeyUpdate(BaseModel):
    name: str = None
    is_active: bool = None
    expires_at: datetime = None

# 密码校验
def verify_password(plain_password, hashed_password):
    # 手动截断密码到72字节，避免bcrypt错误
    plain_password = plain_password[:72].encode('utf-8')
    hashed_password = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_password, hashed_password)

# 生成密码哈希
def get_password_hash(password):
    # 手动截断密码到72字节，避免bcrypt错误
    password = password[:72].encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password, salt)
    return hashed.decode('utf-8')

# 获取用户
def get_user(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

# 创建访问令牌
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# 生成API密钥
def generate_api_key():
    import secrets
    return secrets.token_urlsafe(32)

# 获取当前用户
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(db, username=username)
    if user is None:
        raise credentials_exception
    return user

# 获取当前活跃用户
async def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    return current_user

# 注册路由
@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    # 检查用户名是否已存在
    db_user = get_user(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # 检查邮箱是否已存在
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # 检查密码长度，bcrypt要求密码不能超过72字节
    if len(user.password) > 72:
        raise HTTPException(status_code=400, detail="Password cannot exceed 72 characters")
    
    # 创建用户
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# 登录路由
@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = get_user(db, username=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }

# 获取当前用户信息
@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    return current_user

# 生成API密钥
@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    api_key_create: APIKeyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # 生成API密钥
    api_key_value = generate_api_key()
    
    # 创建API密钥记录
    db_api_key = models.APIKey(
        key=api_key_value,
        user_id=current_user.id,
        name=api_key_create.name,
        expires_at=api_key_create.expires_at
    )
    
    db.add(db_api_key)
    db.commit()
    db.refresh(db_api_key)
    
    return db_api_key

# 获取用户的所有API密钥
@router.get("/api-keys", response_model=list[APIKeyResponse])
async def get_api_keys(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    api_keys = db.query(models.APIKey).filter(
        models.APIKey.user_id == current_user.id
    ).all()
    return api_keys

# 获取单个API密钥
@router.get("/api-keys/{api_key_id}", response_model=APIKeyResponse)
async def get_api_key(
    api_key_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    api_key = db.query(models.APIKey).filter(
        models.APIKey.id == api_key_id,
        models.APIKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return api_key

# 更新API密钥
@router.put("/api-keys/{api_key_id}", response_model=APIKeyResponse)
async def update_api_key(
    api_key_id: int,
    api_key_update: APIKeyUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    api_key = db.query(models.APIKey).filter(
        models.APIKey.id == api_key_id,
        models.APIKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # 更新API密钥信息
    update_data = api_key_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(api_key, field, value)
    
    db.commit()
    db.refresh(api_key)
    
    return api_key

# 删除API密钥
@router.delete("/api-keys/{api_key_id}")
async def delete_api_key(
    api_key_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    api_key = db.query(models.APIKey).filter(
        models.APIKey.id == api_key_id,
        models.APIKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    db.delete(api_key)
    db.commit()
    
    return {"message": "API key deleted successfully"}
