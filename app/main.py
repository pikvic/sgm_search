from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import httpx
import re
import json
from bs4 import BeautifulSoup

class Item(BaseModel):
    name: str
    source: str
    url: str

class Query(BaseModel):
    query: str

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


templates = Jinja2Templates(directory="./app/templates")

async def search_geosociety(query: str) -> list[Item]:
    payload = '''
            {
            "operationName": "search",
            "variables": {
                "q": "gold",
                "filters": {
                "institutionId": 809
                },
                "cursor": "",
                "pageSize": 40,
                "page": "search"
            },
            "query": "query search($q: String, $cursor: String, $pageSize: Int, $page: String!, $sort: Order, $filters: SearchFiltersInput) {\n  search(\n    searchTerm: $q\n    cursor: $cursor\n    pageSize: $pageSize\n    sort: $sort\n    filters: $filters\n  ) {\n    count\n    cursor\n    sortOrder(page: $page) {\n      __typename\n      selected {\n        __typename\n        by\n        type\n      }\n      elements {\n        __typename\n        label\n        value\n      }\n    }\n    suggestions {\n      ... on ItemVersionListEntity {\n        __typename\n        id\n        title\n        version\n        openInNewTab\n        isEmbargoed\n        embargoDate\n        embargoType\n        timeline {\n          onlinePublication\n          publisherPublication\n          publisherAcceptance\n          submission\n          posted\n          revision\n        }\n        institution {\n          id\n          name\n        }\n        definedType: itemType {\n          id\n          name\n          icon\n        }\n        authors {\n          count\n          elements {\n            id\n            openInNewTab\n            name\n            urlName\n            url\n            isPublic\n            isActive\n          }\n        }\n        isConfidential\n        isMetadataRecord\n        thumb\n        url\n      }\n      ... on CollectionVersionListEntity {\n        __typename\n        id\n        title\n        version\n        timeline {\n          onlinePublication\n          publisherPublication\n          publisherAcceptance\n          submission\n          posted\n          revision\n        }\n        institution {\n          id\n          name\n        }\n        authors {\n          count\n          elements {\n            id\n            openInNewTab\n            name\n            urlName\n            url\n            isPublic\n            isActive\n          }\n        }\n        url\n      }\n      ... on ProjectListEntity {\n        __typename\n        id\n        title\n        authors {\n          count\n          elements {\n            id\n            openInNewTab\n            name\n            urlName\n            url\n            isPublic\n            isActive\n          }\n        }\n        institution {\n          id\n          name\n        }\n        url\n        publishedDate\n      }\n    }\n    items: elements {\n      ... on ItemVersionListEntity {\n        __typename\n        id\n        title\n        version\n        openInNewTab\n        isEmbargoed\n        embargoDate\n        embargoType\n        timeline {\n          onlinePublication\n          publisherPublication\n          publisherAcceptance\n          submission\n          posted\n          revision\n        }\n        institution {\n          id\n          name\n        }\n        definedType: itemType {\n          id\n          name\n          icon\n        }\n        authors {\n          count\n          elements {\n            id\n            openInNewTab\n            name\n            urlName\n            url\n            isPublic\n            isActive\n          }\n        }\n        isConfidential\n        isMetadataRecord\n        thumb\n        url\n      }\n      ... on CollectionVersionListEntity {\n        __typename\n        id\n        title\n        version\n        timeline {\n          onlinePublication\n          publisherPublication\n          publisherAcceptance\n          submission\n          posted\n          revision\n        }\n        institution {\n          id\n          name\n        }\n        authors {\n          count\n          elements {\n            id\n            openInNewTab\n            name\n            urlName\n            url\n            isPublic\n            isActive\n          }\n        }\n        url\n      }\n      ... on ProjectListEntity {\n        __typename\n        id\n        title\n        authors {\n          count\n          elements {\n            id\n            openInNewTab\n            name\n            urlName\n            url\n            isPublic\n            isActive\n          }\n        }\n        institution {\n          id\n          name\n        }\n        url\n        publishedDate\n      }\n    }\n  }\n}\n"
            }
            '''.replace("\n", " ")
    payload = json.loads(payload)
    payload["variables"]["q"] = query
    selector = 'a[tooltip="Download file"]'

    async with httpx.AsyncClient() as client:
        base_url = "https://gsapubs.figshare.com/api/graphql?thirdPartyCookies=true&type=current&operation=search"
        response = await client.post(base_url, json=payload, timeout=30)
        pages = [{"url": item["url"], "title": item["title"]} for item in response.json()["data"]["search"]["items"]]
        items = []
        for page in pages:
            response = await client.get(page["url"])
            soup = BeautifulSoup(response.text, "html.parser")
            if soup.select(selector):
                url = soup.select(selector)[0]["href"]
                item = Item(name=page["title"], source="The Geological Society of America", url=url)
                items.append(item)
        return items

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
        if not r.json().get("metadata"):
            return items
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

async def search_wiki(query: str) -> list[Item]:
    selector = '.mw-search-result-heading > a'
    async with httpx.AsyncClient() as client:
        base_url = "http://wiki.geologyscience.ru"
        url = f'{base_url}/index.php?title=Служебная:Поиск&limit=500&offset=0&ns0=1&search={query}'
        response = await client.get(url)
        items = []
        soup = BeautifulSoup(response.text, 'html.parser')
        urls =[url for url in soup.select(".mw-search-result-heading > a")]
        for url in urls:
            title = url["title"]
            url = base_url + url["href"]
            item = Item(name=title, source="Wiki Geologyscience", url=url)
            items.append(item) 
        return items

async def search_datacite(query: str) -> list[Item]:
    async with httpx.AsyncClient() as client:
        url = f'https://api.datacite.org/dois?query={query}'
        r = await client.get(url)
        items = []
        for element in r.json()["data"]:
            title = element['attributes']['titles'][0]['title']
            item_url = element['attributes']['url']
            item = Item(name=title, source="DataCite", url=item_url)
            items.append(item)
    return items

targets = {
    "datacite": {
        "title": "Поиск по международной библиотеке DataCite", 
        "heading": "Поиск по международной библиотеке DataCite",
        "func": search_datacite
    },
    "wiki": {
        "title": "Поиск по Энциклопедии \"Геология России\" ГГМ РАН", 
        "heading": "Поиск по Энциклопедии \"Геология России\" ГГМ РАН",
        "func": search_wiki
    },
    "vsegei": {
        "title": "Поиск по Государственным геологическим картам (ВСЕГЕИ)", 
        "heading": "Поиск по Государственным геологическим картам (ВСЕГЕИ)",
        "func": search_vsegei
    },
    "datasgm": {
        "title": "Поиск по Порталу открытых данных ГГМ РАН", 
        "heading": "Поиск по Порталу открытых данных ГГМ РАН",
        "func": search_datasgm
    },
    "repository": {
        "title": "Поиск по Цифровому репозиторию научных статей по геологии ГГМ РАН", 
        "heading": "Поиск по Цифровому репозиторию научных статей по геологии ГГМ РАН",
        "func": search_repository
    },
}

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/search/{target}", response_class=HTMLResponse)
async def search_get(request: Request, target: str):
    if target not in targets:
        return 404
    title = targets[target]["title"]
    heading = targets[target]["heading"]
    return templates.TemplateResponse("search.html", {"request": request, "title": title, "heading": heading})

@app.post("/search/{target}")
async def search_post(target: str, query: Query) -> list[Item]:
    if target not in targets:
        return 404
    func = targets[target]["func"]
    items = await func(query.query)
    return items

@app.get("/search")
async def search(query: str) -> list[Item]:
    repository_items = await search_repository(query)
    datasgm_items = await search_datasgm(query)
    vsegei_items = await search_vsegei(query)
    # geosociety_items = await search_geosociety(query)
    wiki_items = await search_wiki(query)
    datacite_items = await search_datacite(query)

    return repository_items + datasgm_items + vsegei_items + wiki_items + datacite_items