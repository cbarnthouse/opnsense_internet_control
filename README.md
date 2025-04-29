# OPNsense Internet Control (Updated for Newer API)

Home Assistant integration to control internet access per device by managing an OPNsense firewall alias.

## Installation
1. Copy the `custom_components/opnsense_internet_control/` folder to your Home Assistant `config/custom_components/` directory.
2. Add configuration to your `configuration.yaml`.
3. Restart Home Assistant.

## Example Configuration

```yaml
switch:
  - platform: opnsense_internet_control
    url: "https://opnsense.local"
    api_key: "YOUR_API_KEY"
    api_token: "YOUR_API_TOKEN"
    alias: "blocked_devices"
```

## Minimal API Permissions Required

```
For the OPNsense Internet Control Home Assistant integration to work correctly, the API key/token user must have access to the following permissions:
Area	Permission
Firewall	Firewall Aliases
Firewall	Firewall Alias Edit
Firewall	Firewall Rules
Firewall	Firewall Rules Edit
Status	DHCP Leases
'''

## Permission	Purpose
Firewall Aliases	View existing aliases (for loading device block lists).
Firewall Alias Edit	Update the alias list (add/remove devices dynamically).
Firewall Rules	View and reload firewall rules after alias changes.
Firewall Rules Edit	Trigger a rules reload after updating aliases.
DHCP Leases	List active and static devices from DHCP to generate Home Assistant switches.
