from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import re

class Item(BaseModel):
    name: str
    source: str
    url: str

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def search_repository(query: str) -> list[Item]:
    async with httpx.AsyncClient() as client:
        base_url = "https://repository.geologyscience.ru"
        url = 'https://repository.geologyscience.ru/rest/items/find-by-metadata-field?expand=bitstreams'
        headers = {"Accept": "application/json"}
        metadata_entry = {
            "key": "dc.subject",
            "value": query,
            "language": "ru_RU"
        }
        
        r = await client.post(url, headers=headers, json=metadata_entry, timeout=30)
        
        items = []
        
        for element in r.json():
            if not element["bitstreams"]:
                continue
            handle = element["handle"]
            file = element["bitstreams"][-1]["name"]
            item_url = f'{base_url}/bitstream/handle/{handle}/{file}'
            item = Item(name=element["name"], source="Repository Geologyscience", url=item_url)
            items.append(item)
    return items

async def search_datasgm(query: str) -> list[Item]:
    async with httpx.AsyncClient() as client:
        base_url = "http://data.sgm.ru/api/3/action/resource_search?query=name:"
        url = f'{base_url}{query}'
        r = await client.get(url)
        items = []
        for element in r.json()["result"]["results"]:
            item_url = element["url"]
            item = Item(name=element["name"], source="Портал открытых данных ГГМ РАН", url=item_url)
            items.append(item)
    return items

async def search_vsegei(query: str) -> list[Item]:
    async with httpx.AsyncClient() as client:
        url = f"https://maps.geologyscience.ru/geonetwork/srv/rus/q?_content_type=json&any={query}&fast=index&from=1&resultType=details&sortBy=relevance&sortOrder=&to=20"
        r = await client.get(url)
        items = []
        for element in r.json()["metadata"]:
            link = element.get("link")
            item_url = None
            if not link:
                continue
            if isinstance(link, list):
                for l in link:
                     if "application/pdf" in l:
                        item_url = re.findall(r"\w+://\S+", l)[0]
                        item_url = item_url.split("|")[0]
            else:
                if "application/pdf" in l:
                    item_url = re.findall(r"\w+://\S+", l)[0]
                    item_url = item_url.split("|")[0]
            if not item_url:
                continue
            item = Item(name=element["title"], source="Государственные геологические карты ВСЕГЕИ", url=item_url)
            items.append(item)
    return items

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/search")
async def search(query: str) -> list[Item]:
    repository_items = await search_repository(query)
    datasgm_items = await search_datasgm(query)
    vsegei_items = await search_vsegei(query)
    return repository_items + datasgm_items + vsegei_items