# Metrics

The exporter exposes the following Prometheus metrics.

## Controller Metrics

Metrics related to AC Infinity controllers.

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `acinfinity_controller_info` | Gauge | Controller information (always 1) | controller_id, controller_name |
| `acinfinity_controller_temperature_celsius` | Gauge | Controller temperature in Celsius | controller_id, controller_name |
| `acinfinity_controller_humidity_percent` | Gauge | Controller humidity percentage | controller_id, controller_name |
| `acinfinity_controller_vpd_kpa` | Gauge | Controller VPD in kPa | controller_id, controller_name |

## Device Metrics

Metrics related to individual devices (fans, etc.) connected to controllers.

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `acinfinity_device_info` | Gauge | Device information (always 1) | controller_id, port, device_name |
| `acinfinity_device_speed` | Gauge | Device speed (0-10) | controller_id, port, device_name |
| `acinfinity_device_online` | Gauge | Device online status (1/0) | controller_id, port, device_name |
| `acinfinity_device_state` | Gauge | Device state | controller_id, port, device_name |

## Sensor Metrics

Metrics from environmental sensors and probes.

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `acinfinity_sensor_temperature_celsius` | Gauge | Sensor temperature in Celsius | controller_id, port, sensor_type |
| `acinfinity_sensor_humidity_percent` | Gauge | Sensor humidity percentage | controller_id, port, sensor_type |
| `acinfinity_sensor_vpd_kpa` | Gauge | Sensor VPD in kPa | controller_id, port, sensor_type |
| `acinfinity_sensor_co2_ppm` | Gauge | CO2 level in ppm | controller_id, port |
| `acinfinity_sensor_light_percent` | Gauge | Light level percentage | controller_id, port |
| `acinfinity_sensor_soil_percent` | Gauge | Soil moisture percentage | controller_id, port |

## Exporter Metrics

Metrics about the exporter itself.

| Metric | Type | Description |
|--------|------|-------------|
| `acinfinity_last_scrape_success` | Gauge | Whether the last API scrape succeeded (1/0) |
| `acinfinity_last_scrape_timestamp` | Gauge | Unix timestamp of last scrape |

## Labels

### controller_id

The unique identifier for the AC Infinity controller.

### controller_name

The user-assigned name for the controller.

### port

The port number on the controller where the device or sensor is connected.

### device_name

The user-assigned name for the device.

### sensor_type

The type of sensor probe (e.g., internal, external).

## Example Output

```
# HELP acinfinity_controller_temperature_celsius Controller temperature in Celsius
# TYPE acinfinity_controller_temperature_celsius gauge
acinfinity_controller_temperature_celsius{controller_id="12345",controller_name="Tent Controller"} 24.5

# HELP acinfinity_device_speed Device speed (0-10)
# TYPE acinfinity_device_speed gauge
acinfinity_device_speed{controller_id="12345",port="1",device_name="Inline Fan"} 7
```
