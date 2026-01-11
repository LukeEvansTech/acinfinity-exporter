"""Prometheus metrics definitions."""

from prometheus_client import Gauge

# Controller metrics
controller_info = Gauge(
    "acinfinity_controller_info",
    "AC Infinity controller information",
    ["controller_id", "controller_name"],
)

controller_temperature = Gauge(
    "acinfinity_controller_temperature_celsius",
    "Controller temperature in Celsius",
    ["controller_id", "controller_name"],
)

controller_humidity = Gauge(
    "acinfinity_controller_humidity_percent",
    "Controller humidity percentage",
    ["controller_id", "controller_name"],
)

controller_vpd = Gauge(
    "acinfinity_controller_vpd_kpa",
    "Controller VPD in kPa",
    ["controller_id", "controller_name"],
)

controller_temperature_trend = Gauge(
    "acinfinity_controller_temperature_trend",
    "Temperature trend (0=stable, 1=rising, 2=falling)",
    ["controller_id", "controller_name"],
)

controller_humidity_trend = Gauge(
    "acinfinity_controller_humidity_trend",
    "Humidity trend (0=stable, 1=rising, 2=falling)",
    ["controller_id", "controller_name"],
)

controller_mode = Gauge(
    "acinfinity_controller_mode",
    "Controller current mode (1=off, 2=on, 3=auto, 4=timer, 6=cycle, 7=schedule, 8=vpdTemp, 9=vpdHumi)",
    ["controller_id", "controller_name"],
)

controller_last_seen = Gauge(
    "acinfinity_controller_last_seen_timestamp",
    "Unix timestamp when controller was last seen",
    ["controller_id", "controller_name"],
)

# Controller info metric with version labels
controller_version_info = Gauge(
    "acinfinity_controller_version_info",
    "Controller version information (always 1, use labels for info)",
    ["controller_id", "controller_name", "firmware_version", "hardware_version", "wifi_name"],
)

# Device/port metrics
device_info = Gauge(
    "acinfinity_device_info",
    "AC Infinity device information",
    ["controller_id", "port", "device_name"],
)

device_speed = Gauge(
    "acinfinity_device_speed",
    "Device speed (0-10)",
    ["controller_id", "port", "device_name"],
)

device_online = Gauge(
    "acinfinity_device_online",
    "Device online status (1=online, 0=offline)",
    ["controller_id", "port", "device_name"],
)

device_state = Gauge(
    "acinfinity_device_state",
    "Device state",
    ["controller_id", "port", "device_name"],
)

device_mode = Gauge(
    "acinfinity_device_mode",
    "Device current mode (1=off, 2=on, 3=auto, 4=timer, 6=cycle, 7=schedule, 8=vpdTemp, 9=vpdHumi)",
    ["controller_id", "port", "device_name"],
)

device_connected = Gauge(
    "acinfinity_device_connected",
    "Whether device is physically connected (1=connected, 0=not connected)",
    ["controller_id", "port", "device_name"],
)

device_overcurrent = Gauge(
    "acinfinity_device_overcurrent",
    "Overcurrent status (0=normal, 1=overcurrent detected)",
    ["controller_id", "port", "device_name"],
)

device_abnormal = Gauge(
    "acinfinity_device_abnormal",
    "Abnormal state (0=normal, non-zero=fault)",
    ["controller_id", "port", "device_name"],
)

# Sensor metrics
sensor_temperature = Gauge(
    "acinfinity_sensor_temperature_celsius",
    "Sensor temperature in Celsius",
    ["controller_id", "port", "sensor_type"],
)

sensor_humidity = Gauge(
    "acinfinity_sensor_humidity_percent",
    "Sensor humidity percentage",
    ["controller_id", "port", "sensor_type"],
)

sensor_vpd = Gauge(
    "acinfinity_sensor_vpd_kpa",
    "Sensor VPD in kPa",
    ["controller_id", "port", "sensor_type"],
)

sensor_co2 = Gauge(
    "acinfinity_sensor_co2_ppm",
    "CO2 level in ppm",
    ["controller_id", "port"],
)

sensor_light = Gauge(
    "acinfinity_sensor_light_percent",
    "Light level percentage",
    ["controller_id", "port"],
)

sensor_soil = Gauge(
    "acinfinity_sensor_soil_percent",
    "Soil moisture percentage",
    ["controller_id", "port"],
)

# Scrape status metrics
last_scrape_success = Gauge(
    "acinfinity_last_scrape_success",
    "Whether the last scrape was successful (1=success, 0=failure)",
)

last_scrape_timestamp = Gauge(
    "acinfinity_last_scrape_timestamp",
    "Unix timestamp of the last scrape",
)
