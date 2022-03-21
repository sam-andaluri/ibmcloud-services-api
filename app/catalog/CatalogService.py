from ibm_platform_services import GlobalCatalogV1, ApiException
from jsonpath_ng import parse
from typing import Any, List, Optional
from .catalog_types import Service, VisibilityRestrictionEnum, ServicePricing, PlanPricing, DeploymentPricing
from cachetools import cached, TTLCache


def _get_total_number_of_services(result: Any):
    total_number_of_services_expr = parse('$.count')
    return [match.value for match in total_number_of_services_expr.find(result)][0]


def _get_current_offset(result: Any):
    offset_expr = parse('$.offset')
    return [match.value for match in offset_expr.find(result)][0]


def _get_resource_count(result: Any):
    resource_count_expr = parse('$.resource_count')
    return [match.value for match in resource_count_expr.find(result)][0]


def _get_ui_name(svc: Any):
    svc_i18_name_expr = parse('$.metadata.other.swagger_urls[*].i18n.en.name')
    svc_overview_ui_name_expr = parse('$.overview_ui.en.display_name')
    if len([match.value for match in svc_i18_name_expr.find(svc)]) > 0:
        return [match.value for match in svc_i18_name_expr.find(svc)][0]
    elif len([match.value for match in svc_overview_ui_name_expr.find(svc)]) > 0:
        return [match.value for match in svc_overview_ui_name_expr.find(svc)][0]
    else:
        return svc['name']


def _get_geo_tags(svc: Any):
    geo_tags_expr = parse('$.geo_tags')
    if len([match.value for match in geo_tags_expr.find(svc)]) > 0:
        return [match.value for match in geo_tags_expr.find(svc)][0]
    else:
        return []


class CatalogService:
    def __init__(self, service_client: GlobalCatalogV1):
        self.service_client = service_client

    def _get_services_from_global_catalog(self, offset: int = 0):
        result = self.service_client.list_catalog_entries(
            offset=offset,
            limit=200,
            languages='en-us',
            q='kind:service active:true',
            complete=False,
            catalog=True,
        ).get_result()
        return result

    # cache all services for no longer than 12 hours
    @cached(cache=TTLCache(maxsize=1024, ttl=43200))
    def get_all_services(self) -> List[Service]:
        services = []
        result = self._get_services_from_global_catalog()
        services.extend(result['resources'])

        while len(services) < _get_total_number_of_services(result):
            result = self._get_services_from_global_catalog(len(services))
            services.extend(result['resources'])

        normalised_services: List[Service] = [Service(
            ui_name=_get_ui_name(svc),
            active=svc['active'],
            catalog_crn=svc['catalog_crn'],
            disabled=svc['disabled'],
            geo_tags=_get_geo_tags(svc),
            id=svc['id'],
            images=svc['images'],
            updated=svc['updated'],
            visibility=svc['visibility']['restrictions'],
            name=svc['name'],
            kind=svc['kind'],
            tags=svc['tags'],
            description=svc['overview_ui']['en']['description'],
            provider=svc['provider']['name'],
            created=svc['created']
        ) for svc in services]

        return normalised_services

    def get_ibm_services(self) -> List[Service]:
        all_services = self.get_all_services()
        return [svc for svc in all_services if svc.provider.lower() == 'ibm']

    def get_public_services(self) -> List[Service]:
        all_services = self.get_all_services()
        return [svc for svc in all_services if svc.visibility == VisibilityRestrictionEnum.public]

    def get_ibm_public_only_services(self):
        ibm_services = self.get_ibm_services()
        return [svc for svc in ibm_services if svc.visibility == VisibilityRestrictionEnum.public]

    def _get_service_pricing(self, service_id: str) -> Any:
        all_services = self.get_all_services()
        matching_services = [svc for svc in all_services if svc.id == service_id]
        if len(matching_services) > 0:
            # Entry found, retrieving service pricing
            return self.service_client.get_catalog_entry(id=service_id, include='*', depth='*').get_result()
        else:
            return []

    # cache pricing for no longer than 12 hours
    @cached(cache=TTLCache(maxsize=1024, ttl=43200))
    def _get_deployment_pricing(self, catalog_entry_id: str) -> DeploymentPricing:
        deployment_json = self.service_client.get_pricing(id=catalog_entry_id).get_result()
        deployment_type = None
        if 'type' in deployment_json:
            deployment_type = deployment_json['type'].lower()

        deployment_pricing = DeploymentPricing(
            effective_from=deployment_json['effective_from'],
            effective_until=deployment_json['effective_until'],
            type=deployment_type,
            location=deployment_json['deployment_location'],
            id=deployment_json['deployment_id'],
            metrics=deployment_json['metrics'],
            name=None
        )
        return deployment_pricing

    def get_pricing(self, service_id: str, region: Optional[str] = None) -> Optional[ServicePricing]:
        full_service_pricing = self._get_service_pricing(service_id=service_id)

        geo_tags = []
        if 'geo_tags' in full_service_pricing:
            geo_tags = full_service_pricing['geo_tags']
        if len(geo_tags) > 0 and region is not None:
            if region not in geo_tags:
                print(f"Service does not operate in region {region}")
                return None

        service_plans: List[PlanPricing] = []
        for svc_plan in full_service_pricing['children']:
            print(f"Getting plan pricing for {svc_plan['id']}")
            service_deployments: List[DeploymentPricing] = []
            for svc_deployment in svc_plan['children']:
                deployment_location = ''
                if 'geo_tags' in svc_deployment:
                    if len(svc_deployment['geo_tags']) > 0:
                        deployment_location = svc_deployment['geo_tags'][0]

                if region is not None:
                    if region != deployment_location:
                        continue

                print(f"-- Getting deployment pricing for {svc_deployment['id']}")
                try:
                    deployment = self._get_deployment_pricing(svc_deployment['id'])
                    service_deployments.append(deployment)
                except ApiException as ex:
                    print(ex)
                    print(f"-- Cannot retrieve pricing for deployment id {svc_deployment['id']}")
                    print("----- Most likely because it is a non-paid plan, i.e., free or lite")
                    print("----- Adding deployment without pricing details")

                    deployment = DeploymentPricing(
                        name=svc_deployment['name'],
                        location=deployment_location,
                        metrics=[],
                        effective_from=None,
                        effective_until=None,
                        id=svc_deployment['id'],
                        type='not_paid'
                    )
                    service_deployments.append(deployment)

            plan = PlanPricing(
                catalog_crn=svc_plan['catalog_crn'],
                disabled=svc_plan['disabled'],
                active=svc_plan['active'],
                id=svc_plan['id'],
                deployments=service_deployments,
            )
            service_plans.append(plan)

        service_pricing = ServicePricing(
            created=full_service_pricing['created'],
            catalog_crn=full_service_pricing['catalog_crn'],
            disabled=full_service_pricing['disabled'],
            pricing_tags=full_service_pricing['pricing_tags'],
            updated=full_service_pricing['updated'],
            url=full_service_pricing['url'],
            geo_tags=geo_tags,
            plans=service_plans,
            service_id=full_service_pricing['id'],
            service_name=full_service_pricing['name']
        )

        return service_pricing
