from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"

def test_root():
    response = client.get("/")
    assert response.status_code == 200
