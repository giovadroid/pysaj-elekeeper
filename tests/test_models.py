import pytest

from elekeeper import (
    BatteryInfo,
    DeviceInfo,
    DeviceOverview,
    EnergyFlow,
    LoginInfo,
    PlantInfo,
    PlantListEntry,
    PlantOverview,
    PlantStatistics,
    SajAuthError,
    SajClient,
)

# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_authenticated_call_requires_login():
    async with SajClient() as client:
        with pytest.raises(SajAuthError):
            await client.get_login_info()


# ---------------------------------------------------------------------------
# Model constructors
# ---------------------------------------------------------------------------

def test_overview_models_are_importable():
    device = DeviceOverview(serial="device-1", power_w=1234.0)
    overview = PlantOverview(uid="plant-1", devices=[device])

    assert overview.uid == "plant-1"
    assert overview.devices[0].serial == "device-1"
    assert overview.devices[0].power_w == 1234.0


@pytest.mark.asyncio
async def test_overview_rejects_uid_and_name_together():
    client = SajClient()
    with pytest.raises(ValueError, match="either plant_uid or plant_name"):
        await client.get_plant_overview("plant-1", plant_name="Home")


# ---------------------------------------------------------------------------
# from_dict constructors
# ---------------------------------------------------------------------------

def test_login_info_from_dict():
    info = LoginInfo.from_dict({"hasPlant": 1, "officeId": "off-1"})
    assert info.has_plant is True
    assert info.office_id == "off-1"


def test_login_info_from_dict_no_plant():
    info = LoginInfo.from_dict({"hasPlant": 0})
    assert info.has_plant is False
    assert info.office_id is None


def test_plant_list_entry_from_dict():
    entry = PlantListEntry.from_dict({"plantUid": "uid-1", "plantName": "Home"})
    assert entry.uid == "uid-1"
    assert entry.name == "Home"


def test_plant_info_from_dict_device_sn_list():
    info = PlantInfo.from_dict("uid-1", {"deviceSnList": ["SN001", "SN002"]})
    assert info.device_sns == ["SN001", "SN002"]
    assert info.primary_device_sn == "SN001"


def test_plant_info_from_dict_devices_fallback():
    info = PlantInfo.from_dict("uid-1", {"devices": [{"deviceSn": "SN003"}]})
    assert info.device_sns == ["SN003"]


def test_plant_info_primary_device_sn_empty():
    info = PlantInfo.from_dict("uid-1", {})
    assert info.primary_device_sn is None


def test_energy_flow_from_dict():
    flow = EnergyFlow.from_dict({
        "totalPvPower": "3500",
        "totalLoadPowerwatt": "2100",
        "sysGridPowerwatt": "500",
        "gridDirection": "1",
        "batteryDirection": "-1",
    })
    assert flow.pv_power_w == 3500.0
    assert flow.load_power_w == 2100.0
    assert flow.grid_direction == "exporting"
    assert flow.battery_direction == "charging"


def test_plant_statistics_from_dict():
    stats = PlantStatistics.from_dict({
        "dataTime": "2026-05-13 12:00:00",
        "todayPvEnergy": "12.5",
        "totalPvEnergy": "1000",
    })
    assert stats.updated_at == "2026-05-13 12:00:00"
    assert stats.today_pv_energy_kwh == 12.5
    assert stats.total_pv_energy_kwh == 1000.0


def test_battery_info_from_dict():
    batt = BatteryInfo.from_dict({
        "batEnergyPercent": "85",
        "batSohPercent": "97",
        "batPower": "1200",
        "batteryDirection": "1",
        "userModeName": "Self-use",
    })
    assert batt.soc_percent == 85.0
    assert batt.soh_percent == 97.0
    assert batt.power_w == 1200.0
    assert batt.direction == "discharging"
    assert batt.mode == "Self-use"


def test_device_info_from_dict():
    dev = DeviceInfo.from_dict({
        "deviceSn": "SN001",
        "deviceModel": "ESAC2800-H4",
        "solarPower": "2500",
        "invTemp": "42",
        "todayAlarmNum": "0",
    })
    assert dev.serial == "SN001"
    assert dev.model == "ESAC2800-H4"
    assert dev.pv_power_w == 2500.0
    assert dev.temperature == 42.0
    assert dev.today_alarm_count == 0


def test_device_overview_from_dict():
    dev = DeviceOverview.from_dict({
        "deviceSn": "SN001",
        "powerNow": "1500",
        "batEnergyPercent": "72",
    })
    assert dev.serial == "SN001"
    assert dev.power_w == 1500.0
    assert dev.battery_soc_percent == 72.0


def test_float_fields_accept_empty_string():
    batt = BatteryInfo.from_dict({"batEnergyPercent": "", "batPower": None})
    assert batt.soc_percent is None
    assert batt.power_w is None
