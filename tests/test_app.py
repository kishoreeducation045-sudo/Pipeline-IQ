# tests/test_app.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import app, add, multiply

def test_home():
    client = app.test_client()
    r = client.get("/")
    assert r.status_code == 200
    assert r.get_json() == {"message": "PipelineIQ test app"}

def test_health():
    client = app.test_client()
    r = client.get("/health")
    assert r.status_code == 200

def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0

def test_multiply():
    assert multiply(4, 5) == 20
    assert multiply(0, 100) == 0
