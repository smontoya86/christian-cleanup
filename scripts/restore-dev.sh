#!/bin/bash

# Simple Development Restore Script
# Usage: ./scripts/restore-dev.sh

if [ ! -f "backups/latest_dev_backup" ]; then
    echo "❌ No backup found. Run ./scripts/backup-dev.sh first."
    exit 1
fi

BACKUP_NAME=$(cat backups/latest_dev_backup)
BACKUP_FILE="backups/${BACKUP_NAME}.sql"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "🔄 Restoring from backup: $BACKUP_NAME"

# Drop and recreate database
docker exec christiancleanupwindsurf-db-1 psql -U postgres -c "DROP DATABASE IF EXISTS spotify_cleanup;"
docker exec christiancleanupwindsurf-db-1 psql -U postgres -c "CREATE DATABASE spotify_cleanup;"

# Restore from backup
docker exec -i christiancleanupwindsurf-db-1 psql -U postgres spotify_cleanup < "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Database restored successfully!"
    echo "🔄 Restart your application to see the restored data."
else
    echo "❌ Restore failed!"
    exit 1
fi 