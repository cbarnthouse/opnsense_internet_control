import logging
import requests
import voluptuous as vol

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_URL, CONF_API_KEY, CONF_API_TOKEN, CONF_DEVICES
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = "opnsense_internet_control"

CONF_ALIAS = "alias"
CONF_IP = "ip"
CONF_NAME = "name"

DEVICE_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_IP): cv.string,
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_URL): cv.url,
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_API_TOKEN): cv.string,
        vol.Required(CONF_ALIAS): cv.string,
        vol.Required(CONF_DEVICES): vol.All(cv.ensure_list, [DEVICE_SCHEMA]),
    })
}, extra=vol.ALLOW_EXTRA)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the OPNsense Internet Control switches."""
    url = config[CONF_URL]
    api_key = config[CONF_API_KEY]
    api_token = config[CONF_API_TOKEN]
    alias = config[CONF_ALIAS]
    devices = config[CONF_DEVICES]

    switches = []
    for device in devices:
        switches.append(OPNsenseInternetSwitch(
            name=device[CONF_NAME],
            ip=device[CONF_IP],
            url=url,
            api_key=api_key,
            api_token=api_token,
            alias=alias
        ))

    add_entities(switches, True)

class OPNsenseInternetSwitch(SwitchEntity):
    def __init__(self, name, ip, url, api_key, api_token, alias):
        self._name = name
        self._ip = ip
        self._url = url.rstrip("/")
        self._api_key = api_key
        self._api_token = api_token
        self._alias = alias
        self._state = None

    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        return self._state

    def _get_alias_content(self):
        endpoint = f"{self._url}/api/firewall/alias/get"
        try:
            response = requests.get(endpoint, auth=(self._api_key, self._api_token), verify=False, timeout=10)
            if response.status_code == 200:
                aliases = response.json().get('aliases', [])
                for alias in aliases:
                    if alias.get('name') == self._alias:
                        return alias.get('content', [])
                _LOGGER.error(f"Alias {self._alias} not found in OPNsense response.")
            else:
                _LOGGER.error(f"Failed to get aliases: {response.text}")
        except Exception as e:
            _LOGGER.error(f"Error fetching aliases: {e}")
        return []

    def _set_alias_content(self, addresses):
        endpoint = f"{self._url}/api/firewall/alias/set"
        data = {"name": self._alias, "addresses": addresses}
        try:
            response = requests.post(endpoint, auth=(self._api_key, self._api_token), json=data, verify=False, timeout=10)
            if response.status_code != 200:
                _LOGGER.error(f"Failed to update alias {self._alias}: {response.text}")
        except Exception as e:
            _LOGGER.error(f"Error updating alias: {e}")

    def turn_on(self, **kwargs):
        addresses = self._get_alias_content()
        if self._ip in addresses:
            addresses.remove(self._ip)
            self._set_alias_content(addresses)
        self._state = True

    def turn_off(self, **kwargs):
        addresses = self._get_alias_content()
        if self._ip not in addresses:
            addresses.append(self._ip)
            self._set_alias_content(addresses)
        self._state = False

    def update(self):
        addresses = self._get_alias_content()
        self._state = self._ip not in addresses
