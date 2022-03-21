from fastapi.responses import JSONResponse
from fastapi import FastAPI, status
from ibm_platform_services import GlobalCatalogV1
from jsonpath_ng import jsonpath, parse
from cachetools import cached

# Create a new Fast API app
from app.catalog.CatalogService import CatalogService
from app.catalog.catalog_types import Service
from typing import List

app = FastAPI()

# Create a new global catalog instance to retrieve IBM services
service_client = GlobalCatalogV1.new_instance()
catalog_service = CatalogService(service_client)


@app.get('/')
async def get_all_services():
    return catalog_service.get_public_services()


@app.get('/ibm')
async def get_ibm_services() -> List[Service]:
    return catalog_service.get_ibm_public_only_services()


@app.get('/pricing/{service_id}')
async def get_pricing(service_id):
    return catalog_service.get_pricing(service_id)

