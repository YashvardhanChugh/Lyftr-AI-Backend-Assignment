from fastapi.testclient import TestClient
from app.main import app
from app import storage
from datetime import datetime

client = TestClient(app)


def test_messages_listing(tmp_path, monkeypatch):
    db = tmp_path / 'msgs.db'
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{db}')
    monkeypatch.setenv('WEBHOOK_SECRET', 's')
    storage.init_db()
    storage.insert_message('a1', '+111', '+222', '2025-01-01T00:00:00Z', 'hello world')
    storage.insert_message('a2', '+111', '+333', '2025-01-02T00:00:00Z', 'second')
    r = client.get('/messages')
    assert r.status_code == 200
    j = r.json()
    assert j['total'] == 2
    assert len(j['data']) == 2
    # filter from
    r2 = client.get('/messages', params={'from': '+111'})
    assert r2.status_code == 200
    assert r2.json()['total'] == 2
    # since filter
    r3 = client.get('/messages', params={'since': '2025-01-02T00:00:00Z'})
    assert r3.status_code == 200
    assert r3.json()['total'] == 1


def test_pagination_limits(tmp_path, monkeypatch):
    db = tmp_path / 'msgs2.db'
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{db}')
    monkeypatch.setenv('WEBHOOK_SECRET', 's')
    storage.init_db()
    for i in range(5):
        storage.insert_message(f'id{i}', f'+1{i}', '+99', f'2025-01-0{i+1:02d}T00:00:00Z', 'x')
    r = client.get('/messages', params={'limit': 2, 'offset': 1})
    assert r.status_code == 200
    j = r.json()
    assert j['limit'] == 2
    assert j['offset'] == 1
    assert j['total'] == 5
    assert len(j['data']) == 2
