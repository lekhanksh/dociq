#!/bin/bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"
DOC_PATH="${1:-./sample_docs/policy_sample.txt}"
QUESTION="${2:-How many annual leave days do full-time employees receive?}"

if [ ! -f "$DOC_PATH" ]; then
  echo "Document not found: $DOC_PATH"
  echo "Usage: ./scripts/local_e2e_test.sh [doc_path] [question]"
  exit 1
fi

echo "1) Health check..."
curl -sS "${API_BASE_URL}/health" >/dev/null
echo "   OK"

echo "2) Login..."
TOKEN=$(python3 - <<PY
import requests
resp = requests.post(
    "${API_BASE_URL}/auth/login",
    json={"email":"admin@dociq.com","password":"demo123","company_slug":"demo-company"},
    timeout=10,
)
resp.raise_for_status()
print(resp.json()["access_token"])
PY
)
echo "   OK"

echo "3) Upload sample document..."
python3 - <<PY
import requests
with open("${DOC_PATH}", "rb") as f:
    resp = requests.post(
        "${API_BASE_URL}/upload",
        headers={"Authorization": f"Bearer ${TOKEN}"},
        data={"department":"finance"},
        files={"file": ("policy_sample.txt", f, "text/plain")},
        timeout=30,
    )
resp.raise_for_status()
print("   Indexed chunks:", resp.json().get("chunks_indexed"))
PY

echo "4) Ask question..."
python3 - <<PY
import json
import requests
resp = requests.post(
    "${API_BASE_URL}/query",
    headers={"Authorization": f"Bearer ${TOKEN}"},
    json={"question":"${QUESTION}"},
    timeout=30,
)
resp.raise_for_status()
data = resp.json()
print("   Answer:")
print(data.get("answer", ""))
print("")
print("   Sources:")
for s in data.get("sources", []):
    print(f"   - {s.get('filename')} (similarity={s.get('similarity')})")
PY

echo ""
echo "Local E2E test passed."
