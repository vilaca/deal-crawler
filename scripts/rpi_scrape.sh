#!/usr/bin/env bash
# RPi daily price collection script.
#
# Pulls latest code, scrapes all prices, commits and pushes results.
# Run via cron, e.g.: 0 8 * * * /home/pi/fisher/scripts/rpi_scrape.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$REPO_DIR/logs"
TODAY=$(date -u +'%Y-%m-%d')
LOG_FILE="$LOG_DIR/scrape-$TODAY.log"

mkdir -p "$LOG_DIR"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== Price collection started at $(date -u) ==="

cd "$REPO_DIR"

# Pull latest changes
echo "Pulling latest..."
SELF="$SCRIPT_DIR/$(basename "$0")"
HASH_BEFORE=$(md5sum "$SELF" | cut -d' ' -f1)
git pull --ff-only origin main
HASH_AFTER=$(md5sum "$SELF" | cut -d' ' -f1)

if [ "$HASH_BEFORE" != "$HASH_AFTER" ] && [ "${RPi_REEXEC:-}" != "1" ]; then
    echo "Script updated, re-executing..."
    RPi_REEXEC=1 exec "$SELF" "$@"
fi

# Activate virtual environment if present
if [ -d "$REPO_DIR/venv" ]; then
    # shellcheck disable=SC1091
    source "$REPO_DIR/venv/bin/activate"
fi

# Run collection
echo "Collecting prices..."
python collect_all_prices.py --verbose

# Verify output
OUTPUT_FILE="history/all/$TODAY.csv"
if [ ! -s "$OUTPUT_FILE" ]; then
    echo "Error: $OUTPUT_FILE is empty or missing" >&2
    exit 1
fi

echo "Output verified: $OUTPUT_FILE"

# Commit and push (pull --rebase first in case remote changed during scrape)
git add "$OUTPUT_FILE"
if git diff --staged --quiet; then
    echo "No changes to commit"
else
    git commit -m "Collect all prices - $TODAY"
    git pull --rebase origin main
    git push origin main
    echo "Pushed to origin"
fi

# Clean up logs older than 30 days
find "$LOG_DIR" -name "scrape-*.log" -mtime +30 -delete 2>/dev/null || true

echo "=== Done at $(date -u) ==="
