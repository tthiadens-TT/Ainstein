#!/bin/bash
# run_backup.sh — Wekelijkse backup van de Ainstein bronnenlaag naar 09_Backup in Drive.
# Draait als cron job op de VM. Logs naar logs/backup.log.
#
# Crontab (elke maandag 03:00):
#   0 3 * * 1 /home/thomas/Ainstein/scripts/run_backup.sh

set -a
source /home/thomas/Ainstein/.env
set +a

/home/thomas/Ainstein/.venv311/bin/python3 /home/thomas/Ainstein/scripts/backup_drive.py >> /home/thomas/Ainstein/logs/backup.log 2>&1
