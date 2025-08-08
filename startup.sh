#!/bin/bash
set -euo pipefail

APP_HOME="/home/site/wwwroot"
VENV="/home/pyenv"
REQ_FILE="${APP_HOME}/requirements.txt"
HASH_FILE="/home/requirements.sha256"

# 1) One-time venv (lives under /home, which is persistent across deploys)
if [ ! -d "${VENV}" ]; then
  echo "[init] creating venv at ${VENV}"
  python3 -m venv "${VENV}"
  "${VENV}/bin/python" -m pip install --upgrade pip wheel
fi

# 2) Install/skip dependencies based on requirements.txt hash
if [ -f "${REQ_FILE}" ]; then
  CUR_HASH=$(sha256sum "${REQ_FILE}" | awk '{print $1}')
  if [ ! -f "${HASH_FILE}" ] || [ "$(cat ${HASH_FILE})" != "${CUR_HASH}" ]; then
    echo "[deps] requirements changed → installing…"
    "${VENV}/bin/pip" install --upgrade -r "${REQ_FILE}"
    echo "${CUR_HASH}" > "${HASH_FILE}"
  else
    echo "[deps] requirements unchanged → skipping pip install."
  fi
else
  echo "[warn] ${REQ_FILE} not found; skipping dependency install."
fi

# 3) Start your app (FastAPI/Gunicorn)
exec "${VENV}/bin/gunicorn" -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
