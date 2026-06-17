#!/bin/bash
# G4 AI Impact Agent — start server + cloudflare tunnel

set -e

# Kill previous instances
lsof -ti:8080 | xargs kill -9 2>/dev/null || true
pkill -f cloudflared 2>/dev/null || true

# Start server (python-dotenv loads .env automatically)
echo "Starting server..."
python3 -m dotenv run -- python3 -m uvicorn main:app --port 8080 > /tmp/g4-agent.log 2>&1 &
SERVER_PID=$!

for i in $(seq 1 10); do
  curl -s http://localhost:8080/health > /dev/null 2>&1 && break
  sleep 1
done
echo "Server ready (PID $SERVER_PID)"

# Start cloudflare tunnel
cloudflared tunnel --url http://localhost:8080 > /tmp/cf.log 2>&1 &
CF_PID=$!
sleep 6

PUBLIC_URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/cf.log | head -1)

echo ""
echo "============================================"
echo "  G4 AI Impact Agent is LIVE"
echo "============================================"
echo "  Local:     http://localhost:8080"
echo "  Public:    $PUBLIC_URL"
echo "  Dashboard: http://localhost:8080"
echo ""
echo "  GitHub Webhook URL:"
echo "  $PUBLIC_URL/webhook/github"
echo "============================================"
echo ""
echo "Press Ctrl+C to stop."

trap "kill $SERVER_PID $CF_PID 2>/dev/null; echo 'Stopped.'; exit" INT TERM
tail -f /tmp/g4-agent.log
