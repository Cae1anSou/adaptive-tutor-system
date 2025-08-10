from typing import Dict, Any
from sqlalchemy.orm import Session
from ..crud.crud_event import event as crud_event
from ..schemas.behavior import BehaviorEvent
from datetime import datetime, timedelta, UTC

# 导入BKT模型
from ..models.bkt import BKTModel

class StudentProfile:
    def __init__(self, participant_id, is_new_user=True):
        self.participant_id = participant_id  # TODO: cxz 需要从会话或参数中获取participant_id
        self.is_new_user = is_new_user
        # 认知状态
        self.bkt_model = {}  # { 'topic_id': BKT_instance }  # TODO: cxz 需要实现BKT模型，用于追踪知识点掌握情况
        # 情感状态
        self.emotion_state = {
            'current_sentiment': 'NEUTRAL',
            # TODO: cxz 改成浮点
            'is_frustrated': False,
        }  # TODO: cxz 需要实现情感状态追踪
        # 行为状态
        self.behavior_counters = {
            'submission_timestamps': [],
            'error_count': 0,
            # TODO: cxz 补充其他需要跨请求追踪的计数器，如idle_time, focus_changes等
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """将StudentProfile序列化为字典"""
        # 序列化BKT模型
        serialized_bkt_models = {}
        for topic_id, bkt_model in self.bkt_model.items():
            if isinstance(bkt_model, BKTModel):
                serialized_bkt_models[topic_id] = bkt_model.to_dict()
            else:
                # 如果已经是字典形式（从数据库恢复时），直接使用
                serialized_bkt_models[topic_id] = bkt_model
        
        return {
            'participant_id': self.participant_id,
            'is_new_user': self.is_new_user,
            'bkt_model': serialized_bkt_models,
            'emotion_state': self.emotion_state,
            'behavior_counters': self.behavior_counters
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StudentProfile':
        """从字典反序列化创建StudentProfile"""
        # 注意：从数据库恢复的用户不是新用户
        profile = cls(data['participant_id'], is_new_user=data.get('is_new_user', False))
        
        # 反序列化BKT模型
        bkt_models = data.get('bkt_model', {})
        deserialized_bkt_models = {}
        for topic_id, bkt_data in bkt_models.items():
            if isinstance(bkt_data, dict):
                # 如果是字典形式，反序列化为BKTModel对象
                deserialized_bkt_models[topic_id] = BKTModel.from_dict(bkt_data)
            else:
                # 如果已经是BKTModel对象，直接使用
                deserialized_bkt_models[topic_id] = bkt_data
        profile.bkt_model = deserialized_bkt_models
        
        profile.emotion_state = data.get('emotion_state', {'current_sentiment': 'NEUTRAL', 'is_frustrated': False})
        profile.behavior_counters = data.get('behavior_counters', {
            'submission_timestamps': [],
            'error_count': 0,
        })
        return profile


class UserStateService:
    # 快照创建间隔（示例：每1次事件或每1分钟）
    SNAPSHOT_EVENT_INTERVAL = 1
    SNAPSHOT_TIME_INTERVAL = timedelta(minutes=1)
    
    def __init__(self):
        self._state_cache: Dict[str, StudentProfile] = {}
        # 引入解释器，用于回放
        from . import behavior_interpreter_service  # 这个文件是恩琪做的-TDD-07
        self.interpreter = behavior_interpreter_service
    
    def handle_event(self, event: BehaviorEvent, db: Session, background_tasks=None):
        """处理事件，并可能创建快照"""
        # 调用解释器处理事件
        self.interpreter.interpret_event(event)
        
        # 事件处理后，检查是否需要创建快照
        self._maybe_create_snapshot(event.participant_id, db, background_tasks)


    def get_or_create_profile(self, participant_id: str, db: Session = None, group: str = "experimental") -> tuple[StudentProfile, bool]:
        """
        获取或创建用户配置
        
        Args:
            participant_id: 参与者ID
            db: 数据库会话（可选）
            group: 实验分组，默认为'experimental'
            
        Returns:
            tuple: (profile, is_new_user)
        """
        is_new_user = False
        
        # 只有在提供了数据库会话时才检查和创建数据库记录
        if db is not None:
            from ..crud import crud_participant
            from ..schemas.participant import ParticipantCreate
            
            # 检查数据库中是否存在参与者记录
            participant = crud_participant.get(db, obj_id=participant_id)
            
            if not participant:
                # 创建新用户记录
                create_schema = ParticipantCreate(id=participant_id, group=group)
                participant = crud_participant.create(db, obj_in=create_schema)
                is_new_user = True
        
        # 获取或创建内存Profile
        if participant_id not in self._state_cache:
            print(f"INFO: Cache miss for {participant_id}. Attempting recovery from history.")
            # 只有在提供了数据库会话时才从数据库恢复状态
            if db is not None:
                # 强制从数据库恢复状态。此方法会处理老用户的状态恢复，也会为新用户创建Profile。
                self._recover_from_history_with_snapshot(participant_id, db)
            else:
                # 如果没有数据库会话，创建一个默认的新用户profile
                self._state_cache[participant_id] = StudentProfile(participant_id, is_new_user=True)
        
        # 返回profile和is_new_user标志
        profile = self._state_cache[participant_id]
        # 确保profile的is_new_user属性与数据库判断一致
        # 如果没有数据库会话，我们假设用户不是新的（因为我们无法检查）
        if db is not None:
            profile.is_new_user = is_new_user
        
        return profile, is_new_user

    def _recover_from_history_with_snapshot(self, participant_id: str, db: Session):
        # 1. 查找最新的快照
        latest_snapshot = crud_event.get_latest_snapshot(db, participant_id=participant_id)
        
        if latest_snapshot:
            # 2a. 如果找到快照，从快照恢复
            print(f"INFO: Found snapshot for {participant_id}. Restoring from snapshot...")
            # 反序列化快照数据
            profile_data = latest_snapshot.event_data
            temp_profile = StudentProfile.from_dict(profile_data)
            self._state_cache[participant_id] = temp_profile
            
            # 3a. 获取快照之后的事件
            events_after_snapshot = crud_event.get_after_timestamp(
                db, 
                participant_id=participant_id, 
                timestamp=latest_snapshot.timestamp
            )
            
            print(f"INFO: Found {len(events_after_snapshot)} events to replay after snapshot for {participant_id}.")
        else:
            # 2b. 如果没有快照，检查是否有历史事件
            print(f"INFO: No snapshot found for {participant_id}. Checking for history...")
            
            # 获取所有历史事件来判断是否是新用户
            all_history_events = crud_event.get_by_participant(db, participant_id=participant_id)
            
            if all_history_events:
                # 如果有历史事件，说明不是新用户
                print(f"INFO: Found {len(all_history_events)} historical events for {participant_id}. Not a new user.")
                temp_profile = StudentProfile(participant_id, is_new_user=False)
                self._state_cache[participant_id] = temp_profile
            else:
                # 如果没有历史事件，说明是新用户
                print(f"INFO: No history found for {participant_id}. This is a new user.")
                temp_profile = StudentProfile(participant_id, is_new_user=True)
                self._state_cache[participant_id] = temp_profile
            
            # 3b. 获取所有历史事件用于回放
            events_after_snapshot = all_history_events
            
        if not events_after_snapshot:
            print(f"INFO: No events to replay for {participant_id}.")
            return  # 没有事件需要回放
        
        # 4. 回放事件
        for event in events_after_snapshot:
            # 将数据库模型转换为Pydantic模型
            event_schema = BehaviorEvent.model_validate(event)
            # 调用解释器，但在回放模式下
            self.interpreter.interpret_event(event_schema, is_replay=True)
        
        print(f"INFO: Recovery complete for {participant_id}.")

    def _maybe_create_snapshot(self, participant_id: str, db: Session, background_tasks=None):
        """根据策略判断是否需要创建快照"""
        profile = self._state_cache.get(participant_id)
        if not profile:
            return

        # 获取最新快照信息
        latest_snapshot = crud_event.get_latest_snapshot(db, participant_id=participant_id)
        
        event_count_since_snapshot = 0
        if latest_snapshot:
            # 计算自上次快照以来的事件数量
            event_count_since_snapshot = crud_event.get_count_after_timestamp(
                db, 
                participant_id=participant_id, 
                timestamp=latest_snapshot.timestamp
            )
        else:
            # 如果没有快照，获取总事件数
            event_count_since_snapshot = crud_event.get_count_by_participant(db, participant_id=participant_id)
            
        # 检查是否满足快照创建条件
        time_since_last_snapshot = datetime.now(UTC) - (latest_snapshot.timestamp if latest_snapshot else datetime.min)
        
        if (event_count_since_snapshot >= self.SNAPSHOT_EVENT_INTERVAL or 
            time_since_last_snapshot >= self.SNAPSHOT_TIME_INTERVAL):
            
            print(f"INFO: Creating snapshot for {participant_id}...")
            
            # 创建快照事件
            snapshot_event = BehaviorEvent(
                participant_id=participant_id,
                event_type="state_snapshot",
                event_data=profile.to_dict(),
                timestamp=datetime.now(UTC)
            )
            
            # 异步保存快照
            if background_tasks:
                from fastapi import BackgroundTasks
                if isinstance(background_tasks, BackgroundTasks):
                    background_tasks.add_task(crud_event.create_from_behavior, db=db, obj_in=snapshot_event)
                else:
                    # 兼容其他后台任务机制
                    background_tasks.add_task(crud_event.create_from_behavior, db, snapshot_event)
                print(f"INFO: Snapshot scheduled for async save: {participant_id}")
            else:
                # 同步保存（备用方案）
                crud_event.create_from_behavior(db, obj_in=snapshot_event)
                print(f"INFO: Snapshot created for {participant_id}")
            
            # 清理旧快照
            self._cleanup_old_snapshots(participant_id, db)

    def _cleanup_old_snapshots(self, participant_id: str, db: Session, keep_latest: int = 3):
        """清理旧的快照，只保留最新的N个"""
        snapshots = crud_event.get_all_snapshots(db, participant_id=participant_id)
        
        if len(snapshots) > keep_latest:
            # 获取需要删除的快照
            snapshots_to_delete = snapshots[:-keep_latest]
            
            for snapshot in snapshots_to_delete:
                crud_event.remove(db, id=snapshot.id)
            
            print(f"INFO: Cleaned up {len(snapshots_to_delete)} old snapshots for {participant_id}.")

    def update_bkt_on_submission(self, participant_id: str, topic_id: str, is_correct: bool) -> float:
        """
        根据测试提交结果更新BKT模型
        
        Args:
            participant_id: 参与者ID
            topic_id: 知识点ID
            is_correct: 提交结果是否正确
            
        Returns:
            更新后的知识点掌握概率
        """
        # 获取或创建用户档案
        profile = self.get_or_create_profile(participant_id, None)  # 注意：这里可能需要传入db参数
        
        # 获取或创建该知识点的BKT模型
        if topic_id not in profile.bkt_model:
            profile.bkt_model[topic_id] = BKTModel()
            
        # 更新BKT模型
        mastery_prob = profile.bkt_model[topic_id].update(is_correct)
        
        print(f"INFO: Updated BKT model for participant {participant_id}, topic {topic_id}. "
              f"Correct: {is_correct}, New mastery probability: {mastery_prob:.3f}")
        
        return mastery_prob

    def maybe_create_snapshot(self, participant_id: str, db: Session, background_tasks=None):
        """
        公共方法，用于根据策略判断是否需要创建快照
        
        Args:
            participant_id: 参与者ID
            db: 数据库会话
            background_tasks: 后台任务（可选）
        """
        self._maybe_create_snapshot(participant_id, db, background_tasks)
