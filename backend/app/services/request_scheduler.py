import asyncio
from datetime import datetime
from app.db import models
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RequestScheduler:
    """请求调度器，管理实时和任务型请求的资源分配"""
    
    def __init__(self, settings):
        # 系统状态
        self.active_realtime_requests = 0
        self.active_task_requests = 0
        self.max_concurrent_requests = settings.MAX_CONCURRENT_REQUESTS  # 从配置加载
        self.task_request_cap = settings.TASK_REQUEST_CAP  # 从配置加载
        self.latency_threshold = settings.LATENCY_THRESHOLD  # 从配置加载
        
        # 任务队列
        self.task_queue = asyncio.Queue()
        self.is_running = False
        self.settings = settings
        
    async def handle_realtime_request(self, db_request, model_provider_service, db):
        """处理实时请求"""
        start_time = datetime.utcnow()
        
        try:
            # 增加活跃实时请求计数
            self.active_realtime_requests += 1
            
            # 动态调整任务型请求的上限：根据实时请求数量精细调整
            # 实时请求越多，留给任务请求的资源越少
            if self.active_realtime_requests >= self.max_concurrent_requests * 0.7:
                # 实时请求占用了大部分资源，大幅减少任务请求上限
                self.task_request_cap = max(1, int(self.max_concurrent_requests * 0.1))
            elif self.active_realtime_requests >= self.max_concurrent_requests * 0.4:
                # 实时请求占用了较多资源，适度减少任务请求上限
                self.task_request_cap = max(2, int(self.max_concurrent_requests * 0.3))
            elif self.active_realtime_requests > 0:
                # 有少量实时请求，轻微减少任务请求上限
                self.task_request_cap = max(3, self.max_concurrent_requests - self.active_realtime_requests - 1)
            
            logger.info(f"Processing realtime request {db_request.request_id}, active_realtime: {self.active_realtime_requests}, task_cap: {self.task_request_cap}")
            
            # 更新请求状态
            db_request.status = "processing"
            db.commit()
            
            # 调用模型生成
            response = await model_provider_service.generate(
                db_request.model_config,
                db_request.prompt,
                db_request.params
            )
            
            # 计算延迟
            end_time = datetime.utcnow()
            latency = (end_time - start_time).total_seconds() * 1000
            
            # 更新请求状态
            db_request.status = "completed"
            db_request.response = response
            db_request.latency = latency
            db_request.completed_at = end_time
            db.commit()
            
            logger.info(f"Completed realtime request {db_request.request_id}, latency: {latency:.2f}ms")
            
            return response
            
        except Exception as e:
            end_time = datetime.utcnow()
            latency = (end_time - start_time).total_seconds() * 1000
            
            db_request.status = "failed"
            db_request.error = str(e)
            db_request.latency = latency
            db_request.completed_at = end_time
            db.commit()
            
            logger.error(f"Failed realtime request {db_request.request_id}: {str(e)}")
            raise
        finally:
            # 减少活跃实时请求计数
            self.active_realtime_requests = max(0, self.active_realtime_requests - 1)
            
            # 如果没有实时请求，恢复任务型请求上限，但保留一些余量
            if self.active_realtime_requests == 0:
                self.task_request_cap = self.max_concurrent_requests - 2  # 留一些余量给实时请求
            elif self.active_realtime_requests < self.max_concurrent_requests * 0.4:
                # 实时请求较少，适度增加任务请求上限
                self.task_request_cap = min(self.max_concurrent_requests - 1, self.task_request_cap + 1)
    
    async def handle_task_request(self, db_request, model_provider_service, db):
        """处理任务型请求"""
        # 添加到任务队列
        await self.task_queue.put((db_request, model_provider_service, db))
        
        # 如果调度器未运行，启动它
        if not self.is_running:
            self.is_running = True
            asyncio.create_task(self._process_task_queue())
    
    async def _process_task_queue(self):
        """处理任务队列"""
        try:
            while True:
                # 检查是否有任务需要处理
                if self.task_queue.empty():
                    self.is_running = False
                    break
                
                # 检查当前活跃任务数是否超过上限
                if self.active_task_requests >= self.task_request_cap:
                    # 等待一段时间再检查
                    await asyncio.sleep(0.1)
                    continue
                
                # 从队列中获取任务
                db_request, model_provider_service, db = await self.task_queue.get()
                
                # 处理任务
                asyncio.create_task(
                    self._execute_task_request(db_request, model_provider_service, db)
                )
                
                # 短暂等待，避免立即处理过多任务
                await asyncio.sleep(0.05)
                
        except Exception as e:
            logger.error(f"Error in task queue processor: {str(e)}")
            self.is_running = False
    
    async def _execute_task_request(self, db_request, model_provider_service, db):
        """执行单个任务请求"""
        start_time = datetime.utcnow()
        
        try:
            # 增加活跃任务请求计数
            self.active_task_requests += 1
            
            logger.info(f"Processing task request {db_request.request_id}")
            
            # 更新请求状态
            db_request.status = "processing"
            db.commit()
            
            # 调用模型生成
            response = await model_provider_service.generate(
                db_request.model_config,
                db_request.prompt,
                db_request.params
            )
            
            # 计算延迟
            end_time = datetime.utcnow()
            latency = (end_time - start_time).total_seconds() * 1000
            
            # 更新请求状态
            db_request.status = "completed"
            db_request.response = response
            db_request.latency = latency
            db_request.completed_at = end_time
            db.commit()
            
            logger.info(f"Completed task request {db_request.request_id}, latency: {latency:.2f}ms")
            
        except Exception as e:
            end_time = datetime.utcnow()
            latency = (end_time - start_time).total_seconds() * 1000
            
            db_request.status = "failed"
            db_request.error = str(e)
            db_request.latency = latency
            db_request.completed_at = end_time
            db.commit()
            
            logger.error(f"Failed task request {db_request.request_id}: {str(e)}")
        finally:
            # 减少活跃任务请求计数
            self.active_task_requests = max(0, self.active_task_requests - 1)
    
    async def update_system_stats(self, db):
        """更新系统统计信息"""
        from datetime import datetime, timedelta
        
        # 计算最近5分钟内的请求数据
        time_window = timedelta(minutes=5)
        start_time = datetime.utcnow() - time_window
        
        # 查询最近5分钟内已完成的请求
        recent_requests = db.query(models.Request).filter(
            models.Request.completed_at >= start_time,
            models.Request.status == "completed"
        ).all()
        
        # 计算平均延迟
        if recent_requests:
            total_latency = sum(req.latency or 0 for req in recent_requests)
            avg_latency = total_latency / len(recent_requests)
        else:
            avg_latency = 0.0
        
        # 计算吞吐量（请求数/秒）
        throughput = len(recent_requests) / time_window.total_seconds()
        
        # 创建系统统计记录
        stats = models.SystemStats(
            active_realtime_requests=self.active_realtime_requests,
            active_task_requests=self.active_task_requests,
            queue_length=self.task_queue.qsize(),
            avg_latency=avg_latency,
            throughput=throughput
        )
        
        db.add(stats)
        db.commit()
        
        # 如果延迟过高，动态调整任务型请求上限
        if avg_latency > self.latency_threshold:
            self.task_request_cap = max(1, self.task_request_cap - 1)
            logger.info(f"High latency detected ({avg_latency:.2f}ms), reducing task cap to {self.task_request_cap}")
        elif self.active_realtime_requests == 0 and self.task_request_cap < self.max_concurrent_requests - 1:
            # 系统空闲，增加任务型请求上限
            self.task_request_cap += 1
            logger.info(f"System idle, increasing task cap to {self.task_request_cap}")
