#!/bin/bash

# InstructMesh-PhysiOpt-Integration - Frontend Startup Script
echo "Starting InstructMesh-PhysiOpt-Integration Frontend..."

# Check if we're in the right directory
if [ ! -f "index.html" ]; then
    echo "Error: index.html not found. Please run this script from the frontend directory."
    exit 1
fi

# Default port
PORT=8080

# Check if port is in use and find alternative
while netstat -ln 2>/dev/null | grep -q ":$PORT "; do
    echo "Port $PORT is busy, trying $((PORT + 1))..."
    PORT=$((PORT + 1))
done

echo "Starting HTTP server on port $PORT..."
echo "Open your browser and go to: http://localhost:$PORT"
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
python3 -m http.server $PORT

