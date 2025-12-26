# Lyftr AI Backend (FastAPI)

## How to run

Requirements: Docker & Docker Compose.

Start the service:

```bash
make up
```

The API will be available at http://localhost:8000

To stop:

```bash
make down
```

View logs:

```bash
make logs
```

Run tests locally (requires Python and deps):

```bash
make test
```


## Example curl commands

Register a webhook message (replace SECRET with your `WEBHOOK_SECRET`):

```bash
BODY='{"message_id":"m1","from":"+123","to":"+444","ts":"2025-01-15T10:00:00Z","text":"Hello"}'
SIG=$(python -c "import hmac,hashlib,sys; print(hmac.new(b'change_me', b'$BODY', hashlib.sha256).hexdigest())")

curl -X POST http://localhost:8000/webhook -H "Content-Type: application/json" -H "X-Signature: $SIG" -d "$BODY"
```

List messages:

```bash
curl 'http://localhost:8000/messages?limit=10&offset=0'
```

Stats:

```bash
curl http://localhost:8000/stats
```

Health:

```bash
curl http://localhost:8000/health/ready
```

Metrics:

```bash
curl http://localhost:8000/metrics
```


## Design decisions

- HMAC verification: uses raw request body bytes and HMAC-SHA256 with the secret from `WEBHOOK_SECRET`. Comparison uses `hmac.compare_digest` to avoid timing attacks.
- Idempotency: `message_id` is the primary key in SQLite; attempts to insert a duplicate key are caught and reported as `duplicate` without errors.
- Pagination: `limit` and `offset` query params with enforced bounds via FastAPI query validators. Total count is computed separately ignoring `limit` and `offset`.
- Stats: computed from SQL queries. Returns top 10 senders sorted by count desc.
- Logging: structured JSON logs printed one line per request by middleware. Each log includes timestamps, request id, method, path, status, latency and webhook-specific fields when applicable.


## Setup Used

- VSCode + GitHub Copilot + ChatGPT

