from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from ibm_platform_services import GlobalCatalogV1
from typing import Optional

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
async def get_pricing(service_id: str, region: Optional[str] = None):
    if region:
        pricing_for_region = catalog_service.get_pricing(service_id, region=region)
        if pricing_for_region is not None:
            return pricing_for_region
        else:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={
                'error': f'Service is not available in region {region}'
            })
    else:
        return catalog_service.get_pricing(service_id)

