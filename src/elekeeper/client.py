"""Async client for the SAJ Elekeeper API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from elekeeper.crypto import encrypt_password, signed_params
from elekeeper.exceptions import SajApiError, SajAuthError
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


class SajClient:
    """Async client for `https://eop.saj-electric.com/dev-api/api/v1`."""

    def __init__(
        self,
        *,
        base_url: str = "https://eop.saj-electric.com",
        language: str = "en",
        timeout: float = 45.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_base = f"{self.base_url}/dev-api"
        self.language = language
        self._client = client or httpx.AsyncClient(timeout=timeout)
        self._owns_client = client is None
        self.token: str | None = None
        self.refresh_token: str | None = None

    async def __aenter__(self) -> SajClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    async def login(self, username: str, password: str) -> dict[str, Any]:
        """Authenticate and store the returned bearer and refresh tokens.

        Returns the raw login payload. Use :meth:`get_login_info` to get the
        typed :class:`~pysaj.LoginInfo` after logging in.
        """
        payload = {
            "username": username,
            "password": encrypt_password(password),
            "rememberMe": False,
            "loginType": 1,
        }
        data = await self._request(
            "POST",
            "/api/v1/sys/login",
            payload,
            auth=False,
            sign_only_common=True,
        )
        token = data.get("token")
        if not token:
            raise SajAuthError("Login succeeded but no token was returned")
        self.token = token
        self.refresh_token = data.get("refreshToken")
        return data

    async def authenticate(self, username: str, password: str) -> dict[str, Any]:
        """Alias for :meth:`login`."""
        return await self.login(username, password)

    async def refresh_access_token(self) -> dict[str, Any]:
        """Refresh the bearer token using the stored refresh token."""
        if not self.refresh_token:
            raise SajAuthError("No refresh token is available")
        data = await self._request(
            "POST",
            "/api/v1/sys/refreshToken",
            {"refreshToken": self.refresh_token},
            auth=False,
        )
        token = data.get("token")
        if not token:
            raise SajAuthError("Refresh succeeded but no token was returned")
        self.token = token
        self.refresh_token = data.get("refreshToken", self.refresh_token)
        return data

    async def logout(self) -> dict[str, Any]:
        """Invalidate the current session."""
        data = await self._request("POST", "/api/v1/sys/logout", {}, auth=True)
        self.token = None
        self.refresh_token = None
        return data

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    async def get_login_info(self) -> LoginInfo:
        """Return account and session info, including the office ID."""
        data = await self._request("GET", "/api/v1/sys/user/getLoginInfo")
        return LoginInfo.from_dict(data)

    # ------------------------------------------------------------------
    # Plants
    # ------------------------------------------------------------------

    async def get_end_user_plant_list(
        self, *, page_no: int = 1, page_size: int = 10
    ) -> dict[str, Any]:
        """Return the raw paginated plant list envelope."""
        return await self._request(
            "GET",
            "/api/v1/monitor/plant/getEndUserPlantList",
            {"pageNo": page_no, "pageSize": page_size},
        )

    async def list_plants(
        self, *, page: int = 1, page_size: int = 20
    ) -> list[PlantListEntry]:
        """Return the account plant list as typed :class:`~pysaj.PlantListEntry` objects."""
        data = await self.get_end_user_plant_list(page_no=page, page_size=page_size)
        return [PlantListEntry.from_dict(p) for p in (data.get("list") or [])]

    async def get_primary_plant(self) -> PlantListEntry | None:
        """Return the first plant visible to the account, if any."""
        plants = await self.list_plants(page_size=1)
        return plants[0] if plants else None

    async def get_plant_by_uid(self, plant_uid: str) -> PlantListEntry | None:
        """Return a plant by UID from the account list."""
        for plant in await self.list_plants(page_size=100):
            if plant.uid == plant_uid:
                return plant
        return None

    async def get_plant_by_name(self, name: str) -> PlantListEntry | None:
        """Return a plant by exact name (case-insensitive) from the account list."""
        wanted = name.casefold()
        for plant in await self.list_plants(page_size=100):
            if plant.name is not None and plant.name.casefold() == wanted:
                return plant
        return None

    async def get_plant_list(self, *, page_no: int = 1, page_size: int = 10) -> dict[str, Any]:
        """Raw ``getPlantList`` endpoint (office-level listing)."""
        return await self._request(
            "GET",
            "/api/v1/monitor/plant/getPlantList",
            {"pageNo": page_no, "pageSize": page_size},
        )

    async def get_plant_info(self, plant_uid: str) -> PlantInfo:
        """Return plant detail including associated device serial numbers."""
        data = await self._request(
            "GET",
            "/api/v1/monitor/plant/getOnePlantInfo",
            {"plantUid": plant_uid},
        )
        return PlantInfo.from_dict(plant_uid, data)

    async def get_primary_device_sn(self, plant_uid: str) -> str | None:
        """Return the first device serial used by plant detail and chart endpoints."""
        return (await self.get_plant_info(plant_uid)).primary_device_sn

    # ------------------------------------------------------------------
    # High-level aggregate
    # ------------------------------------------------------------------

    async def get_plant_overview(
        self,
        plant_uid: str | None = None,
        *,
        plant_name: str | None = None,
        device_sn: str | None = None,
        search_office_id_arr: str | None = None,
    ) -> PlantOverview:
        """Return a fully populated :class:`~pysaj.PlantOverview`.

        This is the recommended entry point for dashboards and integrations.
        It calls several Elekeeper endpoints internally and aggregates the
        results into a single typed object.

        Args:
            plant_uid: Target plant UID. Defaults to the first plant in the account.
            plant_name: Target plant by name (case-insensitive). Mutually exclusive
                with ``plant_uid``.
            device_sn: Override the device serial used for detail endpoints.
            search_office_id_arr: Override the office ID used for device listing.
                Fetched automatically from :meth:`get_login_info` when omitted.
        """
        if plant_uid and plant_name:
            raise ValueError("Use either plant_uid or plant_name, not both")

        selected_plant: PlantListEntry | None = None
        if plant_name is not None:
            selected_plant = await self.get_plant_by_name(plant_name)
            if not selected_plant:
                raise SajApiError("plant_not_found", f"No plant named {plant_name!r} was found")
            plant_uid = selected_plant.uid
        elif plant_uid is not None:
            selected_plant = await self.get_plant_by_uid(plant_uid)
        else:
            selected_plant = await self.get_primary_plant()
            if not selected_plant:
                raise SajApiError("no_plant", "No plants found for this account")
            plant_uid = selected_plant.uid

        login_info: LoginInfo | None = None
        if search_office_id_arr is None:
            login_info = await self.get_login_info()
            search_office_id_arr = login_info.office_id

        plant_info = await self.get_plant_info(plant_uid)
        device_sn = device_sn or plant_info.primary_device_sn

        stats = await self.get_plant_statistics_data(plant_uid, device_sn=device_sn)
        flow = await self.get_device_energy_flow(plant_uid, device_sn=device_sn)
        battery = await self.get_one_device_battery_info(device_sn) if device_sn else None
        device_list_raw = await self._get_device_list_raw(
            plant_uid, search_office_id_arr=search_office_id_arr
        )

        return PlantOverview(
            uid=plant_uid,
            name=(selected_plant.name if selected_plant else None) or plant_info.name,
            device_sn=device_sn,
            updated_at=stats.updated_at,
            mode=battery.mode if battery else stats.mode,
            pv_power_w=stats.pv_power_w or flow.pv_power_w,
            load_power_w=flow.load_power_w,
            grid_power_w=flow.grid_power_w,
            grid_direction=flow.grid_direction,
            battery_power_w=battery.power_w if battery else None,
            battery_direction=battery.direction if battery else None,
            battery_soc_percent=battery.soc_percent if battery else None,
            battery_soh_percent=battery.soh_percent if battery else None,
            battery_voltage_v=battery.voltage_v if battery else None,
            battery_current_a=battery.current_a if battery else None,
            battery_temperature=battery.temperature if battery else None,
            today_pv_energy_kwh=stats.today_pv_energy_kwh,
            today_load_energy_kwh=stats.today_load_energy_kwh,
            today_grid_import_kwh=stats.today_grid_import_kwh,
            today_grid_export_kwh=stats.today_grid_export_kwh,
            today_battery_charge_kwh=stats.today_battery_charge_kwh,
            today_battery_discharge_kwh=stats.today_battery_discharge_kwh,
            total_pv_energy_kwh=stats.total_pv_energy_kwh,
            total_load_energy_kwh=stats.total_load_energy_kwh,
            total_grid_import_kwh=stats.total_grid_import_kwh,
            total_grid_export_kwh=stats.total_grid_export_kwh,
            total_battery_charge_kwh=stats.total_battery_charge_kwh,
            total_battery_discharge_kwh=stats.total_battery_discharge_kwh,
            devices=[
                DeviceOverview.from_dict(d)
                for d in (device_list_raw.get("list") or [])
                if isinstance(d, Mapping) and d.get("deviceSn")
            ],
            raw={
                "login_info": login_info.raw if login_info else {},
                "plant": selected_plant.raw if selected_plant else {},
                "plant_info": plant_info.raw,
                "stats": stats.raw,
                "flow": flow.raw,
                "battery": battery.raw if battery else {},
                "device_list": device_list_raw,
            },
        )

    # ------------------------------------------------------------------
    # Plant endpoints
    # ------------------------------------------------------------------

    async def get_plant_parallel_info(self, plant_uid: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/api/v1/monitor/plant/getPlantParallelInfo",
            {"plantUid": plant_uid},
        )

    # ------------------------------------------------------------------
    # Weather
    # ------------------------------------------------------------------

    async def get_current_weather(
        self, plant_uid: str, *, forecast_type: int = 1
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/api/v1/monitor/weather/getCurrentWeather",
            {"plantUid": plant_uid, "forecastType": forecast_type},
        )

    async def get_forecast_weather(
        self, plant_uid: str, *, forecast_type: int = 2
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/api/v1/monitor/weather/getForecastWeather",
            {"plantUid": plant_uid, "forecastType": forecast_type},
        )

    # ------------------------------------------------------------------
    # Energy / power / statistics
    # ------------------------------------------------------------------

    async def get_device_energy_flow(
        self, plant_uid: str, *, device_sn: str | None = None
    ) -> EnergyFlow:
        """Return the live power flow snapshot."""
        data = await self._home_get("getDeviceEneryFlowData", plant_uid, device_sn=device_sn)
        return EnergyFlow.from_dict(data)

    async def get_plant_statistics_data(
        self,
        plant_uid: str,
        *,
        device_sn: str | None = None,
        refresh: int | None = None,
    ) -> PlantStatistics:
        """Return today and cumulative energy statistics for the plant."""
        data = await self._home_get(
            "getPlantStatisticsData",
            plant_uid,
            device_sn=device_sn,
            extra={"refresh": refresh},
        )
        return PlantStatistics.from_dict(data)

    async def get_home_energy_statistics(self, plant_uid: str) -> dict[str, Any]:
        return await self._home_get("getHomeEneryStatisticsData", plant_uid)

    async def get_home_plant_statistics(self, plant_uid: str) -> dict[str, Any]:
        return await self._home_get("getHomePlantStatisticsData", plant_uid)

    async def get_home_power_statistics(self, plant_uid: str) -> dict[str, Any]:
        return await self._home_get("getHomePowerStatisticsData", plant_uid)

    async def get_home_battery_statistics(self, plant_uid: str) -> dict[str, Any]:
        return await self._home_get("getHomeBatteryStatisticsData", plant_uid)

    async def get_home_device_statistics(self, plant_uid: str) -> dict[str, Any]:
        return await self._home_get("getHomeDeviceStatisticsData", plant_uid)

    # ------------------------------------------------------------------
    # Devices
    # ------------------------------------------------------------------

    async def get_device_list(
        self,
        plant_uid: str,
        *,
        page_no: int = 1,
        page_size: int = 10,
        search_office_id_arr: str | None = None,
    ) -> dict[str, Any]:
        """Return the raw paginated device list envelope."""
        return await self._get_device_list_raw(
            plant_uid,
            page_no=page_no,
            page_size=page_size,
            search_office_id_arr=search_office_id_arr,
        )

    async def get_battery_list(
        self,
        plant_uid: str,
        *,
        page_no: int = 1,
        page_size: int = 10,
        search_office_id_arr: str | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/api/v1/monitor/battery/getBatteryList",
            {
                "plantUid": plant_uid,
                "pageNo": page_no,
                "pageSize": page_size,
                "searchOfficeIdArr": search_office_id_arr,
            },
        )

    async def get_one_device_info(self, device_sn: str) -> DeviceInfo:
        """Return inverter detail for a single device."""
        data = await self._request(
            "GET",
            "/api/v1/monitor/device/getOneDeviceInfo",
            {"deviceSn": device_sn},
        )
        return DeviceInfo.from_dict(data)

    async def get_one_device_battery_info(self, device_sn: str) -> BatteryInfo:
        """Return live battery telemetry for a battery-capable inverter."""
        data = await self._request(
            "GET",
            "/api/v1/monitor/battery/getOneDeviceBatteryInfo",
            {"deviceSn": device_sn},
        )
        return BatteryInfo.from_dict(data)

    async def get_order_status_summary_report_info(
        self,
        plant_uid: str,
        device_sn: str,
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/api/v1/yw/order/getOrderStatusSummaryReporInfo",
            {"plantUid": plant_uid, "deviceSn": device_sn},
        )

    # ------------------------------------------------------------------
    # Charts / historical data (raw — structure varies per endpoint)
    # ------------------------------------------------------------------

    async def get_self_use_energy_data(
        self,
        plant_uid: str,
        *,
        chart_date_type: int = 1,
        chart_day: str | None = None,
        chart_day_end: str | None = None,
        device_sn: str | None = None,
        custom_search: int = 1,
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/api/v1/monitor/plant/chart/getSelfUseEnergyData",
            {
                "plantUid": plant_uid,
                "deviceSn": device_sn,
                "chartDateType": chart_date_type,
                "chartDay": chart_day,
                "chartDayEnd": chart_day_end,
                "customSearch": custom_search,
            },
        )

    async def get_store_power_analysis_data(
        self,
        plant_uid: str,
        *,
        chart_day: str | None = None,
        chart_day_end: str | None = None,
        device_sn: str | None = None,
        custom_search: int = 1,
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/api/v1/monitor/plant/chart/getStorePowerAnalysisData",
            {
                "plantUid": plant_uid,
                "chartDay": chart_day,
                "chartDayEnd": chart_day_end,
                "customSearch": custom_search,
                "deviceSn": device_sn,
            },
        )

    async def get_store_energy_compare_data(
        self,
        plant_uid: str,
        *,
        device_sn: str | None = None,
        chart_compare_type: int = 1,
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/api/v1/monitor/plant/chart/getStoreEnergyCompareData",
            {
                "plantUid": plant_uid,
                "chartCompareType": chart_compare_type,
                "deviceSn": device_sn,
            },
        )

    async def get_store_energy_balance_data(
        self,
        *,
        device_sn: str,
        chart_date_type: int = 1,
        chart_day: str | None = None,
        chart_week_start_day: str | None = None,
        chart_week_end_day: str | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/api/v1/monitor/plant/chart/getStoreEnergyBalanceData",
            {
                "chartDateType": chart_date_type,
                "deviceSn": device_sn,
                "chartDay": chart_day,
                "chartWeekStartDay": chart_week_start_day,
                "chartWeekEndDay": chart_week_end_day,
            },
        )

    async def get_grid_curve_analysis_data(
        self,
        *,
        device_sn: str,
        chart_date_type: int = 1,
        chart_day: str | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/api/v1/monitor/plant/chart/getGridCurveAnalysisData",
            {
                "chartDay": chart_day,
                "deviceSn": device_sn,
                "chartDateType": chart_date_type,
            },
        )

    async def get_grid_energy_statistics_data(
        self,
        *,
        device_sn: str,
        chart_date_type: int = 2,
        chart_week_start_day: str | None = None,
        chart_week_end_day: str | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/api/v1/monitor/plant/chart/getGridEnergyStatisticsData",
            {
                "chartDateType": chart_date_type,
                "deviceSn": device_sn,
                "chartWeekStartDay": chart_week_start_day,
                "chartWeekEndDay": chart_week_end_day,
            },
        )

    # ------------------------------------------------------------------
    # Escape hatches
    # ------------------------------------------------------------------

    async def get_raw(
        self, path: str, params: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        """Call an authenticated GET endpoint not yet wrapped by this client."""
        return await self._request("GET", path, params)

    async def post_raw(
        self, path: str, payload: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        """Call an authenticated POST endpoint not yet wrapped by this client."""
        return await self._request("POST", path, payload)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_device_list_raw(
        self,
        plant_uid: str,
        *,
        page_no: int = 1,
        page_size: int = 10,
        search_office_id_arr: str | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/api/v1/monitor/device/getDeviceList",
            {
                "plantUid": plant_uid,
                "pageNo": page_no,
                "pageSize": page_size,
                "searchOfficeIdArr": search_office_id_arr,
            },
        )

    async def _home_get(
        self,
        endpoint: str,
        plant_uid: str,
        *,
        device_sn: str | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        params = {"plantUid": plant_uid, "deviceSn": device_sn, **(extra or {})}
        return await self._request(
            "GET",
            f"/api/v1/monitor/home/{endpoint}",
            params,
        )

    async def _request(
        self,
        method: str,
        path: str,
        params: Mapping[str, Any] | None = None,
        *,
        auth: bool = True,
        sign_only_common: bool = False,
    ) -> dict[str, Any]:
        if auth and not self.token:
            raise SajAuthError("Login is required before calling authenticated endpoints")

        signed = signed_params(
            params,
            language=self.language,
            sign_only_common=sign_only_common,
        )
        headers = self._headers(auth=auth)
        url = f"{self.api_base}{path}"
        if method.upper() == "GET":
            response = await self._client.get(url, params=signed, headers=headers)
        elif method.upper() == "POST":
            response = await self._client.post(url, data=signed, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")

        response.raise_for_status()
        payload = response.json()
        err_code = payload.get("errCode", 0)
        if err_code != 0:
            raise SajApiError(err_code, payload.get("errMsg", "Unknown error"), payload)
        return payload.get("data") or {}

    def _headers(self, *, auth: bool) -> dict[str, str]:
        headers = {
            "Content-Language": "zh_CN",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "enableSign": "false",
            "lang": self.language,
        }
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
