from fastapi.responses import JSONResponse
from fastapi import FastAPI, status
from ibm_platform_services import GlobalCatalogV1
from jsonpath_ng import jsonpath, parse
from cachetools import cached

# Create a new Fast API app
app = FastAPI()

# Create a new global catalog instance to retrieve IBM services
service_client = GlobalCatalogV1.new_instance()


@cached(cache={})
def retrieve_all_services():
    services = []
    result = get_services()
    services.extend(result['resources'])

    services = [dict(svc, **{'ui_name': get_ui_name(svc)}) for svc in services]

    while len(services) < get_total_number_of_services(result):
        result = get_services(len(services))
        services.extend(result['resources'])

    return services


def retrieve_pricing_plans(service_id):
    matching_services = [svc for svc in retrieve_all_services() if svc['id'] == service_id]
    if len(matching_services) > 0:
        # Entry found, retrieving pricing plans
        return service_client.get_catalog_entry(id=service_id, include='*', depth='*').get_result()
    else:
        return []


@cached(cache={})
def retrieve_ibm_services():
    all_services = retrieve_all_services()
    return [ibm_service for ibm_service in all_services if ibm_service['provider']['name'] == 'IBM']


def get_ui_name(svc):
    svc_i18_name_expr = parse('$.metadata.other.swagger_urls[*].i18n.en.name')
    svc_overview_ui_name_expr = parse('$.overview_ui.en.display_name')
    if len([match.value for match in svc_i18_name_expr.find(svc)]) > 0:
        return [match.value for match in svc_i18_name_expr.find(svc)][0]
    elif len([match.value for match in svc_overview_ui_name_expr.find(svc)]) > 0:
        return [match.value for match in svc_overview_ui_name_expr.find(svc)][0]
    else:
        return svc['name']


def get_services(offset=0):
    result = service_client.list_catalog_entries(
        offset=offset,
        limit=200,
        languages='en-us',
        q='kind:service active:true',
        complete=False,
        catalog=True,
    ).get_result()
    return result


def get_total_number_of_services(result):
    total_number_of_services_expr = parse('$.count')
    return [match.value for match in total_number_of_services_expr.find(result)][0]


def get_current_offset(result):
    offset_expr = parse('$.offset')
    return [match.value for match in offset_expr.find(result)][0]


def get_resource_count(result):
    resource_count_expr = parse('$.resource_count')
    return [match.value for match in resource_count_expr.find(result)][0]


@app.get('/')
async def get_all_services():
    return retrieve_all_services()


@app.get('/ibm')
async def get_ibm_services():
    return retrieve_ibm_services()


@app.get('/services/{service_id}/pricing-plans')
async def get_pricing(service_id):
    plans = retrieve_pricing_plans(service_id)
    if len(plans) > 0:
        return plans
    else:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": f"{service_id} is not a valid IBM Cloud service"})


@app.get('/pricing/{catalog_entry_id}')
async def get_pricing_details(catalog_entry_id):
    pricing = service_client.get_pricing(id=catalog_entry_id).get_result()
    return pricing


@app.get('/services/pricing-jsonpath')
async def get_pricing_jsonpath():
    return {
        'plan_id': '$.children[*].id',
        'regions_for_plan': "$.children[?(@.id == 'plan_id')].children[*].metadata.deployment.location",
        'regional_plan_deployment_id': "$.children[?(@.id == 'plan_id')].children[?(@.metadata.deployment.location == 'region')].id"
    }
