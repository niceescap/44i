#!/bin/bash
# Redémarrage du service 44 interprètes
# Usage: sudo ./restart.sh

cd "$(dirname "$0")" || exit 1

echo "🔄 Arrêt de l'ancien processus uvicorn..."
pkill -f "uvicorn.*backend.app:app.*3252" 2>/dev/null
sleep 1

echo "🚀 Démarrage du nouveau service..."
sudo nohup /usr/local/bin/python3.12 /usr/local/bin/uvicorn backend.app:app --host 0.0.0.0 --port 3252 > /tmp/44i.log 2>&1 &

sleep 2

if curl -sf http://localhost:3252/health > /dev/null 2>&1; then
    echo "✅ Service 44i redémarré sur http://localhost:3252"
else
    echo "⚠️  Problème — consulte /tmp/44i.log"
fi