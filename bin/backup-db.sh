#!/bin/bash

# Variables
DATABASE_PATH="/home/pi/goonbot/gbdb.sqlite"
BACKUP_DIR="/mnt/gbdb-backup"
BACKUP_NAME="backup_$(date +%Y-%m-%d).db"
RETENTION_DAYS=7

# Make sure backup USB drive exists and is mounted
if [ ! -d "$BACKUP_DIR" ]; then
    echo "Backup directory does not exist!" >&2
    exit 1
fi

# Create a new backup
sqlite3 "$DATABASE_PATH" ".backup '$BACKUP_DIR/$BACKUP_NAME'"

# Check if the backup was successful
if [ $? -eq 0 ]; then
    echo "Backup created: $BACKUP_DIR/$BACKUP_NAME"
else
    echo "Backup failed!" >&2
    exit 1
fi

# Delete backups older than the retention period
find "$BACKUP_DIR" -type f -name "backup_*.db" -mtime +$RETENTION_DAYS -exec rm -f {} \;
