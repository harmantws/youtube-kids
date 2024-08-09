from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, FileResponse
from typing import List, Union
from schemas import *
import requests
import googleapiclient.discovery
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
import os

load_dotenv() 

app = FastAPI()

API_KEY = os.environ['Youtube_API']
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
            'regionCode': 'IN', 
            'maxResults': 100
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

def contains_any_language(text: str, languages: List[str]) -> bool:
    """
    Check if the text contains any of the specified languages.
    """
    text = text.lower()
    return any(language in text for language in languages)

def filter_videos(videos: dict, harmful_keywords: List[str]) -> List[Video]:
    filtered_videos = []

    unwanted_languages = [
        'french', 'spanish', 'german', 'italian', 'portuguese', 'chinese',
        'japanese', 'korean', 'russian', 'arabic', 'turkish', 'telugu', 'tamil',
        'bengali', 'gujarati', 'marathi', 'swahili'
    ]
    
    for video in videos.get('items', []):
        video_id = video['id']['videoId']
        title = video['snippet']['title']
        description = video['snippet']['description']
        thumbnails = video['snippet']['thumbnails']

        if contains_any_language(title, unwanted_languages):
            continue
        
        if not contains_harmful_keywords(title, harmful_keywords) and \
           not contains_harmful_keywords(description, harmful_keywords):
            filtered_videos.append(Video(
                id=video_id,
                snippet=VideoSnippet(
                    title=title,
                    description=description,
                    thumbnails=thumbnails
                )
            ))

    return filtered_videos

def SafeSearchModel(query):
    api_key = os.environ['Gemini_API']
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", api_key=api_key)

    prompt_template = PromptTemplate(
        input_variables=["query"],
        template="Determine if the following text contains any adult, bad, offensive, or vulgar content. Respond with 'yes' if it does and 'no' if it does not.\n\nText: \"{query}\""
    )
    formatted_prompt = prompt_template.format(query=query)

    message = HumanMessage(content=formatted_prompt)

    response = llm.invoke([message])
    response_text = response.content.strip()

    if response_text.lower() == 'yes':
        return 'Not Allowed'
    elif response_text.lower() == 'no':
        return 'Allowed'
    else:
        return 'Response not clear'

@app.get("/search", response_model=Union[List[Video], ErrorResponse])
async def search_videos(
    query: str = Query(..., description="Search query for YouTube videos"),
    language: str = Query(..., description="Language code (e.g., 'hi' for Hindi, 'pa' for Punjabi)"),
    safe_search: str = Query('strict', description="Safe search filter (default: 'strict')")
):
    harmful_keywords = [
        'violence', 'abuse', 'assault', 'blood', 'torture', 'murder', 'fight', 'gore',
        'self-harm', 'cruelty', 'drugs', 'alcohol', 'addiction', 'narcotics', 'overdose',
        'hate', 'racism', 'sexism', 'sexy', 'pornography', 'explicit', 'sexual', 'adult content',
        'nudity', 'dangerous', 'risky', 'illegal', 'criminal', 'sex', 'scam', 'harassment',
        'bullying', 'threats', 'intimidation', 'trolling', 'depression', 'suicide',
        'self-destruction', 'extremist', 'terrorism', 'radicalization', 'hate speech', 'danger'
    ]

    print("----",language)

    if query == 'hi':
        query = query + "| In hindi"
    elif query == 'pa':
        query = query + "| In punjabi"
    elif query == 'en':
        query = query + "| In english"

    query = query + "| In hindi or punjabi"
    safe_search_result = SafeSearchModel(query)
    if safe_search_result == 'Not Allowed':
        return ErrorResponse(message="This search query is not allowed according to YouTube's safe search policy.")
    elif safe_search_result == 'Response not clear':
        return ErrorResponse(message="This search query is not allowed according to YouTube's safe search policy. Please modify your search query.")

    search_results = search_youtube(query, language, safe_search)
    
    if 'error' in search_results:
        return ErrorResponse(message=search_results['error'])
    
    safe_videos = filter_videos(search_results, harmful_keywords)
    return safe_videos

@app.get("/", response_class=HTMLResponse)
async def read_index():
    return FileResponse('templates/index.html')
