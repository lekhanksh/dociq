#!/bin/bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/opt/homebrew/opt/python@3.11/bin:$PATH"

ENV_NAME="${1:-development}"
ENV_FILE=".env.${ENV_NAME}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing ${ENV_FILE}."
  echo "Copy one of: .env.development.example | .env.staging.example | .env.production.example"
  exit 1
fi

echo "Loading ${ENV_FILE}"
set -a
source "$ENV_FILE"
set +a

echo "Starting DocIQ backend (${ENV_NAME})..."
echo "Python version: $(python3 --version)"
echo "Vector backend: ${VECTOR_BACKEND:-memory}"
echo "Backend URL: http://localhost:8000"

python3 -m uvicorn app:app --reload --port 8000
