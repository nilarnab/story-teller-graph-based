#!/bin/bash

echo "----------------------------------------"
echo "Prompt to Video Generator Setup Script"
echo "----------------------------------------"

Python virtual environment
echo "[1/6] Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "[2/6] Installing backend dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# uploads folder
echo "[3/6] Creating backend uploads folder..."
mkdir -p backend/uploads

echo "[4/6] Setting environment variables..."
export FLASK_ENV=development
export MONGO_URI="mongodb://localhost:27017"
export MONGO_DB_NAME="prompt_video_app"
export UPLOAD_FOLDER="uploads"

echo "Environment variables loaded."

# backend
echo "[5/6] Starting Flask backend on http://localhost:8000 ..."
python backend/app.py &
BACKEND_PID=$!

sleep 2

# frontend
echo "[6/6] Starting frontend on http://localhost:5500/index.html ..."
cd ui
python3 -m http.server 5500 &
FRONTEND_PID=$!

echo "----------------------------------------"
echo "SUCCESS! Your app is running."
echo "Frontend : http://localhost:5500/index.html"
echo "Backend  : http://localhost:8000/api/jobs"
echo "----------------------------------------"

echo "Press CTRL+C to stop all servers."

# Wait until user interrupts (Ctrl+C)
wait $BACKEND_PID $FRONTEND_PID
