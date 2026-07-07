FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

USER 65534:65534

EXPOSE 8000

# Default entrypoint runs the exporter
# Override with: python -m src.fan_sync for fan sync controller
ENTRYPOINT ["python", "-m", "src.main"]
