from ninja import Schema
from typing import Optional, List

class LoginIn(Schema):
    username: str
    password: str

class LoginOut(Schema):
    api_key: str
    expiry: int

class ChatIn(Schema):
    session_id: str = "default_session"
    user_input: str
    query_type: str = "analysis"  # 查询类型：analysis（日志分析）, general_chat（日常聊天）

class ChatOut(Schema):
    reply: str

class HistoryOut(Schema):
    history: str

class ErrorResponse(Schema):
    error: str


class ModelInfo(Schema):
    key: str
    name: str
    description: Optional[str] = None
    llm: str
    use_api: bool
    context_window: Optional[int] = None


class ModelsOut(Schema):
    current: str
    options: List[ModelInfo]


class ModelSwitchIn(Schema):
    model_key: str


class FileUploadOut(Schema):
    original_filename: str
    stored_filename: str
    size: int
    relative_path: str
