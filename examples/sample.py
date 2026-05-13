"""Command-line sample to inspect SAJ Elekeeper API values for an account.

Reads credentials from a .env file in the current directory.
Run with: python examples/sample.py [--jsonl elekeeper-sample.jsonl]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Self

from elekeeper import SajApiError, SajClient


def load_env(path: Path | None = None) -> None:
    env_path = path or Path.cwd() / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


@dataclass(frozen=True)
class SampleResult:
    name: str
    status: str
    data: dict[str, Any]
    error: dict[str, Any] | None = None


class JsonlRecorder:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("w", encoding="utf-8")

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._handle.close()

    def write(
        self,
        endpoint: str,
        payload: dict[str, Any],
        *,
        status: str = "ok",
        error: dict[str, Any] | None = None,
    ) -> None:
        record: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "endpoint": endpoint,
            "status": status,
            "payload": payload,
        }
        if error is not None:
            record["error"] = error
        self._handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        self._handle.flush()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--jsonl",
        type=Path,
        default=Path("elekeeper-sample.jsonl"),
        help="Path where full endpoint payloads are written as JSONL.",
    )
    return parser.parse_args()


def print_header(jsonl_path: Path, base_url: str) -> None:
    print("PySaj Elekeeper sample")
    print("======================")
    print(f"API:   {base_url}")
    print(f"JSONL: {jsonl_path}")


def print_table(title: str, rows: dict[str, Any]) -> None:
    width = max((len(k) for k in rows), default=0)
    print(f"\n{title}")
    print("-" * len(title))
    for key, value in rows.items():
        print(f"{key:<{width}} : {_fmt(value)}")


def print_result(result: SampleResult) -> None:
    marker = "[OK]" if result.status == "ok" else "[WARN]"
    print(f"{marker} {result.name}")
    if result.error:
        print(f"     {result.error.get('errCode')}: {result.error.get('errMsg')}")
        return
    highlights = _interesting_fields(result.data)
    if highlights:
        for key, value in highlights.items():
            print(f"     {key}: {_fmt(value)}")
    else:
        print(f"     keys: {', '.join(sorted(result.data.keys())) or '(empty)'}")


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:g}"
    if isinstance(value, list):
        return f"{len(value)} items"
    if isinstance(value, dict):
        return f"{len(value)} keys"
    if value is None:
        return "-"
    return str(value)


def _interesting_fields(data: dict[str, Any]) -> dict[str, Any]:
    preferred = [
        "plantName", "todayPvEnergy", "monthPvEnergy", "yearPvEnergy", "totalPvEnergy",
        "systemPower", "totalPvPower", "solarPower", "totalLoadPowerwatt", "sysGridPowerwatt",
        "batteryDirection", "gridDirection", "batteryNumTotal", "batteryOnlineRate",
        "deviceNumTotal", "deviceNumOnline", "deviceOnlineRate", "dataTime", "powerNow",
        "todayLoadEnergy", "todayBuyEnergy", "todaySellEnergy", "todayBatChgEnergy",
        "todayBatDischgEnergy", "pvEnergy", "loadEnergy", "buyEnergy", "sellEnergy",
        "chargeEnergy", "dischargeEnergy", "temperature", "weatherName", "forecastTitle",
        "xAxis", "yAxis", "deviceSn", "deviceType", "batteryNumStandby",
        "batteryNumDischarge", "batteryNumCharging", "batterySn", "batEnergyPercent",
        "batPower", "batVoltage", "batCurrent", "batTemperature", "batSohPercent",
        "batteryWorkTime", "totalEnergy", "totalEnergyUnit", "serviceNum", "finishNum",
    ]
    return {k: data[k] for k in preferred if k in data}


def _device_sns(device_list: dict[str, Any]) -> list[str]:
    sns: list[str] = []
    for device in device_list.get("list") or []:
        if isinstance(device, Mapping) and device.get("deviceSn"):
            sns.append(str(device["deviceSn"]))
    return sns


async def _capture_raw(
    name: str,
    call: Any,
    recorder: JsonlRecorder,
) -> SampleResult:
    """Capture a call that returns a raw dict."""
    try:
        data: dict[str, Any] = await call
    except SajApiError as exc:
        error = {"errCode": exc.err_code, "errMsg": exc.err_msg}
        recorder.write(name, exc.payload, status="error", error=error)
        return SampleResult(name=name, status="warn", data={}, error=error)
    recorder.write(name, data)
    return SampleResult(name=name, status="ok", data=data)


async def _capture_typed(
    name: str,
    call: Any,
    recorder: JsonlRecorder,
) -> SampleResult:
    """Capture a call that returns a typed model (uses .raw for JSONL)."""
    try:
        obj = await call
    except SajApiError as exc:
        error = {"errCode": exc.err_code, "errMsg": exc.err_msg}
        recorder.write(name, exc.payload, status="error", error=error)
        return SampleResult(name=name, status="warn", data={}, error=error)
    raw: dict[str, Any] = obj.raw if hasattr(obj, "raw") else {}
    recorder.write(name, raw)
    return SampleResult(name=name, status="ok", data=raw)


async def main() -> None:
    args = parse_args()
    load_env()

    username = os.environ.get("SAJ_USER")
    password = os.environ.get("SAJ_PASS")
    base_url = os.environ.get("SAJ_BASE_URL", "https://eop.saj-electric.com")
    if not username or not password:
        raise SystemExit("Missing SAJ_USER or SAJ_PASS. Create .env from .env.example.")

    print_header(args.jsonl, base_url)

    with JsonlRecorder(args.jsonl) as recorder:
        async with SajClient(base_url=base_url) as client:
            # Auth
            login = await client.login(username, password)
            recorder.write("login", login)
            print_table("login", {
                "has_token": bool(login.get("token")),
                "expires_in": login.get("expiresIn"),
            })

            # Account info
            login_info = await client.get_login_info()
            recorder.write("account", login_info.raw)
            print_table("account", {
                "has_plant": login_info.has_plant,
                "office_id": login_info.office_id,
            })

            # Plant list
            plants_raw = await client.get_end_user_plant_list(page_no=1, page_size=20)
            recorder.write("plants", plants_raw)
            plant_list = plants_raw.get("list") or []
            print_table("plants", {
                "total": plants_raw.get("total"),
                "returned": len(plant_list),
                "first_keys": sorted(plant_list[0].keys()) if plant_list else [],
            })

            if not plant_list:
                return

            first = plant_list[0]
            plant_uid = str(first["plantUid"])
            print_table("first plant", {
                "plantName": first.get("plantName"),
                "plantUid": plant_uid,
                "type": first.get("type"),
                "isPlant": first.get("isPlant"),
            })

            # Plant detail
            plant_info = await client.get_plant_info(plant_uid)
            recorder.write("plant_info", plant_info.raw)
            device_sn = plant_info.primary_device_sn
            today = date.today().isoformat()
            week_start = (date.today() - timedelta(days=6)).isoformat()
            print_table("plant detail", {
                "name": plant_info.name,
                "device_sns": plant_info.device_sns,
                "primary_device_sn": device_sn,
            })

            # Raw dict endpoints
            raw_calls: list[tuple[str, Any]] = [
                ("energy", client.get_home_energy_statistics(plant_uid)),
                ("power", client.get_home_power_statistics(plant_uid)),
                ("plant_statistics", client.get_home_plant_statistics(plant_uid)),
                ("battery_statistics", client.get_home_battery_statistics(plant_uid)),
                ("device_statistics", client.get_home_device_statistics(plant_uid)),
                ("plant_parallel", client.get_plant_parallel_info(plant_uid)),
                ("current_weather", client.get_current_weather(plant_uid)),
                ("forecast_weather", client.get_forecast_weather(plant_uid)),
                ("self_use_energy", client.get_self_use_energy_data(
                    plant_uid, device_sn=device_sn, chart_day=today, chart_day_end=today,
                )),
                ("store_power_analysis", client.get_store_power_analysis_data(
                    plant_uid, device_sn=device_sn,
                    chart_day=f"{today} 00:00:00", chart_day_end=f"{today} 23:59:59",
                )),
                ("store_energy_compare", client.get_store_energy_compare_data(
                    plant_uid, device_sn=device_sn,
                )),
                ("device_list", client.get_device_list(
                    plant_uid, search_office_id_arr=login_info.office_id,
                )),
                ("battery_list", client.get_battery_list(
                    plant_uid, search_office_id_arr=login_info.office_id,
                )),
            ]

            # Typed endpoints
            typed_calls: list[tuple[str, Any]] = [
                ("flow", client.get_device_energy_flow(plant_uid, device_sn=device_sn)),
                ("plant_statistics_detail", client.get_plant_statistics_data(
                    plant_uid, device_sn=device_sn,
                )),
            ]

            print("\nendpoint summary")
            print("----------------")

            for title, call in typed_calls:
                print_result(await _capture_typed(title, call, recorder))

            for title, call in raw_calls:
                result = await _capture_raw(title, call, recorder)
                print_result(result)

                if title == "device_list":
                    for sn in _device_sns(result.data):
                        await _capture_device_calls(
                            sn, plant_uid, today, week_start, client, recorder
                        )

                if title == "battery_list" and device_sn:
                    await _capture_battery_calls(
                        device_sn, today, week_start, client, recorder
                    )

    print(f"\nFull JSON payloads written to {args.jsonl}")


async def _capture_device_calls(
    sn: str,
    plant_uid: str,
    today: str,
    week_start: str,
    client: SajClient,
    recorder: JsonlRecorder,
) -> None:
    calls = [
        (f"device_info:{sn}", client.get_one_device_info(sn), True),
        (f"order_status:{sn}", client.get_order_status_summary_report_info(plant_uid, sn), False),
        (
            f"grid_curve:{sn}",
            client.get_grid_curve_analysis_data(device_sn=sn, chart_day=today),
            False,
        ),
        (
            f"grid_energy_statistics:{sn}",
            client.get_grid_energy_statistics_data(
                device_sn=sn,
                chart_week_start_day=week_start,
                chart_week_end_day=today,
            ),
            False,
        ),
    ]
    for title, call, typed in calls:
        if typed:
            print_result(await _capture_typed(title, call, recorder))
        else:
            print_result(await _capture_raw(title, call, recorder))


async def _capture_battery_calls(
    device_sn: str,
    today: str,
    week_start: str,
    client: SajClient,
    recorder: JsonlRecorder,
) -> None:
    calls = [
        (f"battery_info:{device_sn}", client.get_one_device_battery_info(device_sn), True),
        (
            f"store_energy_balance:{device_sn}",
            client.get_store_energy_balance_data(
                device_sn=device_sn,
                chart_day=today,
                chart_week_start_day=week_start,
                chart_week_end_day=today,
            ),
            False,
        ),
    ]
    for title, call, typed in calls:
        if typed:
            print_result(await _capture_typed(title, call, recorder))
        else:
            print_result(await _capture_raw(title, call, recorder))


if __name__ == "__main__":
    asyncio.run(main())
