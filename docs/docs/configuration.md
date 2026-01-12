# Configuration

The exporter is configured using environment variables.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ACINFINITY_EMAIL` | Yes | - | AC Infinity account email |
| `ACINFINITY_PASSWORD` | Yes | - | AC Infinity account password |
| `METRICS_PORT` | No | 8000 | Port to expose metrics |
| `POLL_INTERVAL` | No | 60 | Seconds between API polls |
| `LOG_LEVEL` | No | INFO | Logging level |

## Required Variables

### ACINFINITY_EMAIL

Your AC Infinity account email address. This is the same email you use to log in to the AC Infinity app.

### ACINFINITY_PASSWORD

Your AC Infinity account password.

## Optional Variables

### METRICS_PORT

The port on which the exporter listens for HTTP requests. Defaults to `8000`.

### POLL_INTERVAL

How often (in seconds) to poll the AC Infinity API for new data. Defaults to `60` seconds.

Note: Setting this too low may result in rate limiting from the AC Infinity API.

### LOG_LEVEL

Controls the verbosity of logging output. Valid values:

- `DEBUG` - Verbose output for troubleshooting
- `INFO` - Normal operation messages (default)
- `WARNING` - Only warnings and errors
- `ERROR` - Only error messages

## Example Configuration

```yaml
services:
  acinfinity-exporter:
    image: ghcr.io/lukeeevanstech/acinfinity-exporter:latest
    environment:
      ACINFINITY_EMAIL: your@email.com
      ACINFINITY_PASSWORD: yourpassword
      METRICS_PORT: 8000
      POLL_INTERVAL: 60
      LOG_LEVEL: INFO
```
