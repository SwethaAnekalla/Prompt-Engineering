#!/bin/bash
# Backup Script for Meeting Minutes Database
# This script can be scheduled via Cron or a hosting platform's built-in scheduler (e.g., Render Cron Jobs).

set -e

BACKUP_DIR="backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Check which database is being used
if [[ "$DATABASE_URL" == postgresql* ]]; then
    echo "PostgreSQL detected. Running pg_dump..."
    BACKUP_FILE="${BACKUP_DIR}/db_backup_${TIMESTAMP}.sql"
    pg_dump "$DATABASE_URL" > "$BACKUP_FILE"
    echo "Backup saved to $BACKUP_FILE"
else
    echo "SQLite detected. Creating a copy of the database file..."
    DB_FILE="meeting_minutes.db"
    if [ -f "$DB_FILE" ]; then
        BACKUP_FILE="${BACKUP_DIR}/meeting_minutes_${TIMESTAMP}.sqlite3.bak"
        cp "$DB_FILE" "$BACKUP_FILE"
        echo "Backup saved to $BACKUP_FILE"
    else
        echo "SQLite database file ($DB_FILE) not found!"
        exit 1
    fi
fi

# Optional: Upload to S3 or clean up old backups here
# find "$BACKUP_DIR" -type f -mtime +30 -delete
