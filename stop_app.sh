#!/bin/bash

set -u

BACKEND_PORT=8000
DB_NAME="live_game"
DB_HOST="192.168.250.3"
DB_USER="root"

echo "====================================================================="
echo " Stopping Click Game"
echo "====================================================================="

# ---------------------------------------------------------------------
# 1. Stop Python Backend
# ---------------------------------------------------------------------
echo
echo "[1/3] Stopping Python Backend on port ${BACKEND_PORT}..."

PID=$(lsof -t -i:${BACKEND_PORT} 2>/dev/null)

if [ -n "$PID" ]; then
    kill -9 $PID
    echo "   Backend stopped. PID: $PID"
else
    echo "   Backend was not running."
fi

# ---------------------------------------------------------------------
# 2. Stop Nginx
# ---------------------------------------------------------------------
echo
echo "[2/3] Stopping Nginx Web Server..."

if systemctl is-active --quiet nginx; then
    systemctl stop nginx
    echo "   Nginx stopped."
else
    echo "   Nginx was not running."
fi

# ---------------------------------------------------------------------
# 3. Optional Database Cleanup
# ---------------------------------------------------------------------
echo
echo "[3/3] Database..."

if [ "${1:-}" = "--clean-db" ]; then

    echo
    echo "   WARNING: This will TRUNCATE all tables in:"
    echo "   Database : ${DB_NAME}"
    echo "   Host     : ${DB_HOST}"
    echo

    read -r -p "   Type DELETE to continue: " CONFIRM

    if [ "$CONFIRM" != "DELETE" ]; then
        echo "   Database cleanup cancelled."
        exit 0
    fi

    echo
    read -r -s -p "   Enter MariaDB password: " DB_PASSWORD
    echo

    # Get table list
    echo
    echo "   Getting table list..."

    TABLES=$(MYSQL_PWD="$DB_PASSWORD" mysql \
        -h "$DB_HOST" \
        -u "$DB_USER" \
        "$DB_NAME" \
        -N \
        -e "SHOW TABLES;")

    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to connect to database."
        unset DB_PASSWORD
        exit 1
    fi

    if [ -z "$TABLES" ]; then
        echo "   No tables found."
        unset DB_PASSWORD
    else
        echo "   Truncating tables..."

        # Disable foreign-key checks and truncate ALL tables
        # in ONE MySQL session.
        SQL="SET FOREIGN_KEY_CHECKS=0;"

        while IFS= read -r TABLE; do
            [ -z "$TABLE" ] && continue

            echo "      TRUNCATE $TABLE"

            SQL="${SQL} TRUNCATE TABLE \`${TABLE}\`;"
        done <<< "$TABLES"

        SQL="${SQL} SET FOREIGN_KEY_CHECKS=1;"

        MYSQL_PWD="$DB_PASSWORD" mysql \
            -h "$DB_HOST" \
            -u "$DB_USER" \
            "$DB_NAME" \
            -e "$SQL"

        if [ $? -ne 0 ]; then
            echo
            echo "ERROR: Failed to truncate database tables."
            unset DB_PASSWORD
            exit 1
        fi

        unset DB_PASSWORD

        echo
        echo "   Database tables truncated successfully."
    fi

else
    echo "   Database was NOT modified."
    echo "   Use './stop_app.sh --clean-db' to truncate ${DB_NAME}."
fi

echo
echo "====================================================================="
echo " Click Game is now offline."
echo "====================================================================="

