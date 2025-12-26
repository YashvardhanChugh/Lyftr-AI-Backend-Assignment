from fastapi.testclient import TestClient
from app.main import app
from app import storage

client = TestClient(app)


def test_stats_empty(tmp_path, monkeypatch):
    db = tmp_path / 's.db'
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{db}')
    monkeypatch.setenv('WEBHOOK_SECRET', 's')
    storage.init_db()
    r = client.get('/stats')
    assert r.status_code == 200
    j = r.json()
    assert j['total_messages'] == 0
    assert j['senders_count'] == 0
    assert j['messages_per_sender'] == []
    assert j['first_message_ts'] is None
    assert j['last_message_ts'] is None


def test_stats_with_data(tmp_path, monkeypatch):
    db = tmp_path / 's2.db'
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{db}')
    monkeypatch.setenv('WEBHOOK_SECRET', 's')
    storage.init_db()
    storage.insert_message('m1', '+1', '+2', '2025-01-01T00:00:00Z', 'a')
    storage.insert_message('m2', '+1', '+2', '2025-01-02T00:00:00Z', 'b')
    storage.insert_message('m3', '+3', '+2', '2025-01-03T00:00:00Z', 'c')
    r = client.get('/stats')
    assert r.status_code == 200
    j = r.json()
    assert j['total_messages'] == 3
    assert j['senders_count'] == 2
    assert any(item['from'] == '+1' and item['count'] == 2 for item in j['messages_per_sender'])
    assert j['first_message_ts'] == '2025-01-01T00:00:00Z'
    assert j['last_message_ts'] == '2025-01-03T00:00:00Z'
