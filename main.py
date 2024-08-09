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


def search_youtube(query: str, language: str) -> dict:
    try:
        params = {
            'part': 'snippet',
            'q': query,
            'key': API_KEY,
            'type': 'video',
            'videoCaption': 'any',
            'relevanceLanguage': language,
            'safeSearch': 'none',
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


# def contains_harmful_keywords(text: str, harmful_keywords: List[str]) -> bool:
#     return any(keyword in text.lower() for keyword in harmful_keywords)

# def contains_allowed_categories(text: str) -> bool:
#     allowed_categories = [
#         'story', 'motivational', 'poem', 'cartoon', 'educational', 'tutorial',
#         'technology'
#     ]
#     text = text.lower()
#     return any(category in text for category in allowed_categories)


def filter_videos(videos: dict) -> List[Video]:
    filtered_videos = []

    for video in videos.get('items', []):
        video_id = video['id']['videoId']
        title = video['snippet']['title']
        description = video['snippet']['description']
        thumbnails = video['snippet']['thumbnails']

        # if not contains_allowed_categories(title) and \
        #    not contains_allowed_categories(description):
        #     continue

        # if not contains_harmful_keywords(title, harmful_keywords) and \
        #    not contains_harmful_keywords(description, harmful_keywords):
        filtered_videos.append(
            Video(id=video_id,
                  snippet=VideoSnippet(title=title,
                                       description=description,
                                       thumbnails=thumbnails)))

    return filtered_videos


def SafeSearchModel(query: str) -> str:
    api_key = os.environ['Gemini_API']
    llm = ChatGoogleGenerativeAI(model="gemini-1.0-pro", api_key=api_key)

    prompt_template = PromptTemplate(
        input_variables=["query"],
        template=
        "Determine if the following text is related to allowed categories only like stories, motivational videos, poems, cartoons, or educational videos/tutorials, technology. Respond only with 'yes' if it does and 'no' if it does not.\n\nText: \"{query}\""
    )
    formatted_prompt = prompt_template.format(query=query)

    message = HumanMessage(content=formatted_prompt)

    response = llm.invoke([message])
    response_text = response.content.strip()

    if response_text.lower() == 'yes':
        return 'Allowed'
    else:
        return 'Not Allowed'


@app.get("/search", response_model=Union[List[Video], ErrorResponse])
async def search_videos(
        query: str = Query(..., description="Search query for YouTube videos"),
        language: str = Query(
            ...,
            description="Language code (e.g., 'hi' for Hindi, 'pa' for Punjabi)"
        )):

    # harmful_keywords = [
    #     'violence', 'abuse', 'assault', 'blood', 'torture', 'murder', 'fight',
    #     'gore', 'self-harm', 'cruelty', 'drugs', 'alcohol', 'addiction',
    #     'narcotics', 'overdose', 'hate', 'racism', 'sexism', 'sexy',
    #     'pornography', 'explicit', 'sexual', 'adult content', 'nudity',
    #     'dangerous', 'risky', 'illegal', 'criminal', 'sex', 'scam',
    #     'harassment', 'bullying', 'threats', 'intimidation', 'trolling',
    #     'depression', 'suicide', 'self-destruction', 'extremist', 'terrorism',
    #     'radicalization', 'hate speech', 'danger'
    # ]

    query = query.lower()
    safe_search_result = SafeSearchModel(query)
    if safe_search_result == 'Not Allowed':
        return ErrorResponse(
            message=
            "This search query is not allowed according to YouTube's policy.")
    else:
        search_results = search_youtube(query, language)

    safe_videos = filter_videos(search_results)
    return safe_videos


@app.get("/", response_class=HTMLResponse)
async def read_index():
    return FileResponse('templates/index.html')
