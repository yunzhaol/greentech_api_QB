#!/usr/bin/env python3
"""
GreenTech Painting - QuickBooks API Server Startup Script
Simple script to start the API server.
"""
import sys
import pathlib

# Add current directory to path
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from api_server import run_server

if __name__ == '__main__':
    # Default configuration
    HOST = '0.0.0.0'  # Listen on all interfaces
    PORT = 5000        # Default port
    
    # You can override with environment variables
    import os
    port = int(os.getenv('API_PORT', PORT))
    host = os.getenv('API_HOST', HOST)
    
    run_server(host=host, port=port, debug=False)


