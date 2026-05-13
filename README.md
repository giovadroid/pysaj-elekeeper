# pysaj-elekeeper

[![CI](https://github.com/giovadroid/pysaj-elekeeper/actions/workflows/ci.yml/badge.svg)](https://github.com/giovadroid/pysaj-elekeeper/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pysaj-elekeeper)](https://pypi.org/project/pysaj-elekeeper/)
[![Python](https://img.shields.io/pypi/pyversions/pysaj-elekeeper)](https://pypi.org/project/pysaj-elekeeper/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-giovadroid.github.io-blue)](https://giovadroid.github.io/pysaj-elekeeper)

Async Python client for the current SAJ Elekeeper API at
`https://eop.saj-electric.com/`.

> **Looking for testers!** pysaj-elekeeper has been validated against SAJ inverters with
> serial prefixes **R5X** (on-grid) and **ASS** (AC-coupling with battery).
> If you have a different SAJ device and are willing to test, please open an
> issue — your feedback helps expand coverage.

pysaj-elekeeper targets the newer Elekeeper web API (`/dev-api/api/v1/...`) used by the
current SAJ portal. It does not use the legacy `/saj/login` cookie flow.

## Status

This package is in alpha. The implemented endpoints have been validated against
a real Elekeeper account, but the upstream API is private and can change without
notice.

## Features

- Async `httpx` client.
- Elekeeper-compatible AES password encryption.
- Elekeeper-compatible request signing.
- Login, refresh token, and logout helpers.
- Plant list and plant detail helpers.
- Power flow, energy statistics, battery, device, weather, and chart helpers.
- Raw authenticated `GET` and `POST` helpers for endpoints not wrapped yet.
- CLI discovery sample with JSONL output.
- CLI plant summary focused on relevant daily values.

## Installation

From GitHub:

```bash
python -m pip install pysaj-elekeeper
```

From a local checkout:

```bash
git clone https://github.com/giovadroid/pysaj-elekeeper.git
cd pysaj-elekeeper
uv sync --extra dev
```

Editable install without uv:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Credentials

Create a local `.env` file from the example:

```bash
cp .env.example .env
```

Then fill:

```text
SAJ_USER=your-email@example.com
SAJ_PASS=your-password
SAJ_BASE_URL=https://eop.saj-electric.com
```

## Library Usage

High-level API for normal integrations:

```python
import asyncio
import os

from elekeeper import SajClient


async def main() -> None:
    async with SajClient() as client:
        await client.authenticate(os.environ["SAJ_USER"], os.environ["SAJ_PASS"])
        overview = await client.get_plant_overview()
        # Or select explicitly:
        # overview = await client.get_plant_overview(plant_name="Home")
        # overview = await client.get_plant_overview(plant_uid="...")

        print(overview.name)
        print(overview.pv_power_w)
        print(overview.battery_soc_percent)


asyncio.run(main())
```

Lower-level endpoint wrappers are also available when you need raw Elekeeper
payloads:

```python
import asyncio
import os

from elekeeper import SajClient


async def main() -> None:
    async with SajClient() as client:
        await client.login(os.environ["SAJ_USER"], os.environ["SAJ_PASS"])

        first = await client.get_primary_plant()
        if first is None:
            return
        plant_uid = first["plantUid"]

        device_sn = await client.get_primary_device_sn(plant_uid)

        flow = await client.get_device_energy_flow(plant_uid, device_sn=device_sn)
        battery = await client.get_one_device_battery_info(device_sn) if device_sn else {}

        print(flow.get("totalPvPower"), battery.get("batEnergyPercent"))


asyncio.run(main())
```

## CLI Examples

Both examples read credentials from a `.env` file in the current directory:

```bash
cp .env.example .env
# edit SAJ_USER and SAJ_PASS
```

### Discovery sample

```bash
python examples/sample.py
python examples/sample.py --jsonl elekeeper-sample.jsonl
```

Logs in, lists plants, fetches the first plant's detail, device, battery, weather, and chart
endpoints. Prints a compact discovery summary and writes full endpoint payloads to JSONL.

### Plant summary

```bash
python examples/plant_summary.py
python examples/plant_summary.py --plant-uid <plant-uid>
python examples/plant_summary.py --plant-name <plant-name>
```

Prints relevant daily plant values:

- Current PV, load, grid, and battery power flow.
- Today's production, load, import, export, battery charge, and battery discharge.
- Lifetime plant totals.
- Battery SOC, SOH, voltage, current, temperature, and work time.
- Device rows with current power, daily production, and SOC where available.

## Wrapped Endpoints

Auth and account:

- `authenticate`
- `login`
- `refresh_access_token`
- `logout`
- `get_login_info`

Plants and home statistics:

- `list_plants`
- `get_primary_plant`
- `get_plant_by_uid`
- `get_plant_by_name`
- `get_primary_device_sn`
- `get_plant_overview`
- `get_end_user_plant_list`
- `get_plant_list`
- `get_plant_info`
- `get_plant_parallel_info`
- `get_device_energy_flow`
- `get_home_energy_statistics`
- `get_home_power_statistics`
- `get_home_plant_statistics`
- `get_plant_statistics_data`
- `get_home_battery_statistics`
- `get_home_device_statistics`

Devices and battery:

- `get_device_list`
- `get_battery_list`
- `get_one_device_info`
- `get_one_device_battery_info`
- `get_order_status_summary_report_info`

Weather and charts:

- `get_current_weather`
- `get_forecast_weather`
- `get_self_use_energy_data`
- `get_store_power_analysis_data`
- `get_store_energy_compare_data`
- `get_store_energy_balance_data`
- `get_grid_curve_analysis_data`
- `get_grid_energy_statistics_data`

Escape hatches:

- `get_raw`
- `post_raw`

## Known Limitations

- `getPlantSankeyDiagram` returned upstream `errCode=10001` for the tested
  account and is intentionally not called by the sample.
- Some endpoints require `deviceSn`; for the tested plant this came from
  `get_plant_info()["deviceSnList"][0]`.
- Some dashboard endpoints use `searchOfficeIdArr`, available from
  `get_login_info()["officeId"]`.

## API Documentation

Generated from docstrings with [pdoc](https://pdoc.dev). Hosted at
<https://giovadroid.github.io/pysaj-elekeeper>.

To generate locally:

```bash
make docs        # generate HTML → docs/api/
make docs-serve  # live preview at http://localhost:8080
```

Or directly:

```bash
uv run pdoc -o docs/api src/elekeeper
```

## Development

```bash
uv sync --extra dev
uv run ruff check .
uv run python -m pytest -q
uv build
uv run twine check dist/*
```

GitHub Actions:

- `CI` validates lint, tests, and package build on pushes and pull requests.
- `Release` builds GitHub Release artifacts when pushing a SemVer tag such as
  `v0.1.0`.
- `Publish to PyPI` is manual and uses PyPI Trusted Publishing. It is included
  for later use, but GitHub releases are the default publishing path for now.

## License

MIT
