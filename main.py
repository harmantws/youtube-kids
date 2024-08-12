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

def SafeSearchModel(query: str) -> str:
    api_key = os.environ['Gemini_API']
    llm = ChatGoogleGenerativeAI(model="gemini-1.0-pro", api_key=api_key)

    prompt_template = PromptTemplate(
        input_variables=["query"],
        template=(
            "You are an AI assistant that helps determine the appropriateness of search queries. "
            "The text provided should only relate to specific categories such as:\n"
            "- Motivational content\n"
            "- Educational videos or tutorials\n"
            "- Technology-related content\n"
            "- Stories or poems\n"
            "- Spiritual content\n"
            "- Cartoons\n\n"
            "If the text is related to these categories, respond with 'yes.' If it is unrelated or includes "
            "inappropriate content, respond with 'no.'\n\n"
            "Here is the text to evaluate:\n\"{query}\""
        )
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

    query = query.lower()
    safe_search_result = SafeSearchModel(query)
    if safe_search_result == 'Not Allowed':
        return ErrorResponse(
            message=
            "This search query is not allowed according to YouTube's policy.")
    else:
        search_results = search_youtube(query, language)
        return search_results

@app.get("/", response_class=HTMLResponse)
async def read_index():
    return FileResponse('templates/index.html')