"""The Climate Climote integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, USERNAME, PASSWORD, CLIMOTE_ID

from .climote_service import ClimoteService

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.CLIMATE]
import logging

_LOGGER = logging.getLogger(__name__)

# This seems to replace async_setup (which was used for configuration.yaml based settings)
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Climate Climote from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    _LOGGER.info(f"async_setup_entry UniqueID [{entry.unique_id}] Data [{entry.data}]")

    # TODO 1. Create API instance
    username = entry.data[USERNAME]
    password = entry.data[PASSWORD]
    climoteid = entry.data[CLIMOTE_ID]

    # Repr of service, no attempt at login
    climote_svc = ClimoteService(username, password, climoteid)

    # This now does the first HTTP request
    # if not (climote_svc.initialize()):
    #    return False
    # Convert to async
    init_successful = await hass.async_add_executor_job(climote_svc.initialize)
    if not init_successful:
        a = 1
        return False
        # TODO should this raise?
        # raise ConfigEntryNotReady
    # climote = Climote(
    #     username, password, climoteid, default_boost_duration_hrs, _LOGGER
    # )
    # TODO 2. Validate the API connection (and authentication)
    # TODO 3. Store an API object for your platforms to access
    # hass.data[DOMAIN][entry.entry_id] = MyApi(...)

    # TODO until using a coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = climote_svc
    # RAY: I commented this out
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
