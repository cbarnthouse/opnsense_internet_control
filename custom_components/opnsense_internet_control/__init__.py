"""OPNsense Internet Control - Home Assistant Integration."""

import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN = "opnsense_internet_control"

def setup(hass, config):
    """Set up the OPNsense Internet Control integration."""
    _LOGGER.info("Setting up OPNsense Internet Control integration")
    return True
