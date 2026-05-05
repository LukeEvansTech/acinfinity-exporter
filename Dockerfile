FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

USER 65534:65534

EXPOSE 8000

# Health check via TCP socket on the listening port — no extra deps,
# works for any uvicorn/gunicorn/asgi listener.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import socket,sys;s=socket.socket();s.settimeout(2);s.connect(('127.0.0.1',8000));s.close()" || exit 1
ENTRYPOINT ["python", "-m", "src.main"]
