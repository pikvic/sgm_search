from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

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

fake_items_db = [{"item_name": "Foo"}, {"item_name": "Bar"}, {"item_name": "Baz"}]

async def search_repository(query: str) -> list[Item]:
    async with httpx.AsyncClient() as client:
        base_url = "https://repository.geologyscience.ru"
        url = 'https://repository.geologyscience.ru/rest/items/find-by-metadata-field'
        headers = {"Accept": "application/json"}
        metadata_entry = {
            "key": "dc.subject",
            "value": query,
            "language": "ru_RU"
        }
        r = await client.post(url, headers=headers, json=metadata_entry)
        items = []
        for element in r.json():
            url2 = base_url + element["link"] + "/bitstreams"
            r2 = await client.get(url2, headers=headers)
            item_url = base_url + r2.json()[-1]["retrieveLink"]
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

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/search")
async def search(query: str) -> list[Item]:
    repository_items = await search_repository(query)
    datasgm_items = await search_datasgm(query)
    return repository_items + datasgm_items