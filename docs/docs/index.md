# AC Infinity Prometheus Exporter

A Prometheus exporter for AC Infinity UIS controllers (grow tent fans and environmental equipment).

## Overview

This exporter polls the AC Infinity cloud API and exposes metrics for Prometheus scraping. It supports multiple controllers and devices, handles sensor data from various probes, and automatically re-authenticates when tokens expire.

## Quick Start

```bash
docker run -d \
  --name acinfinity-exporter \
  -p 8000:8000 \
  -e ACINFINITY_EMAIL=your@email.com \
  -e ACINFINITY_PASSWORD=yourpassword \
  ghcr.io/lukeeevanstech/acinfinity-exporter:latest
```

## Features

- Polls AC Infinity cloud API at configurable intervals
- Exposes metrics for Prometheus scraping
- Supports multiple controllers and devices
- Handles sensor data from probes (temperature, humidity, VPD, CO2, light, soil)
- Automatic re-authentication on token expiry

## Navigation

- [Installation](installation.md) - Get started with Docker or Docker Compose
- [Configuration](configuration.md) - Environment variables and settings
- [Metrics](metrics.md) - Complete list of exposed metrics
- [Prometheus Setup](prometheus.md) - Configure Prometheus to scrape metrics
