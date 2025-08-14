FROM python:3.11-slim

# system deps for common ML libs; keep small to start
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git && rm -rf /var/lib/apt/lists/*

# cache-friendly: first copy requirements, then install
WORKDIR /PYTHON
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy app
COPY . .
COPY startup.sh /startup.sh

# allow runtime env overrides for caches later
ENV HF_HOME=/cache \
    TRANSFORMERS_CACHE=/cache/transformers

ENTRYPOINT ["/startup.sh"]
