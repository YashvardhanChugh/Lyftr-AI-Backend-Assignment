import hmac
import hashlib
import json
import time
import logging
from fastapi import FastAPI, Request, Header, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from starlette.responses import Response
from . import config, storage, models, metrics
from .logging_utils import StructuredLoggingMiddleware
from typing import Optional
from datetime import datetime

# Silence uvicorn's default access/error logs so logs contain our single JSON line per request
logging.getLogger('uvicorn.access').handlers = [logging.NullHandler()]
logging.getLogger('uvicorn.error').handlers = [logging.NullHandler()]

app = FastAPI()
app.add_middleware(StructuredLoggingMiddleware)

# Initialize DB on startup
@app.on_event('startup')
async def startup():
    storage.init_db()


@app.post('/webhook')
async def webhook(request: Request, x_signature: Optional[str] = Header(None)):
    body = await request.body()
    # signature validation
    secret = config.WEBHOOK_SECRET or ''
    if not x_signature:
        # ensure log includes result and message_id if parseable
        try:
            payload_json = json.loads(body.decode('utf-8'))
            request.state.message_id = payload_json.get('message_id') if isinstance(payload_json, dict) else None
        except Exception:
            request.state.message_id = None
        request.state.result = 'invalid_signature'
        metrics.webhook_metric('invalid_signature')
        raise HTTPException(status_code=401, detail='invalid signature')
    computed = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed, x_signature):
        try:
            payload_json = json.loads(body.decode('utf-8'))
            request.state.message_id = payload_json.get('message_id') if isinstance(payload_json, dict) else None
        except Exception:
            request.state.message_id = None
        request.state.result = 'invalid_signature'
        metrics.webhook_metric('invalid_signature')
        raise HTTPException(status_code=401, detail='invalid signature')

    # parse and validate payload
    try:
        payload_json = json.loads(body.decode('utf-8'))
    except Exception:
        # Let pydantic raise
        payload_json = None
    try:
        payload = models.WebhookPayload.parse_obj(payload_json)
    except Exception:
        # validation error
        request.state.message_id = payload_json.get('message_id') if isinstance(payload_json, dict) else None
        request.state.result = 'validation_error'
        metrics.webhook_metric('validation_error')
        raise HTTPException(status_code=422, detail='validation error')

    # Insert with idempotency
    request.state.message_id = payload.message_id
    result = storage.insert_message(payload.message_id, payload.from_, payload.to, payload.ts, payload.text)
    request.state.dup = (result == 'duplicate')
    request.state.result = result
    metrics.webhook_metric(result)
    return JSONResponse({'status': 'ok'})


@app.get('/messages')
async def get_messages(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    from_msisdn: Optional[str] = Query(None, alias='from'),
    since: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
):
    # validate since if present
    if since is not None:
        try:
            if not since.endswith('Z'):
                raise ValueError()
            datetime.strptime(since, "%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            raise HTTPException(status_code=422, detail='invalid since')
    rows, total = storage.query_messages(limit, offset, from_msisdn, since, q)
    data = [
        {
            'message_id': r[0],
            'from_msisdn': r[1],
            'to_msisdn': r[2],
            'ts': r[3],
            'text': r[4],
            'created_at': r[5],
        }
        for r in rows
    ]
    return JSONResponse({'data': data, 'total': total, 'limit': limit, 'offset': offset})


@app.get('/stats')
async def get_stats():
    s = storage.stats()
    return JSONResponse(s)


@app.get('/health/live')
async def live():
    return JSONResponse({}, status_code=200)


@app.get('/health/ready')
async def ready():
    if not config.WEBHOOK_SECRET:
        return JSONResponse({'detail': 'not ready'}, status_code=503)
    try:
        # DB reachable and schema initialized
        db_ok = storage.db_ready()
        if not db_ok:
            return JSONResponse({'detail': 'not ready'}, status_code=503)
    except Exception:
        return JSONResponse({'detail': 'not ready'}, status_code=503)
    return JSONResponse({}, status_code=200)


@app.get('/metrics')
async def metrics_endpoint():
    return metrics.metrics_response()
