#!/bin/bash

# =====================================================================
# CLICK GAME - UNIFIED DEPLOYMENT SCRIPT
#
# Offline-safe deployment for:
#   Backend : FastAPI / Python 3.11
#   Frontend: Angular
#   Web     : Nginx
#
# Backend project:
#   /opt/myapp/backend/
#       +-- pyproject.toml
#       +-- venv/
#       +-- src/
#           +-- click_game/
#               +-- main.py
# =====================================================================

set -u

# =====================================================================
# CONFIGURATION
# =====================================================================

BACKEND_DIR="/opt/myapp/backend"
FRONTEND_DIR="/opt/myapp/frontend"
WEB_ROOT="/var/www/angular-app"

BACKEND_PORT=8000
BACKEND_HOST="192.168.250.3"

VENV_DIR="$BACKEND_DIR/venv"
PYTHON="$VENV_DIR/bin/python"

BACKEND_LOG="$BACKEND_DIR/backend.log"

ANGULAR_DIST="$FRONTEND_DIR/dist/click-game/browser"


# =====================================================================
# START
# =====================================================================

echo "====================================================================="
echo " Starting Click Game Unified Deployment"
echo "====================================================================="


# =====================================================================
# 1. CHECK DIRECTORIES
# =====================================================================

echo ""
echo "[1/7] Checking directories..."

if [ ! -d "$BACKEND_DIR" ]; then
    echo "ERROR: Backend directory not found:"
    echo "       $BACKEND_DIR"
    exit 1
fi

if [ ! -d "$FRONTEND_DIR" ]; then
    echo "ERROR: Frontend directory not found:"
    echo "       $FRONTEND_DIR"
    exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "ERROR: Python virtual environment not found:"
    echo "       $VENV_DIR"
    echo ""
    echo "This deployment script does not create or install a new"
    echo "environment because this server is offline."
    exit 1
fi

if [ ! -x "$PYTHON" ]; then
    echo "ERROR: Python executable not found:"
    echo "       $PYTHON"
    exit 1
fi

echo "   Backend : $BACKEND_DIR"
echo "   Frontend: $FRONTEND_DIR"
echo "   Web root: $WEB_ROOT"
echo "   Venv    : $VENV_DIR"


# =====================================================================
# 2. VERIFY PYTHON ENVIRONMENT
# =====================================================================

echo ""
echo "[2/7] Verifying Python environment..."

echo "   Python:"
"$PYTHON" --version

echo ""
echo "   Checking required Python modules..."

"$PYTHON" -c "
import fastapi
import uvicorn
import mysql.connector
import jose
import pydantic

print('   FastAPI:', fastapi.__version__)
print('   Uvicorn:', uvicorn.__version__)
print('   MySQL Connector:', mysql.connector.__version__)
print('   python-jose: OK')
print('   Pydantic:', pydantic.__version__)
" || {
    echo ""
    echo "ERROR: One or more required Python modules are missing."
    echo ""
    echo "Installed packages:"
    "$PYTHON" -m pip list
    exit 1
}

echo "   Python environment OK."


# =====================================================================
# 3. VERIFY REFACTORED BACKEND
# =====================================================================

echo ""
echo "[3/7] Verifying refactored backend..."

if [ ! -f "$BACKEND_DIR/pyproject.toml" ]; then
    echo "ERROR: pyproject.toml not found:"
    echo "       $BACKEND_DIR/pyproject.toml"
    exit 1
fi

if [ ! -d "$BACKEND_DIR/src/click_game" ]; then
    echo "ERROR: Python package directory not found:"
    echo "       $BACKEND_DIR/src/click_game"
    exit 1
fi

if [ ! -f "$BACKEND_DIR/src/click_game/main.py" ]; then
    echo "ERROR: FastAPI application not found:"
    echo "       $BACKEND_DIR/src/click_game/main.py"
    exit 1
fi

echo "   Project structure OK."

# ---------------------------------------------------------------------
# Verify that click_game.main can actually be imported.
#
# No pip install is performed.
# The source directory is supplied directly through PYTHONPATH.
# ---------------------------------------------------------------------

echo "   Testing application import..."

PYTHONPATH="$BACKEND_DIR/src" \
"$PYTHON" -c "
from click_game.main import app
print('   FastAPI application import: OK')
print('   Application:', app.title)
" || {
    echo ""
    echo "ERROR: FastAPI application import failed."
    echo ""
    echo "Check:"
    echo "  $BACKEND_LOG"
    echo ""
    exit 1
}

echo "   Backend verification OK."


# =====================================================================
# 4. BUILD ANGULAR FRONTEND
# =====================================================================

echo ""
echo "[4/7] Building Angular frontend..."

cd "$FRONTEND_DIR" || {
    echo "ERROR: Cannot enter frontend directory:"
    echo "       $FRONTEND_DIR"
    exit 1
}

# ---------------------------------------------------------------------
# node_modules must already exist because the server is offline.
# ---------------------------------------------------------------------

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "ERROR: node_modules not found:"
    echo "       $FRONTEND_DIR/node_modules"
    echo ""
    echo "This server is offline, so npm install cannot be performed."
    exit 1
fi

echo "   node_modules found."

echo "   Running Angular production build..."

npx ng build --configuration production || {
    echo ""
    echo "ERROR: Angular production build failed."
    exit 1
}

if [ ! -d "$ANGULAR_DIST" ]; then
    echo ""
    echo "ERROR: Angular build output not found:"
    echo "       $ANGULAR_DIST"
    exit 1
fi

echo "   Angular build completed successfully."


# =====================================================================
# 5. STOP OLD BACKEND
# =====================================================================

echo ""
echo "[5/7] Checking backend port $BACKEND_PORT..."

PIDS=$(lsof -t -i:"$BACKEND_PORT" 2>/dev/null || true)

if [ -n "$PIDS" ]; then

    echo "   Existing backend process(es):"
    echo "$PIDS"

    while read -r PID; do
        if [ -n "$PID" ]; then
            echo "   Stopping PID $PID..."
            kill "$PID" 2>/dev/null || true
        fi
    done <<< "$PIDS"

    sleep 2

    # ---------------------------------------------------------------
    # Force kill only if process did not stop normally.
    # ---------------------------------------------------------------

    PIDS=$(lsof -t -i:"$BACKEND_PORT" 2>/dev/null || true)

    if [ -n "$PIDS" ]; then
        echo "   Process still running. Force stopping..."

        while read -r PID; do
            if [ -n "$PID" ]; then
                kill -9 "$PID" 2>/dev/null || true
            fi
        done <<< "$PIDS"

        sleep 1
    fi

else
    echo "   Port $BACKEND_PORT is already clean."
fi


# =====================================================================
# 6. START BACKEND
# =====================================================================

echo ""
echo "[6/7] Starting FastAPI backend..."

cd "$BACKEND_DIR" || {
    echo "ERROR: Cannot enter backend directory."
    exit 1
}

echo "   Host : $BACKEND_HOST"
echo "   Port : $BACKEND_PORT"
echo "   App  : click_game.main:app"
echo "   Src  : $BACKEND_DIR/src"
echo "   Log  : $BACKEND_LOG"

# ---------------------------------------------------------------------
# IMPORTANT:
#
# We DO NOT run:
#
#     pip install -e .
#
# because this server is offline and pyproject.toml currently requests
# setuptools>=68 while the existing venv contains setuptools 65.5.1.
#
# Instead, tell Python/Uvicorn directly where src/ is located.
# ---------------------------------------------------------------------

nohup env PYTHONPATH="$BACKEND_DIR/src" \
    "$PYTHON" -m uvicorn \
    click_game.main:app \
    --host "$BACKEND_HOST" \
    --port "$BACKEND_PORT" \
    --ws websockets \
    > "$BACKEND_LOG" 2>&1 &

BACKEND_PID=$!

echo "   Backend PID: $BACKEND_PID"

sleep 3


# ---------------------------------------------------------------------
# Verify process
# ---------------------------------------------------------------------

if ! kill -0 "$BACKEND_PID" 2>/dev/null; then

    echo ""
    echo "ERROR: Backend process failed to start."
    echo ""
    echo "Last 50 lines of backend.log:"
    echo "---------------------------------------------------------------------"
    tail -n 50 "$BACKEND_LOG"
    echo "---------------------------------------------------------------------"

    exit 1
fi

echo "   Backend process is running."


# ---------------------------------------------------------------------
# Verify port
# ---------------------------------------------------------------------

sleep 1

if lsof -i:"$BACKEND_PORT" >/dev/null 2>&1; then
    echo "   Port $BACKEND_PORT is listening."
else

    echo ""
    echo "ERROR: Backend process exists but port $BACKEND_PORT is not listening."
    echo ""
    echo "Last 50 lines of backend.log:"
    echo "---------------------------------------------------------------------"
    tail -n 50 "$BACKEND_LOG"
    echo "---------------------------------------------------------------------"

    exit 1
fi


# =====================================================================
# 7. DEPLOY ANGULAR + RESTART NGINX
# =====================================================================

echo ""
echo "[7/7] Deploying Angular files..."

mkdir -p "$WEB_ROOT" || {
    echo "ERROR: Cannot create web root:"
    echo "       $WEB_ROOT"
    exit 1
}

echo "   Removing old frontend files..."

rm -rf "$WEB_ROOT"/*

echo "   Copying new Angular production files..."

cp -r "$ANGULAR_DIST"/* "$WEB_ROOT"/ || {
    echo "ERROR: Failed to copy Angular build."
    exit 1
}

echo "   Setting nginx permissions..."

chown -R nginx:nginx "$WEB_ROOT"
chmod -R 755 "$WEB_ROOT"


# ---------------------------------------------------------------------
# Restart Nginx
# ---------------------------------------------------------------------

echo "   Restarting nginx..."

systemctl restart nginx || {
    echo ""
    echo "ERROR: nginx restart failed."
    echo ""
    systemctl status nginx --no-pager
    exit 1
}

echo "   Nginx restarted successfully."


# =====================================================================
# COMPLETE
# =====================================================================

echo ""
echo "====================================================================="
echo " DEPLOYMENT COMPLETE"
echo "====================================================================="
echo ""
echo "Frontend:"
echo "  Web Root : $WEB_ROOT"
echo "  Nginx   : Port 88"
echo ""
echo "Backend:"
echo "  Host    : $BACKEND_HOST"
echo "  Port    : $BACKEND_PORT"
echo "  PID     : $BACKEND_PID"
echo "  App     : click_game.main:app"
echo "  Source  : $BACKEND_DIR/src"
echo "  Log     : $BACKEND_LOG"
echo ""
echo "Python:"
"$PYTHON" --version
echo ""
echo "====================================================================="

