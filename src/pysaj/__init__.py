"""Python client for the SAJ Elekeeper API."""

from importlib.metadata import version as _version

__version__ = _version("pysaj-elekeeper")

from pysaj.client import SajClient
from pysaj.exceptions import SajApiError, SajAuthError, SajError
from pysaj.models import (
    BatteryInfo,
    DeviceInfo,
    DeviceOverview,
    EnergyFlow,
    LoginInfo,
    PlantInfo,
    PlantListEntry,
    PlantOverview,
    PlantStatistics,
)

__all__ = [
    "__version__",
    "BatteryInfo",
    "DeviceInfo",
    "DeviceOverview",
    "EnergyFlow",
    "LoginInfo",
    "PlantInfo",
    "PlantListEntry",
    "PlantOverview",
    "PlantStatistics",
    "SajApiError",
    "SajAuthError",
    "SajClient",
    "SajError",
]
