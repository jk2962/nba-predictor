#!/bin/bash
# Restart both backend and frontend servers

echo "🛑 Stopping servers..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null
sleep 1

echo "🚀 Starting backend (port 8000)..."
cd "$(dirname "$0")/backend"
source venv/bin/activate
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
sleep 2

echo "🚀 Starting frontend (port 3000)..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Servers started!"
echo "   Backend:  http://localhost:8000  (PID: $BACKEND_PID)"
echo "   Frontend: http://localhost:3000  (PID: $FRONTEND_PID)"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "To stop: lsof -ti:8000,:3000 | xargs kill -9"
