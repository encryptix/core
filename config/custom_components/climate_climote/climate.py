# COPY of BRIAN climate.py (using yaml config...)
import logging

import voluptuous as vol

from .climote_service import ClimoteService
from .const import DOMAIN

from datetime import timedelta


from homeassistant.util import Throttle
import homeassistant.helpers.config_validation as cv
from homeassistant.components.climate import ClimateEntity, PLATFORM_SCHEMA
from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE,
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
)
from homeassistant.const import (
    CONF_ID,
    CONF_NAME,
    ATTR_TEMPERATURE,
    CONF_PASSWORD,
    CONF_USERNAME,
    TEMP_CELSIUS,
    CONF_DEVICES,
)

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=5)
SCAN_INTERVAL = MIN_TIME_BETWEEN_UPDATES
#: Interval in hours that module will try to refresh data from the climote.
CONF_REFRESH_INTERVAL = "refresh_interval"
NOCHANGE = "nochange"
ICON = "mdi:thermometer"

MAX_TEMP = 75
MIN_TEMP = 0

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE
SUPPORT_MODES = [HVAC_MODE_HEAT, HVAC_MODE_OFF]


def validate_name(config):
    """Validate device name."""
    if CONF_NAME in config:
        return config
    climoteid = config[CONF_ID]
    name = "climote_{}".format(climoteid)
    config[CONF_NAME] = name
    return config


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_ID): cv.string,
        vol.Optional(CONF_REFRESH_INTERVAL, default=24): cv.string,
    }
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.config_entries import ConfigEntry

# SOunds like I need a setup_platform() which is auto called....
# Platform can then add entities...

# def setup_platform(
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    add_entities: AddEntitiesCallback,
) -> None:
    """Set up the ephember thermostat."""
    _LOGGER.info("Setting up climote platform through asyncsetupentry")
    _LOGGER.info(
        f"2. async_setup_entry UniqueID [{entry.unique_id}] Data [{entry.entry_id}]"
    )

    climotesvc = hass.data[DOMAIN][entry.entry_id]

    # username = config.get(CONF_USERNAME)
    # password = config.get(CONF_PASSWORD)
    # climoteid = config.get(CONF_ID)

    # interval = int(config.get(CONF_REFRESH_INTERVAL))

    # Add devices
    # climote = ClimoteService(username, password, climoteid)
    # if not (climote.initialize()):
    #     return False

    entities = []

    for id, name in climotesvc.zones.items():
        entities.append(Climote(climotesvc, id, name, 600))
    _LOGGER.info("3. Found entities %s", entities)

    add_entities(entities)

    return


class Climote(ClimateEntity):
    """Representation of a Climote device."""

    def __init__(self, climoteService, zoneid, name, interval):
        """Initialize the thermostat."""
        _LOGGER.info("Initialize Climote Entity")
        self._climote = climoteService
        self._zoneid = zoneid
        self._name = name
        self._force_update = False
        self.throttled_update = Throttle(timedelta(minutes=interval))(
            self._throttled_update
        )

    @property
    def should_poll(self):
        return True

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def hvac_mode(self):
        """Return current operation. ie. heat, cool, off."""
        zone = "zone" + str(self._zoneid)
        _LOGGER.debug(self._climote.data)
        return "heat" if self._climote.data[zone]["status"] == "5" else "off"

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.
        Need to be a subset of HVAC_MODES.
        """
        return SUPPORT_MODES

    @property
    def name(self):
        """Return the name of the thermostat."""
        return self._name

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return ICON

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 1

    @property
    def current_temperature(self):
        zone = "zone" + str(self._zoneid)
        _LOGGER.info(
            "current_temperature: Zone: %s, Temp %s C",
            zone,
            self._climote.data[zone]["temperature"],
        )
        return (
            int(self._climote.data[zone]["temperature"])
            if self._climote.data[zone]["temperature"] != "--"
            else 0
        )

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return MIN_TEMP

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return MAX_TEMP

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        zone = "zone" + str(self._zoneid)
        _LOGGER.info("target_temperature: %s", self._climote.data[zone]["thermostat"])
        return int(self._climote.data[zone]["thermostat"])

    @property
    def hvac_action(self):
        """Return current operation."""
        zone = "zone" + str(self._zoneid)
        return (
            CURRENT_HVAC_HEAT
            if self._climote.data[zone]["status"] == "5"
            else CURRENT_HVAC_IDLE
        )

    def set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVAC_MODE_HEAT:
            """Turn Heating Boost On."""
            res = self._climote.boost(self._zoneid, 1)
            if res:
                self._force_update = True
            return res
        if hvac_mode == HVAC_MODE_OFF:
            """Turn Heating Boost Off."""
            res = self._climote.off(self._zoneid, 0)
            if res:
                self._force_update = True
            return res

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        res = self._climote.set_target_temperature(self._zoneid, temperature)
        if res:
            self._force_update = True
        return res

    def update(self):
        self._climote.updateStatus(self._force_update)

    async def _throttled_update(self, **kwargs):
        """Get the latest state from the thermostat with a throttle."""
        _LOGGER.info("_throttled_update Force: %s", self._force_update)
        self._climote.updateStatus(self._force_update)
