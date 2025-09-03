from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.submission import Submission
from app.schemas.submission import SubmissionCreate, SubmissionUpdate

class CRUDSubmission(CRUDBase[Submission, SubmissionCreate, SubmissionUpdate]):
    pass

# 实例化并暴露给 API 层使用
submission = CRUDSubmission(Submission)