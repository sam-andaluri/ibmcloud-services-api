from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from enum import Enum


class VisibilityRestrictionEnum(str, Enum):
    public = 'public'
    ibm_only = 'ibm_only'


@dataclass
class Image:
    feature_image: Optional[str]
    image: Optional[str]
    medium_image: Optional[str]
    small_image: Optional[str]


@dataclass
class Service:
    ui_name: str
    active: bool
    catalog_crn: str
    disabled: bool
    geo_tags: Optional[List[str]]
    id: str
    images: List[Image]
    kind: str
    name: str
    tags: List[str]
    visibility: VisibilityRestrictionEnum
    updated: datetime
    description: str
    provider: str
    created: datetime


@dataclass
class DeploymentMetricsAmountPricePricing:
    quantity_tier: int
    price: int


@dataclass
class DeploymentMetricsAmountPricing:
    country: str
    currency: str
    prices: List[DeploymentMetricsAmountPricePricing]


@dataclass
class DeploymentMetricsPricing:
    id: str
    tier_model: str
    part_ref: str
    charge_unit: str
    charge_unit_quantity: int
    usage_cap_qty: int
    effective_from: datetime
    effective_until: datetime
    amounts: List[DeploymentMetricsAmountPricing]


@dataclass
class DeploymentPricing:
    id: str
    location: str
    type: Optional[str]
    effective_from: Optional[datetime]
    effective_until: Optional[datetime]
    metrics: List[DeploymentMetricsPricing]
    name: Optional[str]


@dataclass
class PlanPricing:
    active: bool
    catalog_crn: str
    id: str
    disabled: bool
    deployments: List[DeploymentPricing]


@dataclass
class ServicePricing:
    pricing_tags: List[str]
    catalog_crn: str
    url: str
    created: datetime
    disabled: bool
    updated: datetime
    plans: List[PlanPricing]
    geo_tags: List[str]
    service_id: str
    service_name: str
