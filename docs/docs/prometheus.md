# Prometheus Setup

Configure Prometheus to scrape metrics from the AC Infinity exporter.

## Basic Configuration

Add the following to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'acinfinity'
    static_configs:
      - targets: ['acinfinity-exporter:8000']
    scrape_interval: 60s
```

## Configuration with Labels

Add additional labels for better organization:

```yaml
scrape_configs:
  - job_name: 'acinfinity'
    static_configs:
      - targets: ['acinfinity-exporter:8000']
        labels:
          env: 'production'
          location: 'grow-tent'
    scrape_interval: 60s
```

## Docker Compose with Prometheus

Complete example running both the exporter and Prometheus:

```yaml
services:
  acinfinity-exporter:
    image: ghcr.io/lukeeevanstech/acinfinity-exporter:latest
    container_name: acinfinity-exporter
    restart: unless-stopped
    environment:
      ACINFINITY_EMAIL: your@email.com
      ACINFINITY_PASSWORD: yourpassword
      POLL_INTERVAL: 60

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

volumes:
  prometheus_data:
```

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `/metrics` | Prometheus metrics in text format |
| `/health` | Health check endpoint (returns "OK") |

## Grafana Dashboard

Once Prometheus is scraping the exporter, you can create Grafana dashboards to visualize your grow environment data.

Example queries:

```promql
# Current temperature
acinfinity_controller_temperature_celsius

# Average temperature over last hour
avg_over_time(acinfinity_controller_temperature_celsius[1h])

# Fan speed
acinfinity_device_speed

# Humidity trend
acinfinity_controller_humidity_percent
```
