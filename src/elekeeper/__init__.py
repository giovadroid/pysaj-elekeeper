"""Python client for the SAJ Elekeeper API."""

from importlib.metadata import version as _version

__version__ = _version("pysaj-elekeeper")

from elekeeper.client import SajClient
from elekeeper.exceptions import SajApiError, SajAuthError, SajError
from elekeeper.models import (
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
