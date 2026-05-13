"""Pretty plant summary for the first SAJ Elekeeper plant in an account.

Reads credentials from a .env file in the current directory.
Run with: python examples/plant_summary.py [--plant-uid UID] [--plant-name NAME]
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from typing import Any

from elekeeper import PlantOverview, SajClient


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plant-uid",
        help="Plant UID to summarize. Defaults to the first plant in the account.",
    )
    parser.add_argument(
        "--plant-name",
        help="Plant name to summarize. Mutually exclusive with --plant-uid.",
    )
    return parser.parse_args()


def fmt(value: Any, unit: str = "") -> str:
    if value is None or value == "":
        return "--"
    if isinstance(value, float):
        text = f"{value:.2f}".rstrip("0").rstrip(".")
    else:
        text = str(value)
    return f"{text} {unit}".strip()


def watts(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "--"
    if abs(number) >= 1000:
        return f"{number / 1000:.2f} kW"
    return f"{number:.0f} W"


def print_section(title: str, rows: dict[str, str]) -> None:
    width = max((len(key) for key in rows), default=0)
    print(f"\n{title}")
    print("-" * len(title))
    for key, value in rows.items():
        print(f"{key:<{width}} : {value}")


def print_devices(devices: PlantOverview) -> None:
    device_rows = devices.devices
    if not device_rows:
        return

    print("\nDevices")
    print("-------")
    for device in device_rows:
        print(f"- {device.serial} | {fmt(device.status)} | {fmt(device.model)}")
        print(
            "  "
            f"power {watts(device.power_w)} | "
            f"today {fmt(device.today_energy_kwh, 'kWh')} | "
            f"SOC {fmt(device.battery_soc_percent, '%')}"
        )


def print_overview(overview: PlantOverview) -> None:
    print("PySaj plant summary")
    print("===================")
    print(f"{overview.name or '--'} | {overview.uid}")

    print_section(
        "Now",
        {
            "Updated": fmt(overview.updated_at),
            "PV power": watts(overview.pv_power_w),
            "Load": watts(overview.load_power_w),
            "Grid": f"{watts(overview.grid_power_w)} ({fmt(overview.grid_direction)})",
            "Battery": f"{watts(overview.battery_power_w)} ({fmt(overview.battery_direction)})",
            "Mode": fmt(overview.mode),
        },
    )

    print_section(
        "Energy Today",
        {
            "PV": fmt(overview.today_pv_energy_kwh, "kWh"),
            "Load": fmt(overview.today_load_energy_kwh, "kWh"),
            "Grid import": fmt(overview.today_grid_import_kwh, "kWh"),
            "Grid export": fmt(overview.today_grid_export_kwh, "kWh"),
            "Battery charge": fmt(overview.today_battery_charge_kwh, "kWh"),
            "Battery discharge": fmt(overview.today_battery_discharge_kwh, "kWh"),
        },
    )

    print_section(
        "Totals",
        {
            "PV total": fmt(overview.total_pv_energy_kwh, "kWh"),
            "Load total": fmt(overview.total_load_energy_kwh, "kWh"),
            "Grid import total": fmt(overview.total_grid_import_kwh, "kWh"),
            "Grid export total": fmt(overview.total_grid_export_kwh, "kWh"),
            "Battery charge total": fmt(overview.total_battery_charge_kwh, "kWh"),
            "Battery discharge total": fmt(overview.total_battery_discharge_kwh, "kWh"),
        },
    )

    print_section(
        "Battery",
        {
            "SOC": fmt(overview.battery_soc_percent, "%"),
            "SOH": fmt(overview.battery_soh_percent, "%"),
            "Power": watts(overview.battery_power_w),
            "Voltage": fmt(overview.battery_voltage_v, "V"),
            "Current": fmt(overview.battery_current_a, "A"),
            "Temperature": fmt(overview.battery_temperature, "C"),
        },
    )

    print_devices(overview)


async def main() -> None:
    args = parse_args()
    if args.plant_uid and args.plant_name:
        raise SystemExit("Use either --plant-uid or --plant-name, not both.")

    load_env()
    username = os.environ.get("SAJ_USER")
    password = os.environ.get("SAJ_PASS")
    base_url = os.environ.get("SAJ_BASE_URL", "https://eop.saj-electric.com")
    if not username or not password:
        raise SystemExit("Missing SAJ_USER or SAJ_PASS. Create .env from .env.example.")

    async with SajClient(base_url=base_url) as client:
        await client.authenticate(username, password)
        overview = await client.get_plant_overview(args.plant_uid, plant_name=args.plant_name)

    print_overview(overview)


if __name__ == "__main__":
    asyncio.run(main())
