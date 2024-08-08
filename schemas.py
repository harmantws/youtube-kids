from pydantic import BaseModel
from typing import Dict

class VideoSnippet(BaseModel):
    title: str
    description: str
    thumbnails: dict

class Video(BaseModel):
    id: str  # Update this to str if the ID is a string
    snippet: VideoSnippet

class ErrorResponse(BaseModel):
    message: str