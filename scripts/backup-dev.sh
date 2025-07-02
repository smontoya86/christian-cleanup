#!/bin/bash

# Simple Development Backup Script
# Usage: ./scripts/backup-dev.sh

echo "🔄 Creating development database backup..."

# Create backups directory
mkdir -p backups

# Create timestamped backup
BACKUP_NAME="dev_backup_$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="backups/${BACKUP_NAME}.sql"

# Backup database
docker exec christiancleanupwindsurf-db-1 pg_dump -U postgres spotify_cleanup > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Backup saved: $BACKUP_FILE"
    echo "📊 Backup contains:"
    
    # Show what's in the backup (using COPY statements)
    USERS=$(grep -c "COPY.*users" "$BACKUP_FILE" 2>/dev/null || echo "0")
    PLAYLISTS=$(grep -c "COPY.*playlists" "$BACKUP_FILE" 2>/dev/null || echo "0")
    SONGS=$(grep -c "COPY.*songs" "$BACKUP_FILE" 2>/dev/null || echo "0")
    ANALYSES=$(grep -c "COPY.*analysis_results" "$BACKUP_FILE" 2>/dev/null || echo "0")
    
    echo "   - $USERS user tables"
    echo "   - $PLAYLISTS playlist tables" 
    echo "   - $SONGS song tables"
    echo "   - $ANALYSES analysis tables"
    
    # Save as latest backup
    echo "$BACKUP_NAME" > backups/latest_dev_backup
    
    echo ""
    echo "💡 To restore later: ./scripts/restore-dev.sh"
else
    echo "❌ Backup failed!"
    exit 1
fi 