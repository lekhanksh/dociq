from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def _login_token() -> str:
    response = client.post(
        "/auth/login",
        json={
            "email": "admin@dociq.com",
            "password": "demo123",
            "company_slug": "demo-company",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_health_login_me_flow():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"

    token = _login_token()
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "admin@dociq.com"


def test_upload_query_collections_flow():
    token = _login_token()
    headers = {"Authorization": f"Bearer {token}"}

    upload = client.post(
        "/upload",
        headers=headers,
        data={"department": "finance"},
        files={"file": ("policy.txt", b"Vacation policy allows 20 annual leave days.", "text/plain")},
    )
    assert upload.status_code == 200, upload.text
    assert upload.json()["chunks_indexed"] >= 1

    query = client.post("/query", headers=headers, json={"question": "How many annual leave days?"})
    assert query.status_code == 200, query.text
    body = query.json()
    assert "answer" in body
    assert isinstance(body.get("sources"), list)

    collections = client.get("/collections/info", headers=headers)
    assert collections.status_code == 200
    assert "finance" in collections.json()
