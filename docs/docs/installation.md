# Installation

## Docker

The simplest way to run the exporter is with Docker:

```bash
docker run -d \
  --name acinfinity-exporter \
  -p 8000:8000 \
  -e ACINFINITY_EMAIL=your@email.com \
  -e ACINFINITY_PASSWORD=yourpassword \
  ghcr.io/lukeeevanstech/acinfinity-exporter:latest
```

## Docker Compose

For a more maintainable setup, use Docker Compose:

```yaml
services:
  acinfinity-exporter:
    image: ghcr.io/lukeeevanstech/acinfinity-exporter:latest
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

Save this as `docker-compose.yml` and run:

```bash
docker compose up -d
```

## Building from Source

If you prefer to build the image yourself:

```bash
git clone https://github.com/LukeEvansTech/acinfinity-exporter.git
cd acinfinity-exporter
docker build -t acinfinity-exporter .
```

Then run your local build:

```bash
docker run -d \
  --name acinfinity-exporter \
  -p 8000:8000 \
  -e ACINFINITY_EMAIL=your@email.com \
  -e ACINFINITY_PASSWORD=yourpassword \
  acinfinity-exporter
```

## Verifying Installation

Once running, verify the exporter is working:

```bash
# Check health endpoint
curl http://localhost:8000/health

# Check metrics endpoint
curl http://localhost:8000/metrics
```

The health endpoint should return `OK` and the metrics endpoint should return Prometheus-formatted metrics.
