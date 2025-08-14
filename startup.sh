#!/usr/bin/env sh
set -e  # exit if any command fails

# --- Your custom startup commands ---
# echo "Creating folder in ephemeral storage..."
# mkdir -p /mnt/storage/uploads
# mkdir -p /mnt/storage/logs
# mkdir -p /mnt/storage/db_store
# mkdir -p /mnt/storage/vector_store`

# chmod -R 775 /mnt/storage/uploads
# chmod -R 775 /mnt/storage/logs
# chmod -R 775 /mnt/storage/db_store
# chmod -R 775 /mnt/storage/vector_store

# You can add other tasks here, e.g., data prep, warmup
# python scripts/warmup.py

# --- Finally, start your main app ---
echo "Starting application..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
