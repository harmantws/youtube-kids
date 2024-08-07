from pydantic import BaseModel
from typing import Dict

class VideoSnippet(BaseModel):
    title: str
    description: str

class Video(BaseModel):
    id: Dict[str, str]
    snippet: VideoSnippet

class ErrorResponse(BaseModel):
    message: str