# AC Infinity Prometheus Exporter

A Python Prometheus exporter for AC Infinity UIS controllers (grow tent fans and
environmental equipment). Polls the AC Infinity cloud API and exposes controller,
device, and sensor metrics (temperature, humidity, VPD, CO2, light, soil) for
scraping. Includes an optional fan-sync controller that syncs intake fan speed to
a percentage of exhaust fan speed. Ships as a Docker image; docs are published via
zensical to GitHub Pages.

Status: active, last commit 2026-07-07.

## Key files

- `src/main.py` — exporter entrypoint (default container command)
- `src/client.py` — AC Infinity cloud API client
- `src/collector.py` — Prometheus metric collection
- `src/metrics.py` — metric definitions
- `src/fan_sync.py` — fan sync controller (run via `python -m src.fan_sync`)
- `Dockerfile` — build/runtime image
- `docs/` — zensical documentation source (published to GitHub Pages)
- `deploy/` — deployment configs

## Configuration

Set via environment variables: `ACINFINITY_EMAIL`, `ACINFINITY_PASSWORD` (required),
`METRICS_PORT` (default 8000). See README.md for the full table and metric reference.

## Commands

```
pip install -r requirements.txt
python -m src.main          # run exporter
python -m src.fan_sync       # run fan sync controller
docker build -t acinfinity-exporter .
```
