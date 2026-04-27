"""
Tests for Phase 1 backend changes:
- File size validation (413)
- File type validation (415)
- Extraction failure guard (422)
- DELETE /documents/{id} endpoint
- 401 on missing/invalid token
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def _admin_token() -> str:
    r = client.post("/auth/login", json={
        "email": "admin@dociq.com", "password": "demo123", "company_slug": "demo-company"
    })
    assert r.status_code == 200
    return r.json()["access_token"]


def _uploader_token() -> str:
    r = client.post("/auth/login", json={
        "email": "sarah@dociq.com", "password": "demo123", "company_slug": "demo-company"
    })
    assert r.status_code == 200
    return r.json()["access_token"]


# ── File type validation (Req 3.3) ──────────────────────────────────────────

def test_unsupported_file_type_returns_415():
    token = _uploader_token()
    r = client.post(
        "/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"department": "finance"},
        files={"file": ("report.xlsx", b"fake excel content", "application/vnd.ms-excel")},
    )
    assert r.status_code == 415, r.text
    assert "Unsupported file type" in r.json()["detail"]


def test_exe_file_returns_415():
    token = _uploader_token()
    r = client.post(
        "/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"department": "hr"},
        files={"file": ("malware.exe", b"\x4d\x5a\x90", "application/octet-stream")},
    )
    assert r.status_code == 415


# ── File size validation (Req 3.2) ──────────────────────────────────────────

def test_oversized_file_returns_413():
    token = _uploader_token()
    big_content = b"x" * (10 * 1024 * 1024 + 1)  # 10 MB + 1 byte
    r = client.post(
        "/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"department": "finance"},
        files={"file": ("big.txt", big_content, "text/plain")},
    )
    assert r.status_code == 413, r.text
    assert "too large" in r.json()["detail"].lower()


def test_exactly_10mb_is_accepted():
    token = _uploader_token()
    content = b"a" * (10 * 1024 * 1024)  # exactly 10 MB
    r = client.post(
        "/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"department": "finance"},
        files={"file": ("exact.txt", content, "text/plain")},
    )
    assert r.status_code == 200


# ── Extraction failure guard (Req 3.5) ──────────────────────────────────────

def test_corrupt_pdf_returns_422():
    token = _uploader_token()
    r = client.post(
        "/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"department": "finance"},
        files={"file": ("corrupt.pdf", b"this is not a real pdf", "application/pdf")},
    )
    assert r.status_code == 422, r.text


def test_corrupt_docx_returns_422():
    token = _uploader_token()
    r = client.post(
        "/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"department": "hr"},
        files={"file": ("corrupt.docx", b"not a real docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert r.status_code == 422, r.text


# ── DELETE /documents/{id} (Req 5.2 / 5.3) ─────────────────────────────────

def test_delete_nonexistent_doc_as_admin_returns_200():
    """Deleting a non-existent doc should still return 200 with 0 removed chunks."""
    token = _admin_token()
    r = client.delete("/documents/nonexistent-id-xyz", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["removed_chunks"] == 0


def test_delete_real_doc_removes_chunks():
    """Upload a doc then delete it — chunks should be removed."""
    token = _admin_token()
    headers = {"Authorization": f"Bearer {token}"}

    upload = client.post(
        "/upload",
        headers=headers,
        data={"department": "general"},
        files={"file": ("deleteme.txt", b"This document will be deleted.", "text/plain")},
    )
    assert upload.status_code == 200
    doc_id = upload.json()["document_id"]

    delete = client.delete(f"/documents/{doc_id}", headers=headers)
    assert delete.status_code == 200
    assert delete.json()["removed_chunks"] >= 1


def test_viewer_cannot_delete():
    token = client.post("/auth/login", json={
        "email": "viewer@dociq.com", "password": "demo123", "company_slug": "demo-company"
    }).json()["access_token"]
    r = client.delete("/documents/any-id", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


# ── Auth / 401 checks ────────────────────────────────────────────────────────

def test_no_token_returns_401():
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_invalid_token_returns_401():
    r = client.get("/auth/me", headers={"Authorization": "Bearer totally-fake-token"})
    assert r.status_code == 401


def test_wrong_password_returns_401():
    r = client.post("/auth/login", json={
        "email": "admin@dociq.com", "password": "wrongpass", "company_slug": "demo-company"
    })
    assert r.status_code == 401


# ── Valid upload still works ─────────────────────────────────────────────────

def test_valid_txt_upload_succeeds():
    token = _uploader_token()
    r = client.post(
        "/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"department": "finance"},
        files={"file": ("policy.txt", b"Annual leave policy: 20 days per year.", "text/plain")},
    )
    assert r.status_code == 200
    assert r.json()["chunks_indexed"] >= 1


def test_valid_md_upload_succeeds():
    token = _uploader_token()
    r = client.post(
        "/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"department": "hr"},
        files={"file": ("readme.md", b"# HR Policy\n\nAll employees get 20 days leave.", "text/markdown")},
    )
    assert r.status_code == 200
