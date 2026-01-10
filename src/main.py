"""AC Infinity Prometheus Exporter entry point."""

import logging
import os
import signal
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, REGISTRY

from .client import ACInfinityClient
from .collector import ACInfinityCollector

logger = logging.getLogger(__name__)


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for /metrics and /health endpoints."""

    def log_message(self, format: str, *args) -> None:
        """Override to use logging module."""
        logger.debug("%s - %s", self.address_string(), format % args)

    def do_GET(self) -> None:
        """Handle GET requests."""
        if self.path == "/metrics":
            self._serve_metrics()
        elif self.path == "/health":
            self._serve_health()
        else:
            self.send_error(404, "Not Found")

    def _serve_metrics(self) -> None:
        """Serve Prometheus metrics."""
        try:
            output = generate_latest(REGISTRY)
            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.send_header("Content-Length", str(len(output)))
            self.end_headers()
            self.wfile.write(output)
        except Exception as e:
            logger.exception("Error generating metrics")
            self.send_error(500, str(e))

    def _serve_health(self) -> None:
        """Serve health check endpoint."""
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")


def get_env_var(name: str, default: str | None = None, required: bool = False) -> str:
    """Get environment variable with optional default."""
    value = os.environ.get(name, default)
    if required and not value:
        logger.error("Required environment variable %s not set", name)
        sys.exit(1)
    return value or ""


def main() -> None:
    """Main entry point."""
    # Configure logging
    log_level = get_env_var("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Get configuration from environment
    email = get_env_var("ACINFINITY_EMAIL", required=True)
    password = get_env_var("ACINFINITY_PASSWORD", required=True)
    port = int(get_env_var("METRICS_PORT", "8000"))
    poll_interval = int(get_env_var("POLL_INTERVAL", "60"))

    logger.info("Starting AC Infinity Prometheus Exporter")
    logger.info("Metrics port: %d, Poll interval: %ds", port, poll_interval)

    # Initialize client and collector
    client = ACInfinityClient(email, password)
    collector = ACInfinityCollector(client, poll_interval)

    # Initial authentication
    if not client.authenticate():
        logger.error("Initial authentication failed")
        sys.exit(1)

    # Start collector
    collector.start()

    # Do initial collection
    collector.collect()

    # Start HTTP server
    server = HTTPServer(("0.0.0.0", port), MetricsHandler)
    logger.info("HTTP server listening on port %d", port)

    # Handle shutdown signals
    def shutdown(signum, frame):
        logger.info("Received signal %d, shutting down", signum)
        collector.stop()
        server.shutdown()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        collector.stop()
        logger.info("Exporter stopped")


if __name__ == "__main__":
    main()
