#!/bin/bash

echo "🚀 Starting DocIQ Application..."

# Kill any existing processes
echo "🧹 Cleaning up existing processes..."
pkill -f uvicorn 2>/dev/null
pkill -f "npm run dev" 2>/dev/null
sleep 2

# Set up Python 3.11 path
export PATH="/opt/homebrew/bin:/opt/homebrew/opt/python@3.11/bin:$PATH"

echo "🧠 Starting Backend (FastAPI)..."
cd /Users/lukebond/dociq/backend
if [ ! -f ".env.development" ]; then
  cp .env.development.example .env.development
fi
set -a
source .env.development
set +a
nohup python3.11 -m uvicorn app:app --reload --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!

echo "🎨 Starting Frontend (React)..."
cd /Users/lukebond/dociq/frontend
nohup npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!

echo ""
echo "✅ Both servers starting..."
echo "🧠 Backend: http://localhost:8000 (PID: $BACKEND_PID)"
echo "🎨 Frontend: http://localhost:8080 (PID: $FRONTEND_PID)"
echo ""
echo "📊 Logs:"
echo "   Backend:  tail -f /Users/lukebond/dociq/backend.log"
echo "   Frontend: tail -f /Users/lukebond/dociq/frontend.log"
echo ""
echo "🛑 To stop: pkill -f uvicorn && pkill -f 'npm run dev'"
echo ""
echo "⏳ Waiting for servers to start..."
sleep 5

# Check if servers are running
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend is healthy!"
else
    echo "❌ Backend failed to start - check backend.log"
fi

if curl -s http://localhost:8080 > /dev/null; then
    echo "✅ Frontend is running!"
else
    echo "⏳ Frontend still starting..."
fi

echo ""
echo "🎯 Ready to use DocIQ!"
echo "🌐 Open: http://localhost:8080"
echo "🔑 Demo accounts available if backend auth fails"
