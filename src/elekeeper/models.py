"""Typed models for the PySaj API."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Internal helpers (shared with client.py)
# ---------------------------------------------------------------------------

def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _direction(value: Any, *, negative: str, positive: str, zero: str = "idle") -> str | None:
    number = _float_or_none(value)
    if number is None:
        return None
    if number < 0:
        return negative
    if number > 0:
        return positive
    return zero


def _int_or_none(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Auth / account
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LoginInfo:
    """Account and session info returned by ``get_login_info()``."""

    has_plant: bool
    """Whether the account has at least one plant."""

    office_id: str | None = None
    """Office/organisation ID used as ``searchOfficeIdArr`` in device endpoints."""

    raw: dict[str, Any] = field(default_factory=dict, repr=False)
    """Original API payload for fields not explicitly modelled."""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LoginInfo:
        return cls(
            has_plant=bool(data.get("hasPlant")),
            office_id=str(data["officeId"]) if data.get("officeId") else None,
            raw=data,
        )


# ---------------------------------------------------------------------------
# Plants
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PlantListEntry:
    """A single plant row from the account plant list."""

    uid: str
    """Elekeeper plant UID (UUID string)."""

    name: str | None = None
    """Human-readable plant name."""

    plant_type: str | None = None
    """Plant type code as returned by Elekeeper."""

    is_plant: Any | None = None
    """Elekeeper ``isPlant`` flag."""

    raw: dict[str, Any] = field(default_factory=dict, repr=False)
    """Original API payload for fields not explicitly modelled."""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlantListEntry:
        return cls(
            uid=str(data["plantUid"]),
            name=data.get("plantName"),
            plant_type=data.get("type"),
            is_plant=data.get("isPlant"),
            raw=data,
        )


@dataclass(frozen=True)
class PlantInfo:
    """Plant detail returned by ``get_plant_info()`` (``getOnePlantInfo``)."""

    uid: str
    """Elekeeper plant UID."""

    name: str | None = None
    """Human-readable plant name."""

    device_sns: list[str] = field(default_factory=list)
    """Serial numbers of devices associated with this plant."""

    raw: dict[str, Any] = field(default_factory=dict, repr=False)
    """Original API payload for fields not explicitly modelled."""

    @property
    def primary_device_sn(self) -> str | None:
        """First device SN, used as the default for chart and detail endpoints."""
        return self.device_sns[0] if self.device_sns else None

    @classmethod
    def from_dict(cls, plant_uid: str, data: dict[str, Any]) -> PlantInfo:
        device_sns: list[str] = []
        raw_list = data.get("deviceSnList") or []
        if raw_list:
            device_sns = [str(sn) for sn in raw_list]
        else:
            for device in data.get("devices") or []:
                if isinstance(device, Mapping) and device.get("deviceSn"):
                    device_sns.append(str(device["deviceSn"]))
        return cls(
            uid=plant_uid,
            name=data.get("plantName"),
            device_sns=device_sns,
            raw=data,
        )


# ---------------------------------------------------------------------------
# Live data
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EnergyFlow:
    """Live power flow snapshot from ``get_device_energy_flow()``."""

    pv_power_w: float | None = None
    """Current PV generation in watts."""

    load_power_w: float | None = None
    """Current household load in watts."""

    grid_power_w: float | None = None
    """Current grid exchange in watts (positive = exporting, negative = importing)."""

    grid_direction: str | None = None
    """``"importing"``, ``"exporting"``, or ``"idle"``."""

    battery_direction: str | None = None
    """``"charging"``, ``"discharging"``, or ``"idle"``."""

    self_use_power_w: float | None = None
    """Self-consumption power in watts, if reported."""

    raw: dict[str, Any] = field(default_factory=dict, repr=False)
    """Original API payload for fields not explicitly modelled."""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EnergyFlow:
        return cls(
            pv_power_w=_float_or_none(data.get("totalPvPower") or data.get("solarPower")),
            load_power_w=_float_or_none(data.get("totalLoadPowerwatt")),
            grid_power_w=_float_or_none(data.get("sysGridPowerwatt")),
            grid_direction=_direction(
                data.get("gridDirection"),
                negative="importing",
                positive="exporting",
            ),
            battery_direction=_direction(
                data.get("batteryDirection"),
                negative="charging",
                positive="discharging",
            ),
            self_use_power_w=_float_or_none(data.get("selfUsePower")),
            raw=data,
        )


@dataclass(frozen=True)
class PlantStatistics:
    """Plant energy statistics from ``get_plant_statistics_data()``."""

    updated_at: str | None = None
    """Timestamp of the last data update."""

    mode: str | None = None
    """Operating mode name (e.g. ``"Self-use"``)."""

    pv_power_w: float | None = None
    """Current PV output in watts."""

    today_pv_energy_kwh: float | None = None
    today_load_energy_kwh: float | None = None
    today_grid_import_kwh: float | None = None
    today_grid_export_kwh: float | None = None
    today_battery_charge_kwh: float | None = None
    today_battery_discharge_kwh: float | None = None

    total_pv_energy_kwh: float | None = None
    total_load_energy_kwh: float | None = None
    total_grid_import_kwh: float | None = None
    total_grid_export_kwh: float | None = None
    total_battery_charge_kwh: float | None = None
    total_battery_discharge_kwh: float | None = None

    raw: dict[str, Any] = field(default_factory=dict, repr=False)
    """Original API payload for fields not explicitly modelled."""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlantStatistics:
        return cls(
            updated_at=data.get("dataTime") or data.get("updateDate"),
            mode=data.get("userModeName"),
            pv_power_w=_float_or_none(data.get("powerNow")),
            today_pv_energy_kwh=_float_or_none(data.get("todayPvEnergy")),
            today_load_energy_kwh=_float_or_none(data.get("todayLoadEnergy")),
            today_grid_import_kwh=_float_or_none(data.get("todayBuyEnergy")),
            today_grid_export_kwh=_float_or_none(data.get("todaySellEnergy")),
            today_battery_charge_kwh=_float_or_none(data.get("todayBatChgEnergy")),
            today_battery_discharge_kwh=_float_or_none(data.get("todayBatDischgEnergy")),
            total_pv_energy_kwh=_float_or_none(data.get("totalPvEnergy")),
            total_load_energy_kwh=_float_or_none(data.get("totalLoadEnergy")),
            total_grid_import_kwh=_float_or_none(data.get("totalBuyEnergy")),
            total_grid_export_kwh=_float_or_none(data.get("totalSellEnergy")),
            total_battery_charge_kwh=_float_or_none(data.get("totalBatChgEnergy")),
            total_battery_discharge_kwh=_float_or_none(data.get("totalBatDischgEnergy")),
            raw=data,
        )


# ---------------------------------------------------------------------------
# Devices
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DeviceInfo:
    """Inverter/device detail from ``get_one_device_info()``."""

    serial: str
    """Device serial number."""

    model: str | None = None
    """Device model string."""

    device_type: str | None = None
    """Elekeeper device type code."""

    status: str | None = None
    """Running state or status label."""

    mode: str | None = None
    """Operating mode name."""

    pv_power_w: float | None = None
    """Current solar input in watts."""

    temperature: float | None = None
    """Inverter temperature in °C."""

    today_alarm_count: int | None = None
    """Number of alarms raised today."""

    raw: dict[str, Any] = field(default_factory=dict, repr=False)
    """Original API payload for fields not explicitly modelled."""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceInfo:
        return cls(
            serial=str(data.get("deviceSn") or ""),
            model=data.get("deviceModel"),
            device_type=data.get("deviceType"),
            status=data.get("deviceStatus") or data.get("runningState"),
            mode=data.get("userModeName"),
            pv_power_w=_float_or_none(data.get("solarPower")),
            temperature=_float_or_none(data.get("invTemp")),
            today_alarm_count=_int_or_none(data.get("todayAlarmNum")),
            raw=data,
        )


@dataclass(frozen=True)
class BatteryInfo:
    """Battery telemetry from ``get_one_device_battery_info()``."""

    device_sn: str | None = None
    """Serial number of the battery-capable inverter."""

    soc_percent: float | None = None
    """State of charge (0–100)."""

    soh_percent: float | None = None
    """State of health (0–100)."""

    power_w: float | None = None
    """Current charge/discharge power in watts."""

    voltage_v: float | None = None
    """Battery voltage in volts."""

    current_a: float | None = None
    """Battery current in amperes."""

    temperature: float | None = None
    """Battery temperature in °C."""

    direction: str | None = None
    """``"charging"``, ``"discharging"``, or ``"idle"``."""

    mode: str | None = None
    """Operating mode name."""

    today_charge_kwh: float | None = None
    today_discharge_kwh: float | None = None
    total_charge_kwh: float | None = None
    total_discharge_kwh: float | None = None

    work_time: str | None = None
    """Cumulative battery work time as reported by Elekeeper."""

    raw: dict[str, Any] = field(default_factory=dict, repr=False)
    """Original API payload for fields not explicitly modelled."""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BatteryInfo:
        return cls(
            device_sn=data.get("deviceSn") or data.get("batterySn"),
            soc_percent=_float_or_none(data.get("batEnergyPercent")),
            soh_percent=_float_or_none(data.get("batSohPercent")),
            power_w=_float_or_none(data.get("batPower")),
            voltage_v=_float_or_none(data.get("batVoltage")),
            current_a=_float_or_none(data.get("batCurrent")),
            temperature=_float_or_none(data.get("batTemperature")),
            direction=_direction(
                data.get("batteryDirection"),
                negative="charging",
                positive="discharging",
            ),
            mode=data.get("userModeName"),
            today_charge_kwh=_float_or_none(data.get("todayBatChgEnergy")),
            today_discharge_kwh=_float_or_none(data.get("todayBatDisEnergy")),
            total_charge_kwh=_float_or_none(data.get("totalBatChgEnergy")),
            total_discharge_kwh=_float_or_none(data.get("totalBatDisEnergy")),
            work_time=str(data["batteryWorkTime"]) if data.get("batteryWorkTime") else None,
            raw=data,
        )


# ---------------------------------------------------------------------------
# High-level aggregates (unchanged API, kept at the bottom)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DeviceOverview:
    """Relevant device values for dashboards and status pages."""

    serial: str
    model: str | None = None
    status: str | None = None
    power_w: float | None = None
    today_energy_kwh: float | None = None
    battery_soc_percent: float | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceOverview:
        return cls(
            serial=str(data.get("deviceSn") or ""),
            model=data.get("deviceModel") or data.get("deviceType"),
            status=data.get("deviceStatus"),
            power_w=_float_or_none(data.get("powerNow")),
            today_energy_kwh=_float_or_none(data.get("todayEnergy")),
            battery_soc_percent=_float_or_none(data.get("batEnergyPercent")),
            raw=data,
        )


@dataclass(frozen=True)
class PlantOverview:
    """Relevant plant values collected from multiple Elekeeper endpoints.

    Returned by :meth:`~pysaj.SajClient.get_plant_overview`, which is the
    recommended entry point for dashboards and Home Assistant integrations.
    """

    uid: str
    name: str | None = None
    device_sn: str | None = None
    updated_at: str | None = None
    mode: str | None = None
    pv_power_w: float | None = None
    load_power_w: float | None = None
    grid_power_w: float | None = None
    grid_direction: str | None = None
    battery_power_w: float | None = None
    battery_direction: str | None = None
    battery_soc_percent: float | None = None
    battery_soh_percent: float | None = None
    battery_voltage_v: float | None = None
    battery_current_a: float | None = None
    battery_temperature: float | None = None
    today_pv_energy_kwh: float | None = None
    today_load_energy_kwh: float | None = None
    today_grid_import_kwh: float | None = None
    today_grid_export_kwh: float | None = None
    today_battery_charge_kwh: float | None = None
    today_battery_discharge_kwh: float | None = None
    total_pv_energy_kwh: float | None = None
    total_load_energy_kwh: float | None = None
    total_grid_import_kwh: float | None = None
    total_grid_export_kwh: float | None = None
    total_battery_charge_kwh: float | None = None
    total_battery_discharge_kwh: float | None = None
    devices: list[DeviceOverview] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)
