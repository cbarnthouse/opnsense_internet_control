import logging
import json
import requests
import voluptuous as vol

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_URL, CONF_API_KEY, CONF_API_TOKEN
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = "opnsense_internet_control"
CONF_ALIAS = "alias"

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_URL): cv.url,
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_API_TOKEN): cv.string,
        vol.Required(CONF_ALIAS): cv.string,
    })
}, extra=vol.ALLOW_EXTRA)

def setup_platform(hass, config, add_entities, discovery_info=None):
    url = config[CONF_URL]
    api_key = config[CONF_API_KEY]
    api_token = config[CONF_API_TOKEN]
    alias = config[CONF_ALIAS]

    leases = fetch_dhcp_devices(url, api_key, api_token)

    switches = []
    for lease in leases:
        name = lease.get('hostname') or lease.get('mac')
        ip = lease.get('address')
        if ip and name:
            switches.append(OPNsenseInternetSwitch(
                name=name,
                ip=ip,
                url=url,
                api_key=api_key,
                api_token=api_token,
                alias=alias
            ))

    add_entities(switches, True)

def fetch_dhcp_devices(url, api_key, api_token):
    endpoint = f"{url.rstrip('/')}/api/dhcpv4/leases/searchLease/"
    try:
        _LOGGER.info(f"Fetching DHCP leases from {endpoint}")
        response = requests.get(endpoint, auth=(api_key, api_token), verify=False, timeout=10)
        if response.status_code == 200:
            leases_data = response.json()
            return leases_data.get('rows', [])
        else:
            _LOGGER.error(f"Failed to fetch DHCP leases: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        _LOGGER.exception(f"Exception fetching DHCP leases: {e}")
        return []

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
                all_aliases = aliases_wrapper.get('alias', {}).get('aliases', {}).get('alias', {})
                for alias_id, alias_data in all_aliases.items():
                    if alias_data.get('name') == self._alias:
                        self._uuid = alias_id
                        content = alias_data.get('content', {})
                        addresses = [k for k in content.keys() if k]
                        return addresses
                _LOGGER.error(f"Alias '{self._alias}' not found.")
            else:
                _LOGGER.error(f"Failed to get aliases: {response.status_code} - {response.text}")
        except Exception as e:
            _LOGGER.exception(f"Error fetching aliases: {e}")
        return []

    def _set_alias_content(self, addresses):
        if not self._uuid:
            _LOGGER.error(f"No UUID for alias '{self._alias}', cannot update.")
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
                "counters": str(len(addresses)),
                "description": ""
            },
            "network_content": "",
            "authgroup_content": ""
        }

        try:
            _LOGGER.debug(f"Setting alias {self._alias} with data: {json.dumps(data)}")
            response = requests.post(endpoint, auth=(self._api_key, self._api_token), json=data, verify=False, timeout=10)
            if response.status_code == 200:
                _LOGGER.info(f"Alias '{self._alias}' updated successfully.")
            else:
                _LOGGER.error(f"Failed to update alias: {response.status_code} - {response.text}")
        except Exception as e:
            _LOGGER.exception(f"Error setting alias: {e}")

    def _reload_firewall(self):
        endpoint = f"{self._url}/api/firewall/filter/reload"
        try:
            response = requests.post(endpoint, auth=(self._api_key, self._api_token), verify=False, timeout=10)
            if response.status_code != 200:
                _LOGGER.error(f"Failed to reload firewall: {response.status_code} - {response.text}")
            else:
                _LOGGER.info("Firewall reload triggered.")
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

