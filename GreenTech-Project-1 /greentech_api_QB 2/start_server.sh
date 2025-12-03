#!/bin/bash
# GreenTech Painting - QuickBooks API Server (Mac/Linux)
# Starts the API server for VBA integration

echo "Starting GreenTech QuickBooks API Server..."
echo ""

cd "$(dirname "$0")"
python3 start_server.py


