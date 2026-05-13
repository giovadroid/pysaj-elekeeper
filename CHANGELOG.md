# Changelog

## 0.0.7 - Unreleased

- Renamed Python module from `pysaj` to `elekeeper` to avoid conflict with the
  built-in SAJ local Wi-Fi integration in Home Assistant. Install with
  `pip install pysaj-elekeeper`, import with `from elekeeper import ...`.

## 0.0.6 - 2026-05-13

- Bump version; no functional changes from 0.0.5.

- Initial public release.
- Async `SajClient` with Elekeeper-compatible AES password encryption and request signing.
- Typed models for all major endpoints: `LoginInfo`, `PlantListEntry`, `PlantInfo`,
  `EnergyFlow`, `PlantStatistics`, `DeviceInfo`, `BatteryInfo`, `PlantOverview`.
- High-level `get_plant_overview()` aggregate for dashboards and integrations.
- Plant lookup by UID or name, primary device SN resolution.
- Auth, plant, energy, weather, battery, device, and chart endpoint wrappers.
- Raw `get_raw()` / `post_raw()` escape hatches.
- CLI examples: `examples/sample.py`, `examples/plant_summary.py`.
- GitHub Actions CI pipeline: test → bump → build → release → docs.
