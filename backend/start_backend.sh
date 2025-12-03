#!/bin/bash

# InstructMesh-PhysiOpt-Integration - Backend Startup Script
echo "Starting InstructMesh-PhysiOpt-Integration Backend..."

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "Error: app.py not found. Please run this script from the backend directory."
    exit 1
fi

# Activate trellis conda environment
eval "$(conda shell.bash hook)"
if conda env list | grep -q "^trellis "; then
    echo "Activating trellis conda environment..."
    conda activate trellis
else
    echo "Warning: trellis conda environment not found. Continuing with current environment."
fi

# Default port
PORT=8000

# Check if port is in use and find alternative
while netstat -ln 2>/dev/null | grep -q ":$PORT "; do
    echo "Port $PORT is busy, trying $((PORT + 1))..."
    PORT=$((PORT + 1))
done

echo "Starting backend server on port $PORT..."
echo "API will be available at: http://localhost:$PORT"
echo "API documentation at: http://localhost:$PORT/docs"
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
python3 app.py

