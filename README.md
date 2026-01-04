# Hybrid LLM Gateway

企业级大模型调用网关，服务于中小型技术团队，开源可部署。

## 功能特性

### 核心功能
- **模型供应商接入**：支持OpenAI、Anthropic、Gemini、DeepSeek等主流模型供应商
- **调用分类支持**：
  - 实时型调用：C端用户等待，需要立即返回
  - 任务型调用：每天/周需要完成多少数量任务的计算，只要完成即可，不要求立即返回
- **智能资源调度**：
  - 当有C端请求时，减少任务调用
  - 当服务空闲时，增大任务调用
  - 大量任务调用导致延迟较高时，C端任务可立即抢占算力资源

### 辅助功能
- **权限管理**：基于JWT的用户认证和API密钥管理
- **限流保护**：基于Redis的IP限流
- **监控统计**：系统状态监控和请求统计
- **多租户支持**：用户级别的请求隔离

## 技术栈

### 后端
- **框架**：FastAPI
- **数据库**：SQLite（可扩展为PostgreSQL/MySQL）
- **缓存**：Redis
- **认证**：JWT + API Key
- **ORM**：SQLAlchemy

### 前端（待实现）
- **框架**：React + Vite
- **UI组件库**：Ant Design
- **状态管理**：Zustand
- **API请求**：Axios

## 项目结构

```
HybridLLMGateway/
├── backend/                # 后端服务
│   ├── app/                # 应用代码
│   │   ├── api/            # API路由
│   │   ├── db/             # 数据库配置和模型
│   │   ├── middleware/     # 中间件
│   │   ├── services/       # 业务逻辑服务
│   │   └── main.py         # 主应用入口
│   ├── config/             # 配置文件
│   └── requirements.txt    # 依赖列表
├── frontend/               # 前端管理端（待实现）
└── README.md               # 项目文档
```

## 快速开始

### 后端部署

1. **安装依赖**
```bash
cd backend
pip install -r requirements.txt
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑.env文件，配置数据库、Redis等信息
```

3. **启动服务**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. **访问API文档**
```
http://localhost:8000/docs  # Swagger UI
http://localhost:8000/redoc  # ReDoc
```

### 前端部署（待实现）

## API使用示例

### 1. 用户注册
```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "password123"}'
```

### 2. 用户登录
```bash
curl -X POST "http://localhost:8000/api/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=password123"
```

### 3. 创建模型配置
```bash
curl -X POST "http://localhost:8000/api/model/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider": "openai", "model_name": "gpt-3.5-turbo", "api_key": "sk-xxx"}'
```

### 4. 发送实时请求
```bash
curl -X POST "http://localhost:8000/api/request/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model_config_id": 1, "prompt": "Hello, world!", "request_type": "realtime"}'
```

### 5. 发送任务型请求
```bash
curl -X POST "http://localhost:8000/api/request/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model_config_id": 1, "prompt": "Generate a report", "request_type": "task"}'
```

## 架构设计

### 调用流程

1. **请求接收**：FastAPI接收客户端请求
2. **认证鉴权**：验证API密钥或JWT令牌
3. **请求分类**：区分实时型和任务型请求
4. **资源调度**：
   - 实时请求：立即分配资源处理
   - 任务请求：加入任务队列，根据系统负载动态分配资源
5. **模型调用**：调用相应的模型供应商API
6. **结果返回**：
   - 实时请求：立即返回结果
   - 任务请求：返回任务ID，后续可查询状态
7. **状态更新**：更新请求状态和统计信息

### 资源调度策略

- **优先级机制**：实时请求优先级高于任务请求
- **动态调整**：
  - 有实时请求时，减少任务型请求的并发数
  - 服务空闲时，增加任务型请求的并发数
  - 延迟过高时，进一步减少任务型请求
- **抢占机制**：高优先级请求可抢占低优先级请求的资源

## 监控和统计

- **系统状态**：活跃请求数、队列长度、平均延迟
- **请求统计**：总请求数、成功率、响应时间分布
- **资源使用**：CPU、内存、网络等系统资源使用情况

## 扩展建议

1. **数据库扩展**：将SQLite替换为PostgreSQL或MySQL，支持更大规模的数据
2. **缓存优化**：使用Redis集群提高缓存可靠性
3. **负载均衡**：部署多个网关实例，使用Nginx进行负载均衡
4. **监控增强**：集成Prometheus + Grafana，实现更全面的监控
5. **日志系统**：集成ELK或Loki，实现日志集中管理和分析
6. **CI/CD**：配置GitHub Actions或GitLab CI，实现自动化测试和部署

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！
