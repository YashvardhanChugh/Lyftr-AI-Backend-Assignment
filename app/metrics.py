from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
from prometheus_client.core import REGISTRY
from fastapi import Response

# Counters and histogram with labels
http_requests_total = Counter('http_requests_total', 'HTTP requests total', ['path','status'])
webhook_requests_total = Counter('webhook_requests_total', 'Webhook requests total', ['result'])
http_request_latency_seconds = Histogram('http_request_latency_seconds', 'Request latency seconds', ['path'])


def metrics_response():
    data = generate_latest(REGISTRY)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


def observe_request(path: str, status: str, latency_s: float):
    try:
        http_requests_total.labels(path=path, status=str(status)).inc()
        http_request_latency_seconds.labels(path=path).observe(latency_s)
    except Exception:
        pass


def webhook_metric(result: str):
    try:
        webhook_requests_total.labels(result=result).inc()
    except Exception:
        pass
