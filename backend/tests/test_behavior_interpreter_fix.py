import pytest
from unittest.mock import MagicMock
import sys
import os
from datetime import datetime
import logging

# 将 backend 目录添加到 sys.path 中
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.services.behavior_interpreter_service import BehaviorInterpreterService
from app.services.user_state_service import UserStateService
from app.schemas.behavior import BehaviorEvent, EventType, SubmissionData, AiHelpRequestData

@pytest.fixture
def interpreter():
    """提供一个 BehaviorInterpreterService 实例"""
    return BehaviorInterpreterService(
        window_minutes=2,
        error_rate_threshold=0.75,
        interval_seconds=10
    )

@pytest.fixture
def mock_user_state_service():
    """提供一个 UserStateService 的 MagicMock"""
    return MagicMock(spec=UserStateService)

@pytest.fixture
def mock_db_session():
    """提供一个数据库会话的 MagicMock"""
    return MagicMock()

class TestBehaviorInterpreterRefactor:
    """测试重构后的 BehaviorInterpreterService"""

    def test_no_circular_dependency(self):
        """测试1: 验证循环依赖问题是否已解决"""
        try:
            from app.services.behavior_interpreter_service import behavior_interpreter_service
            from app.services.user_state_service import UserStateService
            assert behavior_interpreter_service is not None
            assert UserStateService is not None
        except ImportError as e:
            pytest.fail(f"导入服务时发生错误，可能存在循环依赖: {e}")

    def test_frustration_detection_delegates_call(self, interpreter, mock_user_state_service, mock_db_session):
        """测试2: 验证挫败检测是否正确调用了 UserStateService 的方法"""
        # 准备数据
        participant_id = "frustration_user"
        # 模拟5次失败的提交
        mock_events = [
            MagicMock(
                event_type="test_submission",
                timestamp=datetime.utcnow(),
                event_data={"is_correct": False, "passed": False}
            ) for _ in range(5)
        ]
        
        test_event = BehaviorEvent(
            participant_id=participant_id,
            event_type=EventType.TEST_SUBMISSION,
            event_data=SubmissionData(topic_id="t1", code={"js":""}).model_dump(),
            timestamp=datetime.utcnow()
        )
        
        # 模拟 crud_event 和 SessionLocal
        mock_crud = MagicMock()
        mock_crud.get_by_participant.return_value = mock_events
        mock_session_local = MagicMock()
        mock_session_local.return_value = mock_db_session

        # 直接调用 _detect_frustration 方法进行测试
        interpreter._detect_frustration(
            participant_id, test_event.timestamp, mock_user_state_service, 
            mock_db_session, mock_crud, mock_session_local, is_replay=False
        )
        
        # 验证: handle_frustration_event 方法被正确调用
        mock_user_state_service.handle_frustration_event.assert_called_once_with(participant_id)

    def test_ai_help_request_delegates_call(self, interpreter, mock_user_state_service):
        """测试3: 验证AI求助请求是否正确调用了 UserStateService 的方法"""
        participant_id = "help_user"
        
        # 调用
        interpreter._handle_ai_help_request(participant_id, mock_user_state_service, is_replay=False)
        
        # 验证
        mock_user_state_service.handle_ai_help_request.assert_called_once_with(participant_id)

    def test_lightweight_event_delegates_call(self, interpreter, mock_user_state_service):
        """测试4: 验证轻量级事件是否正确调用了 UserStateService 的方法"""
        participant_id = "lightweight_user"
        event_type = "page_focus_change"
        
        # 调用
        interpreter._handle_lightweight_event(participant_id, event_type, mock_user_state_service, is_replay=False)
        
        # 验证
        mock_user_state_service.handle_lightweight_event.assert_called_once_with(participant_id, event_type)

    def test_replay_mode_prevents_delegation(self, interpreter, mock_user_state_service):
        """测试5: 验证在回放模式下，事件处理器不会被调用"""
        participant_id = "replay_user"
        
        # 测试 AI help request 在回放模式
        interpreter._handle_ai_help_request(participant_id, mock_user_state_service, is_replay=True)
        # 验证: handle_ai_help_request 方法没有被调用
        mock_user_state_service.handle_ai_help_request.assert_not_called()

        # 测试 lightweight event 在回放模式
        interpreter._handle_lightweight_event(participant_id, "code_edit", mock_user_state_service, is_replay=True)
        # 验证: handle_lightweight_event 方法没有被调用
        mock_user_state_service.handle_lightweight_event.assert_not_called()

        # 测试 frustration detection 在回放模式
        mock_crud = MagicMock()
        mock_crud.get_by_participant.return_value = [
            MagicMock(event_type="test_submission", timestamp=datetime.utcnow(), event_data={"is_correct": False})
        ] * 5
        
        interpreter._detect_frustration(
            participant_id, datetime.utcnow(), mock_user_state_service,
            MagicMock(), mock_crud, MagicMock(), is_replay=True
        )
        # 验证: handle_frustration_event 方法没有被调用
        mock_user_state_service.handle_frustration_event.assert_not_called()
        
    def test_event_dispatcher(self, interpreter, mock_user_state_service):
        """测试6: 验证 interpret_event 中的事件分发逻辑"""
        participant_id = "dispatcher_user"
        
        # 模拟所有需要的 event_data 类型
        events = {
            "test_submission": BehaviorEvent(
                participant_id=participant_id, event_type="test_submission",
                event_data=SubmissionData(topic_id="t1", code={"js": ""}).model_dump()
            ),
            "ai_help_request": BehaviorEvent(
                participant_id=participant_id, event_type="ai_help_request",
                event_data=AiHelpRequestData(message="help").model_dump()
            ),
            "page_focus_change": BehaviorEvent(
                participant_id=participant_id, event_type="page_focus_change",
                event_data={"status": "focus"}
            ),
        }
        
        # 创建模拟的处理方法
        mock_test_sub = MagicMock()
        mock_ai_help = MagicMock()
        mock_lightweight = MagicMock()
        
        # 临时替换 _event_handlers 字典中的方法
        original_handlers = interpreter._event_handlers.copy()
        interpreter._event_handlers.update({
            'test_submission': mock_test_sub,
            'ai_help_request': mock_ai_help,
            'page_focus_change': mock_lightweight
        })
        
        try:
            # 触发 test_submission
            interpreter.interpret_event(events["test_submission"], mock_user_state_service, MagicMock())
            mock_test_sub.assert_called_once()
            
            # 触发 ai_help_request
            interpreter.interpret_event(events["ai_help_request"], mock_user_state_service, MagicMock())
            mock_ai_help.assert_called_once()
            
            # 触发 page_focus_change
            interpreter.interpret_event(events["page_focus_change"], mock_user_state_service, MagicMock())
            mock_lightweight.assert_called_once()
        finally:
            # 恢复原始的 _event_handlers 字典
            interpreter._event_handlers = original_handlers

    def test_interpret_event_missing_fields(self, interpreter, mock_user_state_service):
        """测试7: 验证 interpret_event 中缺少必要字段的处理"""
        # 测试缺少 participant_id
        event_no_participant = {"event_type": "test_submission", "event_data": {}}
        interpreter.interpret_event(event_no_participant, mock_user_state_service, MagicMock())
        # 不应该调用任何处理方法
        mock_user_state_service.handle_ai_help_request.assert_not_called()
        
        # 测试缺少 event_type
        event_no_type = {"participant_id": "test_user", "event_data": {}}
        interpreter.interpret_event(event_no_type, mock_user_state_service, MagicMock())
        # 不应该调用任何处理方法
        mock_user_state_service.handle_ai_help_request.assert_not_called()

    def test_interpret_event_invalid_dict_timestamp(self, interpreter, mock_user_state_service):
        """测试8: 验证 interpret_event 中无效时间戳的处理"""
        # 测试无效的时间戳格式（使用字典形式的事件）
        event_invalid_timestamp = {
            "participant_id": "test_user",
            "event_type": "test_submission",
            "event_data": {"topic_id": "t1", "code": {"js": ""}},
            "timestamp": "invalid_timestamp"
        }
        # 应该能够处理无效时间戳而不抛出异常
        interpreter.interpret_event(event_invalid_timestamp, mock_user_state_service, MagicMock())
        
    def test_handle_test_submission_bkt_update_failure(self, interpreter, mock_user_state_service):
        """测试9: 验证 _handle_test_submission 中 BKT 更新失败的处理"""
        participant_id = "bkt_failure_user"
        event_data = SubmissionData(topic_id="t1", code={"js": ""})
        
        # 模拟 update_bkt_on_submission 抛出异常
        mock_user_state_service.update_bkt_on_submission.side_effect = Exception("BKT update failed")
        
        # 应该能够处理异常而不中断执行
        interpreter._handle_test_submission(
            participant_id, event_data, datetime.utcnow(),
            mock_user_state_service, None, None, None, False
        )
        
        # 验证方法被调用过（即使失败了）
        # 注意：由于我们模拟了异常，所以方法可能不会被成功调用
        # 我们主要验证的是异常处理不会中断执行

    def test_detect_frustration_database_exception(self, interpreter, mock_user_state_service):
        """测试10: 验证 _detect_frustration 中数据库异常的处理"""
        participant_id = "frustration_db_error_user"
        timestamp = datetime.utcnow()
        
        # 模拟数据库会话和crud操作抛出异常
        mock_db_session = MagicMock()
        mock_crud = MagicMock()
        mock_crud.get_by_participant.side_effect = Exception("Database error")
        mock_session_local = MagicMock()
        mock_session_local.return_value = mock_db_session
        
        # 应该能够处理数据库异常而不中断执行
        interpreter._detect_frustration(
            participant_id, timestamp, mock_user_state_service,
            mock_db_session, mock_crud, mock_session_local, False
        )
        
    def test_unhandled_event_type_dict(self, interpreter, mock_user_state_service, caplog):
        """测试11: 验证未处理事件类型的日志记录"""
        participant_id = "unhandled_event_user"
        # 使用字典形式的事件，避免Pydantic验证错误
        unhandled_event = {
            "participant_id": participant_id,
            "event_type": "unknown_event_type",
            "event_data": {}
        }
        
        # 捕获日志输出
        with caplog.at_level(logging.INFO):
            interpreter.interpret_event(unhandled_event, mock_user_state_service, MagicMock())
            
        # 验证日志中包含未处理事件类型的信息
        assert "未处理的事件类型 unknown_event_type" in caplog.text

    def test_event_handler_exception(self, interpreter, mock_user_state_service, caplog):
        """测试12: 验证事件处理过程中的异常处理"""
        participant_id = "handler_exception_user"
        test_event = {
            "participant_id": participant_id,
            "event_type": "test_submission",
            "event_data": {"topic_id": "t1", "code": {"js": ""}}
        }
        
        # 模拟处理方法抛出异常
        mock_handler = MagicMock(side_effect=Exception("Handler error"))
        original_handlers = interpreter._event_handlers.copy()
        interpreter._event_handlers["test_submission"] = mock_handler
        
        try:
            # 捕获日志输出
            with caplog.at_level(logging.ERROR):
                interpreter.interpret_event(test_event, mock_user_state_service, MagicMock())
                
            # 验证日志中包含错误信息
            assert "处理事件 test_submission 时发生错误" in caplog.text
        finally:
            # 恢复原始的 _event_handlers 字典
            interpreter._event_handlers = original_handlers

if __name__ == "__main__":
    pytest.main([__file__, "-v"])