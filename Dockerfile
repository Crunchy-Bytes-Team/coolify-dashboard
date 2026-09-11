FROM python:3.13-slim
WORKDIR /app
COPY service.py /app/service.py
COPY alerts.py /app/alerts.py
COPY dist /app/dist
COPY deploy/coolify-gateway.yaml /app/gateway.yaml
RUN mkdir -p /data && chown 10001:10001 /data
USER 10001:10001
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
CMD ["python", "service.py", "dashboard"]
