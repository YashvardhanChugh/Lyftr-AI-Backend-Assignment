import hmac
import hashlib
import json
from fastapi.testclient import TestClient
from app.main import app
from app import config, storage

client = TestClient(app)


def sign(body: bytes):
    return hmac.new((config.WEBHOOK_SECRET or '').encode(), body, hashlib.sha256).hexdigest()


def test_webhook_create_and_idempotent(tmp_path, monkeypatch):
    # use temporary DB
    db = tmp_path / 'test.db'
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{db}')
    monkeypatch.setenv('WEBHOOK_SECRET', 'secret')
    # re-init storage
    storage.init_db()
    payload = {"message_id": "m1", "from": "+123", "to": "+456", "ts": "2025-01-15T10:00:00Z", "text": "Hello"}
    body = json.dumps(payload).encode()
    sig = hmac.new(b'secret', body, hashlib.sha256).hexdigest()
    r = client.post('/webhook', data=body, headers={'X-Signature': sig, 'Content-Type': 'application/json'})
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    # idempotent
    r2 = client.post('/webhook', data=body, headers={'X-Signature': sig, 'Content-Type': 'application/json'})
    assert r2.status_code == 200
    assert r2.json() == {"status": "ok"}


def test_webhook_invalid_signature(tmp_path, monkeypatch):
    db = tmp_path / 'test2.db'
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{db}')
    monkeypatch.setenv('WEBHOOK_SECRET', 'secret')
    storage.init_db()
    payload = {"message_id": "m2", "from": "+123", "to": "+456", "ts": "2025-01-15T10:00:00Z"}
    body = json.dumps(payload).encode()
    r = client.post('/webhook', data=body, headers={'X-Signature': 'bad', 'Content-Type': 'application/json'})
    assert r.status_code == 401
    assert r.json().get('detail') == 'invalid signature'


def test_webhook_validation_error(tmp_path, monkeypatch):
    db = tmp_path / 'test3.db'
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{db}')
    monkeypatch.setenv('WEBHOOK_SECRET', 'secret')
    storage.init_db()
    payload = {"message_id": "", "from": "nope", "to": "+456", "ts": "not-a-ts"}
    body = json.dumps(payload).encode()
    sig = hmac.new(b'secret', body, hashlib.sha256).hexdigest()
    r = client.post('/webhook', data=body, headers={'X-Signature': sig, 'Content-Type': 'application/json'})
    assert r.status_code == 422
