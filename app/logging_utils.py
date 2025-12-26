import time
import uuid
import json
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from datetime import datetime, timezone
from . import metrics


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        request_id = uuid.uuid4().hex
        request.state.request_id = request_id
        # Ensure default log fields
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception as exc:
            status = 500
            raise
        finally:
            latency_ms = int((time.time() - start) * 1000)
            log_obj = {
                "ts": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace('+00:00','Z'),
                "level": "INFO",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": status,
                "latency_ms": latency_ms,
            }
            # Extra webhook fields if present
            try:
                msg_id = getattr(request.state, 'message_id', None)
                dup = getattr(request.state, 'dup', None)
                result = getattr(request.state, 'result', None)
                if msg_id is not None:
                    log_obj['message_id'] = msg_id
                if dup is not None:
                    log_obj['dup'] = bool(dup)
                if result is not None:
                    log_obj['result'] = result
            except Exception:
                pass
            print(json.dumps(log_obj), flush=True)
            # observe prometheus metrics (latency in seconds)
            try:
                metrics.observe_request(request.url.path, status, latency_ms / 1000.0)
            except Exception:
                pass
        return response
