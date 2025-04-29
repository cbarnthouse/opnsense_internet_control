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
