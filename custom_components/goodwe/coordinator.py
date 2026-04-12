"""Update coordinator for Goodwe."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Any

from goodwe import Inverter, InverterError, RequestFailedException
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    BaseCoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

type GoodweConfigEntry = ConfigEntry[GoodweRuntimeData]


@dataclass
class GoodweRuntimeData:
    """Data class for runtime data."""

    inverter: Inverter
    coordinator: GoodweUpdateCoordinator
    device_info: DeviceInfo


class GoodweUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Gather data for the energy device."""

    config_entry: GoodweConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: GoodweConfigEntry,
        inverter: Inverter,
    ) -> None:
        """Initialize update coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=entry.title,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.inverter: Inverter = inverter
        self._last_data: dict[str, Any] = {}
        # Entities registered for periodic re-polling.
        # Value is (interval_seconds, last_poll_datetime_or_None).
        self._polled_entities: dict[
            BaseCoordinatorEntity, tuple[int, datetime | None]
        ] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the inverter."""
        await self._update_polled_entities()

        try:
            self._last_data = self.data or {}
            return await self.inverter.read_runtime_data()
        except RequestFailedException as ex:
            # UDP communication with inverter is by definition unreliable.
            # It is rather normal in many environments to fail to receive
            # proper response in usual time, so we intentionally ignore isolated
            # failures and report problem with availability only after
            # consecutive streak of 3 of failed requests.
            if ex.consecutive_failures_count < 3:
                _LOGGER.debug(
                    "No response received (streak of %d)", ex.consecutive_failures_count
                )
                # return last known data
                return self._last_data
            # Inverter does not respond anymore (e.g. it went to sleep mode)
            _LOGGER.debug(
                "Inverter not responding (streak of %d)", ex.consecutive_failures_count
            )
            raise UpdateFailed(ex) from ex
        except InverterError as ex:
            raise UpdateFailed(ex) from ex

    async def _update_polled_entities(self) -> None:
        now = datetime.now()
        for entity, (interval, last_poll) in list(self._polled_entities.items()):
            if last_poll is not None and (now - last_poll).total_seconds() < interval:
                continue
            try:
                await entity.async_update()
                self._polled_entities[entity] = (interval, now)
                if hasattr(entity, "async_write_ha_state"):
                    entity.async_write_ha_state()
            except InverterError:
                _LOGGER.debug("Failed to update entity %s", entity.name)

    def sensor_value(self, sensor: str) -> Any:
        """Answer current (or last known) value of the sensor."""
        val = self.data.get(sensor)
        return val if val is not None else self._last_data.get(sensor)

    def total_sensor_value(self, sensor: str) -> Any:
        """Answer current value of the 'total' (never 0) sensor."""
        val = self.data.get(sensor)
        return val or self._last_data.get(sensor)

    def reset_sensor(self, sensor: str) -> None:
        """Reset sensor value to 0.

        Intended for "daily" cumulative sensors (e.g. PV energy produced today),
        which should be explicitly reset to 0 at midnight if inverter is suspended.
        """
        self._last_data[sensor] = 0
        self.data[sensor] = 0

    def entity_state_polling(
        self, entity: BaseCoordinatorEntity, interval: int
    ) -> None:
        """Enable/disable periodic re-polling of an entity's state.

        interval: seconds between polls. Pass 0 to disable polling.
        """
        if interval:
            # Preserve the existing last_poll timestamp when re-registering,
            # otherwise None means "poll on next coordinator cycle".
            existing = self._polled_entities.get(entity)
            last_poll = existing[1] if existing else None
            self._polled_entities[entity] = (interval, last_poll)
        else:
            self._polled_entities.pop(entity, None)
