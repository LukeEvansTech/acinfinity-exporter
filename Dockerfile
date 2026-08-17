FROM python:3.14-slim@sha256:ce40764625a4ff50df3548277632e7f96c4e77fe75fa848aae9885476e7df5a4

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

USER 65534:65534

EXPOSE 8000

# Health check via TCP socket on the metrics port — no extra dependencies, and
# it works for any listener without assuming an HTTP path exists.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import socket;s=socket.socket();s.settimeout(2);s.connect(('127.0.0.1',8000));s.close()" || exit 1

# Default entrypoint runs the exporter
# Override with: python -m src.fan_sync for fan sync controller
ENTRYPOINT ["python", "-m", "src.main"]
