from fastapi import APIRouter
from app.api.endpoints import session, chat, submission, content, config, progress, knowledge_graph

api_router = APIRouter()
api_router.include_router(session.router, prefix="/session", tags=["session"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(submission.router, prefix="/submission", tags=["submission"])
api_router.include_router(content.router, tags=["learning-content", "test-tasks"])
api_router.include_router(config.router, prefix="/config", tags=["config"])
api_router.include_router(progress.router, prefix="/progress", tags=["progress"])
api_router.include_router(knowledge_graph.router, prefix="/knowledge-graph", tags=["knowledge-graph"])