from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, FileResponse
from typing import List, Union
from schemas import *
import requests
import os

app = FastAPI()

API_KEY = 'AIzaSyCt7FJfMy6M_17EAv2rhvP0znk8_KvxVSU'
SEARCH_URL = 'https://www.googleapis.com/youtube/v3/search'


def search_youtube(query: str, language: str, safe_search: str = 'strict') -> dict:
    try:
        params = {
            'part': 'snippet',
            'q': query,
            'key': API_KEY,
            'type': 'video',
            'videoCaption': 'any',
            'relevanceLanguage': language,
            'safeSearch': safe_search,
            'maxResults': 50
        }
        response = requests.get(SEARCH_URL, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error occurred while searching YouTube: {e}")
        return {"error": str(e)}
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"error": str(e)}

def contains_harmful_keywords(text: str, harmful_keywords: List[str]) -> bool:
    return any(keyword in text.lower() for keyword in harmful_keywords)

def filter_videos(videos: dict, harmful_keywords: List[str]) -> List[Video]:
    filtered_videos = []
    for video in videos.get('items', []):
        title = video['snippet']['title']
        description = video['snippet']['description']
        
        if not contains_harmful_keywords(title, harmful_keywords) and \
           not contains_harmful_keywords(description, harmful_keywords):
            filtered_videos.append(Video(
                id=video['id'],
                snippet=VideoSnippet(
                    title=video['snippet']['title'],
                    description=video['snippet']['description']
                )
            ))
    return filtered_videos

@app.get("/search", response_model=Union[List[Video], ErrorResponse])
async def search_videos(
    query: str = Query(..., description="Search query for YouTube videos"),
    language: str = Query(..., description="Language code (e.g., 'hi' for Hindi, 'pa' for Punjabi)"),
    safe_search: str = Query('strict', description="Safe search filter (default: 'strict')")
):
    harmful_keywords = [
        'violence', 'abuse', 'assault', 'blood', 'torture', 'murder', 'fight', 'gore',
        'self-harm', 'cruelty', 'drugs', 'alcohol', 'addiction', 'narcotics', 'overdose',
        'hate', 'racism', 'sexism','sexy', 'pornography', 'explicit', 'sexual', 'adult content',
        'nudity', 'dangerous', 'risky', 'illegal', 'criminal','sex', 'scam', 'harassment',
        'bullying', 'threats', 'intimidation', 'trolling', 'depression', 'suicide',
        'self-destruction', 'extremist', 'terrorism', 'radicalization', 'hate speech', 'danger'
    ]

    # Check if the search query contains harmful keywords
    if contains_harmful_keywords(query, harmful_keywords):
        return ErrorResponse(message="The search query contains harmful keywords. Please modify your search query.")

    search_results = search_youtube(query, language, safe_search)
    
    if 'error' in search_results:
        return ErrorResponse(message=search_results['error'])
    
    safe_videos = filter_videos(search_results, harmful_keywords)
    print(safe_videos)
    return safe_videos

@app.get("/", response_class=HTMLResponse)
async def read_index():
    return FileResponse('templates/index.html')
