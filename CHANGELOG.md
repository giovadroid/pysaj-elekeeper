# Changelog

## 0.0.5 - Unreleased

## 0.0.4 - 2026-05-13

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
