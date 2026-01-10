# AC Infinity Prometheus Exporter

A Prometheus exporter for AC Infinity UIS controllers (grow tent fans and environmental equipment).

## Features

- Polls AC Infinity cloud API at configurable intervals
- Exposes metrics for Prometheus scraping
- Supports multiple controllers and devices
- Handles sensor data from probes (temperature, humidity, VPD, CO2, light, soil)
- Automatic re-authentication on token expiry

## Metrics

### Controller Metrics

| Metric | Description | Labels |
|--------|-------------|--------|
| `acinfinity_controller_info` | Controller information (always 1) | controller_id, controller_name |
| `acinfinity_controller_temperature_celsius` | Controller temperature in Celsius | controller_id, controller_name |
| `acinfinity_controller_humidity_percent` | Controller humidity percentage | controller_id, controller_name |
| `acinfinity_controller_vpd_kpa` | Controller VPD in kPa | controller_id, controller_name |

### Device Metrics

| Metric | Description | Labels |
|--------|-------------|--------|
| `acinfinity_device_info` | Device information (always 1) | controller_id, port, device_name |
| `acinfinity_device_speed` | Device speed (0-10) | controller_id, port, device_name |
| `acinfinity_device_online` | Device online status (1/0) | controller_id, port, device_name |
| `acinfinity_device_state` | Device state | controller_id, port, device_name |

### Sensor Metrics

| Metric | Description | Labels |
|--------|-------------|--------|
| `acinfinity_sensor_temperature_celsius` | Sensor temperature in Celsius | controller_id, port, sensor_type |
| `acinfinity_sensor_humidity_percent` | Sensor humidity percentage | controller_id, port, sensor_type |
| `acinfinity_sensor_vpd_kpa` | Sensor VPD in kPa | controller_id, port, sensor_type |
| `acinfinity_sensor_co2_ppm` | CO2 level in ppm | controller_id, port |
| `acinfinity_sensor_light_percent` | Light level percentage | controller_id, port |
| `acinfinity_sensor_soil_percent` | Soil moisture percentage | controller_id, port |

### Exporter Metrics

| Metric | Description |
|--------|-------------|
| `acinfinity_last_scrape_success` | Whether the last API scrape succeeded (1/0) |
| `acinfinity_last_scrape_timestamp` | Unix timestamp of last scrape |

## Configuration

| Environment Variable | Required | Default | Description |
|---------------------|----------|---------|-------------|
| `ACINFINITY_EMAIL` | Yes | - | AC Infinity account email |
| `ACINFINITY_PASSWORD` | Yes | - | AC Infinity account password |
| `METRICS_PORT` | No | 8000 | Port to expose metrics |
| `POLL_INTERVAL` | No | 60 | Seconds between API polls |
| `LOG_LEVEL` | No | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

## Usage

### Docker

```bash
docker run -d \
  --name acinfinity-exporter \
  -p 8000:8000 \
  -e ACINFINITY_EMAIL=your@email.com \
  -e ACINFINITY_PASSWORD=yourpassword \
  ghcr.io/lukeeevanstech/acinfinity:latest
```

### Docker Compose

```yaml
services:
  acinfinity-exporter:
    image: ghcr.io/lukeeevanstech/acinfinity:latest
    container_name: acinfinity-exporter
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      ACINFINITY_EMAIL: your@email.com
      ACINFINITY_PASSWORD: yourpassword
      POLL_INTERVAL: 60
      LOG_LEVEL: INFO
```

### Prometheus Configuration

```yaml
scrape_configs:
  - job_name: 'acinfinity'
    static_configs:
      - targets: ['acinfinity-exporter:8000']
    scrape_interval: 60s
```

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `/metrics` | Prometheus metrics |
| `/health` | Health check (returns "OK") |

## Building

```bash
docker build -t acinfinity-exporter .
```

## License

MIT
