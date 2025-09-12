#!/usr/bin/env sh
set -e  # exit if any command fails

# --- Your custom startup commands ---
echo "Preparing uploads directory..."
# Respect UPLOAD_DIR if provided, else default to /PYTHON/uploads (matches app default)
DEST_UPLOAD_DIR=${UPLOAD_DIR:-/PYTHON/uploads}
mkdir -p "$DEST_UPLOAD_DIR"

# If a MyProfile file is shipped or mounted at /app, copy it into uploads
if [ -n "$MYPROFILE_FILE" ] && [ -f "/app/$MYPROFILE_FILE" ]; then
  echo "Seeding MyProfile file: /app/$MYPROFILE_FILE -> $DEST_UPLOAD_DIR/$MYPROFILE_FILE"
  cp "/app/$MYPROFILE_FILE" "$DEST_UPLOAD_DIR/$MYPROFILE_FILE" || true
else
  echo "No MyProfile seed found at /app/$MYPROFILE_FILE (MYPROFILE_FILE='$MYPROFILE_FILE')."
fi

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
