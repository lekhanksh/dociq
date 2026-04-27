"""RBAC tests using the demo accounts in app.py"""
import io
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def _token(email: str, password: str = "demo123") -> str:
    r = client.post("/auth/login", json={
        "email": email, "password": password, "company_slug": "demo-company"
    })
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_viewer_cannot_upload():
    token = _token("viewer@dociq.com")
    r = client.post(
        "/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"department": "hr"},
        files={"file": ("test.txt", b"some content", "text/plain")},
    )
    assert r.status_code == 403


def test_uploader_can_upload():
    token = _token("sarah@dociq.com")
    r = client.post(
        "/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"department": "finance"},
        files={"file": ("test.txt", b"Finance policy content.", "text/plain")},
    )
    assert r.status_code == 200


def test_non_admin_cannot_delete():
    token = _token("sarah@dociq.com")
    r = client.delete("/documents/fake-id-123", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_admin_can_access_stats():
    token = _token("admin@dociq.com")
    r = client.get("/admin/stats", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_non_admin_cannot_access_stats():
    token = _token("viewer@dociq.com")
    r = client.get("/admin/stats", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
