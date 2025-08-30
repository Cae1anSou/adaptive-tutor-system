# backend/app/services/behavior_interpreter_service.py
"""
BehaviorInterpreterService（行为解释服务）

- 接收前端上报的单条行为事件（BehaviorEvent 或等价 dict）
- 根据规则（例如 BKT 更新、挫败检测等）解释事件并触发 UserStateService 的具体处理（更新 BKT、设置情绪标志、创建快照等）
- 设计为容错，尽量不抛异常到 API 层

和现有模块的兼容性：
- 依赖 app.services.user_state_service.UserStateService 的方法：
    - get_or_create_profile(participant_id, db: Session = None, group="...")
    - update_bkt_on_submission(participant_id, topic_id, is_correct)
    - maybe_create_snapshot(participant_id, db, background_tasks=None)
- 依赖 app.crud.crud_event.event 中的方法：
    - get_by_participant(db, participant_id)
    - get_latest_snapshot, get_after_timestamp, get_count_after_timestamp, get_count_by_participant, get_all_snapshots
  （如果 crud 接口名称不同，需要调整）
"""

import logging
from datetime import datetime, timedelta
import traceback
from typing import Optional, Any, Dict, Callable

# 规则参数（可在这里调整或从配置中读取）
FRUSTRATION_WINDOW_MINUTES = 2
FRUSTRATION_ERROR_RATE_THRESHOLD = 0.75
FRUSTRATION_INTERVAL_SECONDS = 10

# 配置日志
logger = logging.getLogger(__name__)


class BehaviorInterpreterService:
    def __init__(self, 
                 window_minutes: int = FRUSTRATION_WINDOW_MINUTES,
                 error_rate_threshold: float = FRUSTRATION_ERROR_RATE_THRESHOLD,
                 interval_seconds: int = FRUSTRATION_INTERVAL_SECONDS):
        """
        初始化行为解释服务
        
        Args:
            window_minutes: 挫败检测时间窗口（分钟）
            error_rate_threshold: 挫败检测错误率阈值
            interval_seconds: 挫败检测时间间隔（秒）
        """
        self.window_minutes = window_minutes
        self.error_rate_threshold = error_rate_threshold
        self.interval_seconds = interval_seconds
        
        # 创建事件类型到处理方法的映射
        self._event_handlers: Dict[str, Callable] = {
            "test_submission": self._handle_test_submission,
            "ai_help_request": self._handle_ai_help_request,
            "knowledge_level_access": self._handle_knowledge_level_access,
        }
        # 添加轻量级事件的处理
        for event_type in ("dom_element_select", "code_edit", "page_focus_change", "user_idle", "page_click", "significant_edits", "large_addition", "coding_problem", "coding_session_summary", "idle_hint_displayed"):

            self._event_handlers[event_type] = self._handle_lightweight_event

    def interpret_event(self, event, user_state_service=None, db_session=None, is_replay: bool = False):
        """
        主入口：解释单条行为事件。
        
        Args:
            event: BehaviorEvent pydantic 实例或等价 dict（必须包含 participant_id, event_type, event_data, timestamp 可选）
            user_state_service: UserStateService 实例，用于状态更新操作
            db_session: 数据库会话，用于挫败检测等需要查询历史数据的操作
            is_replay: 如果为 True，表示这是从历史回放的事件（部分操作可跳过持久化等）
        """
        # --- 1. 规范输入，容错解析 event 字段 ---
        try:
            participant_id = getattr(event, "participant_id", None) or (event.get("participant_id") if isinstance(event, dict) else None)
            event_type = getattr(event, "event_type", None) or (event.get("event_type") if isinstance(event, dict) else None)
            event_data = getattr(event, "event_data", None) or (event.get("event_data") if isinstance(event, dict) else {}) or {}
            timestamp = getattr(event, "timestamp", None) or (event.get("timestamp") if isinstance(event, dict) else None)
            
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp)
                except ValueError:
                    timestamp = datetime.utcnow()
            if timestamp is None:
                timestamp = datetime.utcnow()
                
            if not participant_id or not event_type:
                logger.warning("BehaviorInterpreterService: 缺少必要字段 participant_id 或 event_type")
                return
                
            # 输出接收到的事件详情到日志
            logger.info(f"BehaviorInterpreterService: 接收到事件 - participant_id: {participant_id}, event_type: {event_type}, event_data: {event_data}")
                
        except Exception as e:
            logger.error(f"BehaviorInterpreterService: 无效的 event 输入：{event}, 错误: {e}")
            return

        # 使用字典映射来分发事件处理
        handler = self._event_handlers.get(event_type)
        if handler:
            try:
                # 为不同的处理方法提供相应的参数
                if event_type == "test_submission":
                    # 延迟导入 crud_event（用于读取历史事件以做挫败检测）
                    crud_event = None
                    SessionLocal = None
                    if db_session is None:
                        try:
                            from app.crud.crud_event import event as crud_event  
                            from app.db.database import SessionLocal
                        except ImportError as e:
                            logger.error(f"BehaviorInterpreterService: 无法导入数据库相关模块: {e}")
                            
                    handler(participant_id, event_data, timestamp, 
                           user_state_service, db_session, crud_event, SessionLocal, is_replay)
                elif event_type == "ai_help_request":
                    handler(participant_id, user_state_service, is_replay)
                elif event_type in ("dom_element_select", "code_edit", "page_focus_change", "user_idle"):
                    handler(participant_id, event_type, user_state_service, is_replay)
                elif event_type == "knowledge_level_access":
                    handler(participant_id, event_data, user_state_service, is_replay)
            except Exception as e:
                logger.error(f"BehaviorInterpreterService: 处理事件 {event_type} 时发生错误: {e}", exc_info=True)
        else:
            # 默认：不执行任何动作（原始事件仍然会写入 event_logs 以便离线分析）
            logger.info(f"BehaviorInterpreterService: 未处理的事件类型 {event_type}")
            return

    def _handle_test_submission(self, participant_id, event_data, timestamp, 
                               user_state_service, db_session, crud_event, SessionLocal, is_replay):
        """处理测试提交事件"""
        # 从 event_data 中解析 topic_id 与正确性标志
        # 处理 event_data 可能是 Pydantic 模型或字典的情况
        topic_id = getattr(event_data, "topic_id", None) or event_data.get("topic_id") or event_data.get("topic") or None
        # 支持前端可能传的字段名 is_correct 或 passed
        is_correct = None
        if "is_correct" in event_data:
            is_correct = bool(event_data.get("is_correct"))
        elif "passed" in event_data:
            is_correct = bool(event_data.get("passed"))

        # 1) 更新 BKT：优先调用 UserStateService 中的封装方法
        if user_state_service is not None and topic_id is not None and is_correct is not None:
            try:
                # 注意：update_bkt_on_submission 的签名在 user_state_service.py 中为 (participant_id, topic_id, is_correct)
                mastery = user_state_service.update_bkt_on_submission(participant_id, topic_id, is_correct)
                # TODO: 如果需要，可以把 mastery 写入日志或触发其他领域事件
            except Exception as e:
                logger.error(f"BehaviorInterpreterService: 调用 update_bkt_on_submission 失败：{e}")

        # 2) 挫败检测（使用连续挫败指数）
        # 在任何情况下都更新行为模式
        if user_state_service is not None:
            try:
                # 更新行为模式
                user_state_service.update_behavior_patterns(participant_id, "test_submission", event_data)
                
                # 根据测试结果更新情感状态
                if is_correct:
                    # 正确答案提升积极情绪
                    sentiment_update = {'positive': 0.1, 'neutral': -0.05, 'negative': -0.05}
                    user_state_service.update_emotional_state(participant_id, sentiment_update, weight=0.3)
                else:
                    # 错误答案增加消极情绪
                    sentiment_update = {'negative': 0.1, 'neutral': -0.05, 'positive': -0.05}
                    user_state_service.update_emotional_state(participant_id, sentiment_update, weight=0.3)
                    
                    # 触发挫败检测
                    if crud_event is not None and SessionLocal is not None:
                        self._detect_frustration(
                            participant_id, timestamp, user_state_service, 
                            db_session, crud_event, SessionLocal, is_replay
                        )
            except Exception as e:
                logger.error(f"BehaviorInterpreterService: 更新连续状态时发生错误: {e}")

    def _detect_frustration(self, participant_id, timestamp, user_state_service, 
                           db_session, crud_event, SessionLocal, is_replay):
        """检测用户挫败状态 - 使用连续挫败指数"""
        db = None
        try:
            # 如果没有传入 db_session，创建新的数据库会话
            if db_session is None:
                db = SessionLocal()
            else:
                db = db_session
                
            # 计算连续挫败指数
            frustration_index = user_state_service.calculate_frustration_index(participant_id)
            
            # 使用渐进式挫败响应：根据挫败指数决定响应强度
            if frustration_index > 0.7:  # 高挫败
                frustration_increase = 0.3
            elif frustration_index > 0.5:  # 中等挫败
                frustration_increase = 0.2
            elif frustration_index > 0.3:  # 轻微挫败
                frustration_increase = 0.1
            else:
                frustration_increase = 0.0  # 无明显挫败
            
            # 只有当挫败指数超过阈值时才触发事件
            if frustration_increase > 0 and not is_replay and user_state_service is not None:
                user_state_service.handle_frustration_event(participant_id, frustration_increase)
                logger.info(f"BehaviorInterpreterService: 检测到用户 {participant_id} 挫败指数 {frustration_index:.3f}, 增加挫败程度 {frustration_increase}")
            
        except Exception as e:
            logger.error(f"BehaviorInterpreterService: 挫败检测异常（非阻塞）：{e}")
            if not is_replay:
                traceback.print_exc()
        finally:
            # 只有当我们创建了新的数据库会话时才关闭它
            if db is not None and db_session is None:
                db.close()

    def _handle_ai_help_request(self, participant_id, user_state_service, is_replay):
        """处理AI求助请求事件 - 使用连续状态更新"""
        if user_state_service is None:
            return
            
        try:
            # 遵循TDD架构，调用UserStateService的新方法更新连续状态
            if not is_replay:
                user_state_service.handle_ai_help_request(participant_id)
                # 更新行为模式
                user_state_service.update_behavior_patterns(participant_id, "ai_help_request")
                
                # 更新情感状态（求助可能表示轻微挫败）
                sentiment_update = {'negative': 0.1, 'neutral': -0.05, 'positive': -0.05}
                user_state_service.update_emotional_state(participant_id, sentiment_update, weight=0.2)
                
        except Exception as e:
            logger.error(f"BehaviorInterpreterService: ai_help_request 处理异常：{e}")

    def _handle_lightweight_event(self, participant_id, event_type, user_state_service, is_replay):
        """处理轻量级事件（如页面焦点变化、代码编辑等）- 使用连续状态更新"""
        if user_state_service is None:
            return
            
        try:
            # 遵循TDD架构，调用UserStateService的新方法更新连续状态
            if not is_replay:
                user_state_service.handle_lightweight_event(participant_id, event_type)
                # 更新行为模式
                user_state_service.update_behavior_patterns(participant_id, event_type)
                
                # 根据事件类型更新情感状态
                sentiment_update = {}
                if event_type == "code_edit":
                    # 代码编辑可能表示参与度提升
                    sentiment_update = {'positive': 0.05, 'neutral': -0.03, 'negative': -0.02}
                elif event_type == "page_focus_change":
                    # 页面焦点变化可能表示注意力分散
                    sentiment_update = {'negative': 0.02, 'neutral': 0.01, 'positive': -0.03}
                elif event_type == "user_idle":
                    # 空闲可能表示参与度下降
                    sentiment_update = {'negative': 0.03, 'neutral': 0.02, 'positive': -0.05}
                
                if sentiment_update:
                    user_state_service.update_emotional_state(participant_id, sentiment_update, weight=0.1)
                
        except Exception as e:
            logger.error(f"BehaviorInterpreterService: 轻量事件处理异常：{e}")

    def _handle_knowledge_level_access(self, participant_id, event_data, user_state_service, is_replay):
        """处理知识点访问事件"""
        if user_state_service is None:
            return
        
        level = event_data.level
        action = event_data.action
        duration_ms = event_data.duration_ms
        
        logger.info(f"Participant {participant_id} accessed knowledge level {level}, action: {action}, duration: {duration_ms}ms")
        
        # 调用UserStateService更新用户模型
        if user_state_service and not is_replay:
            # Pydantic模型需要转换为字典才能传递
            user_state_service.handle_knowledge_level_access(participant_id, event_data.__dict__)


# 单例导出
behavior_interpreter_service = BehaviorInterpreterService()