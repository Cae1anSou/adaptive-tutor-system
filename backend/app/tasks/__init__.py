# This file makes the tasks directory a Python package
# Import all task modules to ensure they are registered with Celery

from . import chat_tasks
from . import behavior_tasks
from . import db_tasks
from . import submission_tasks

# Explicitly import the tasks to register them
from .chat_tasks import process_chat_request
from .behavior_tasks import interpret_behavior_task
from .db_tasks import save_progress_task, save_behavior_task, log_ai_event_task, save_chat_message_task
from .submission_tasks import process_submission_task

__all__ = [
    'process_chat_request',
    'interpret_behavior_task',
    'save_progress_task',
    'save_behavior_task',
    'log_ai_event_task',
    'save_chat_message_task',
    'process_submission_task'
]