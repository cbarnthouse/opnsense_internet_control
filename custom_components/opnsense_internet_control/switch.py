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
        self._uuid = None
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
            _LOGGER.debug(f"Requesting aliases from {endpoint}")
            response = requests.get(endpoint, auth=(self._api_key, self._api_token), verify=False, timeout=10)
            if response.status_code == 200:
                aliases_wrapper = response.json()
                all_aliases = aliases_wrapper.get('alias', {}).get('aliases', {}).get('alias', {})  # <- FIX HERE
                _LOGGER.debug(f"Found {len(all_aliases)} aliases in response: {list(all_aliases.keys())}")
                for alias_id, alias_data in all_aliases.items():
                    alias_name = alias_data.get('name')
                    _LOGGER.debug(f"Checking alias {alias_id} with name {alias_name}")
                    if alias_name == self._alias:
                        self._uuid = alias_id
                        _LOGGER.info(f"Matched alias '{self._alias}' successfully with UUID {self._uuid}")
                        content = alias_data.get('content', {})
                        addresses = [k for k in content.keys() if k]
                        _LOGGER.debug(f"Current addresses: {addresses}")
                        return addresses
                _LOGGER.error(f"Alias '{self._alias}' not found inside aliases list.")
            else:
                _LOGGER.error(f"Failed to get aliases: {response.status_code} - {response.text}")
        except Exception as e:
            _LOGGER.exception(f"Exception occurred while fetching aliases: {e}")
        return []

    def _set_alias_content(self, addresses):
        if not self._uuid:
            _LOGGER.error(f"No UUID found for alias {self._alias}. Cannot update.")
            return
    
        endpoint = f"{self._url}/api/firewall/alias/setItem/{self._uuid}"
        content_str = "\n".join(addresses)
    
        data = {
            "alias": {
                "enabled": "1",
                "name": self._alias,
                "type": "host",
                "proto": "",
                "categories": "",
                "updatefreq": "",
                "content": f"{content_str}",
                "path_expression": "",
                "authtype": "",
                "username": "",
                "password": "",
                "interface": "",
                "counters": "1",
                "description": ""
            },
            "network_content": "",
            "authgroup_content": ""
        }
    
        _LOGGER.debug(f"Setting alias at {endpoint} with data: {data}")
    
        try:
            response = requests.post(endpoint, auth=(self._api_key, self._api_token), json=data, verify=False, timeout=10)
            if response.status_code == 200:
                _LOGGER.info(f"Alias '{self._alias}' updated successfully!")
                self._reload_firewall()
            else:
                _LOGGER.error(f"Failed to update alias: {response.status_code} - {response.text}")
        except Exception as e:
            _LOGGER.exception(f"Exception occurred while setting alias content: {e}")
     
    def _reload_firewall(self):
        endpoint = f"{self._url}/api/firewall/filter/reload"
        try:
            _LOGGER.info("Reloading firewall rules")
            response = requests.post(endpoint, auth=(self._api_key, self._api_token), verify=False, timeout=10)
            if response.status_code != 200:
                _LOGGER.error(f"Failed to reload firewall: {response.status_code} - {response.text}")
            else:
                _LOGGER.info("Firewall reload triggered successfully.")
        except Exception as e:
            _LOGGER.exception(f"Error reloading firewall: {e}")

    def turn_on(self, **kwargs):
        addresses = self._get_alias_content()
        if self._ip in addresses:
            addresses.remove(self._ip)
        _LOGGER.debug(f"Addresses after enabling {self._ip}: {addresses}")
        self._set_alias_content(addresses)
        self._reload_firewall()
        self._state = True

    def turn_off(self, **kwargs):
        addresses = self._get_alias_content()
        if self._ip not in addresses:
            addresses.append(self._ip)
        _LOGGER.debug(f"Addresses after disabling {self._ip}: {addresses}")
        self._set_alias_content(addresses)
        self._reload_firewall()
        self._state = False

    def update(self):
        addresses = self._get_alias_content()
        self._state = self._ip not in addresses

    async def async_turn_on(self, **kwargs):
        await self.hass.async_add_executor_job(self.turn_on)

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(self.turn_off)

