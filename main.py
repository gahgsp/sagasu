import os
import random
import asyncio

import aiohttp
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

load_dotenv()

API_URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY,
}


class QueryParams(BaseModel):
    query: str
    limit: int = 3
    random_seed: int = 0.5
    content_sort: str = "ASC"


async def get_example_sentence(session: aiohttp.ClientSession, word: str) -> str:
    payload: QueryParams = {
        "query": word,
        "limit": 3,
        "random_seed": round(random.uniform(0, 1), 4),
        "content_sort": "DESC",
    }

    async with session.post(API_URL, json=payload, headers=HEADERS) as resp:
        text = await resp.text()
        print(f"[DEBUG] status: {resp.status}")
        print(f"[DEBUG] response text: {text}")

        if resp.status != 200:
            return f"(Error: {resp.status})"

        try:
            data = await resp.json()
            sentences = data.get("sentences", [])
            if not sentences:
                return "(0 sentences found)"
            selected = random.choice(sentences)
            return selected["segment_info"]["content_jp_highlight"]
        except Exception as e:
            print(f"[ERROR] JSON parse or data access failed: {e}")
            return f"(Failed when processing: {str(e)})"


@app.post("/upload", response_class=HTMLResponse)
async def upload_csv(request: Request, file: UploadFile = File(...)):
    contents = await file.read()
    df = pd.read_csv(pd.io.common.BytesIO(contents), sep=";")
    words = df.iloc[:, 0].dropna().tolist()

    async with aiohttp.ClientSession() as session:
        tasks = [get_example_sentence(session, word) for word in words]
        sentences = await asyncio.gather(*tasks)

    results = list(zip(words, sentences))
    return templates.TemplateResponse(
        "results.html", {"request": request, "results": results}
    )


@app.get("/", response_class=HTMLResponse)
async def form_page(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})
