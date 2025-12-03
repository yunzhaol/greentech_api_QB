#!/usr/bin/env python3
"""
GreenTech Painting - QuickBooks API REST Server
Provides HTTP endpoints for VBA/Excel integration.
"""
import json
import pathlib
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import traceback

# Import our existing modules
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from cli_push_estimate import process_quote
from quickbooks_client import get_company_info, QuickBooksAPIError

app = Flask(__name__)
CORS(app)  # Enable CORS for VBA/Excel requests

# Configuration
API_VERSION = "1.0"
DEFAULT_PORT = 5000

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        company = get_company_info()
        return jsonify({
            "status": "healthy",
            "version": API_VERSION,
            "quickbooks_connected": True,
            "company": company.get("CompanyName", "Unknown")
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "version": API_VERSION,
            "quickbooks_connected": False,
            "error": str(e)
        }), 503

@app.route('/api/v1/estimate', methods=['POST'])
def create_estimate():
    """
    Creates a QuickBooks estimate from JSON data.
    
    Expected JSON payload:
    {
        "customer": {
            "display_name": "John Doe",
            "email": "john@example.com",
            "phone": "416-555-0100"
        },
        "quote": {
            "reference": "GT-001",
            "date": "2025-11-17"
        },
        "items": [
            {
                "description": "Interior painting",
                "qty": 2,
                "unit_price": 150.0
            }
        ],
        "sustainability": {
            "trees": 1,
            "co2_tons": 0.1,
            "water_liters": 10
        },
        "currency": "CAD",
        "mock": false  // Optional: set to true for mock mode
    }
    """
    try:
        # Get JSON data from request
        if not request.is_json:
            return jsonify({
                "ok": False,
                "error": "Request must be JSON"
            }), 400
        
        data = request.get_json()
        
        # Check for mock mode
        use_mock = data.get("mock", False)
        
        # Validate required fields
        if "customer" not in data:
            return jsonify({
                "ok": False,
                "error": "Missing 'customer' field"
            }), 400
        
        if "items" not in data or not isinstance(data["items"], list) or len(data["items"]) == 0:
            return jsonify({
                "ok": False,
                "error": "Missing or empty 'items' array"
            }), 400
        
        # Process the quote using existing logic
        # Create a temporary JSON file for processing
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json.dump(data, tmp_file, indent=2)
            tmp_path = pathlib.Path(tmp_file.name)
        
        try:
            result = process_quote(tmp_path, use_mock=use_mock)
            
            # Clean up temp file
            tmp_path.unlink()
            
            # Return result
            if result.get("ok"):
                return jsonify(result), 200
            else:
                return jsonify(result), 400
                
        except Exception as e:
            # Clean up temp file on error
            if tmp_path.exists():
                tmp_path.unlink()
            raise e
            
    except QuickBooksAPIError as e:
        return jsonify({
            "ok": False,
            "error": f"QuickBooks API Error: {e.message}",
            "status_code": e.status_code
        }), 400
    
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error processing estimate: {error_trace}")
        return jsonify({
            "ok": False,
            "error": f"Server error: {str(e)}"
        }), 500

@app.route('/api/v1/estimate/mock', methods=['POST'])
def create_mock_estimate():
    """Creates a mock estimate (no QuickBooks API call)"""
    data = request.get_json()
    if data:
        data["mock"] = True
    else:
        data = {"mock": True}
    
    return create_estimate()

@app.route('/api/v1/status', methods=['GET'])
def get_status():
    """Returns API status and QuickBooks connection info"""
    try:
        company = get_company_info()
        return jsonify({
            "ok": True,
            "api_version": API_VERSION,
            "quickbooks": {
                "connected": True,
                "company_name": company.get("CompanyName", "Unknown"),
                "company_id": company.get("Id", "Unknown")
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 200
    except Exception as e:
        return jsonify({
            "ok": False,
            "api_version": API_VERSION,
            "quickbooks": {
                "connected": False,
                "error": str(e)
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 503

@app.route('/api/v1/logs', methods=['GET'])
def get_logs():
    """Returns recent quote logs (optional: for debugging)"""
    log_path = pathlib.Path("logs/quotes_log.csv")
    
    if not log_path.exists():
        return jsonify({
            "ok": True,
            "logs": [],
            "message": "No logs found"
        }), 200
    
    try:
        import csv
        logs = []
        with log_path.open('r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            logs = list(reader)
        
        # Return last 50 entries
        recent_logs = logs[-50:] if len(logs) > 50 else logs
        
        return jsonify({
            "ok": True,
            "total": len(logs),
            "recent": len(recent_logs),
            "logs": recent_logs
        }), 200
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "ok": False,
        "error": "Endpoint not found"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "ok": False,
        "error": "Internal server error"
    }), 500

def run_server(host='0.0.0.0', port=DEFAULT_PORT, debug=False):
    """Run the Flask server"""
    print("=" * 70)
    print("GreenTech Painting - QuickBooks API Server")
    print("=" * 70)
    print(f"API Version: {API_VERSION}")
    print(f"Server starting on http://{host}:{port}")
    print()
    print("Available endpoints:")
    print(f"  GET  /health              - Health check")
    print(f"  GET  /api/v1/status       - API status")
    print(f"  POST /api/v1/estimate     - Create estimate")
    print(f"  POST /api/v1/estimate/mock - Create mock estimate")
    print(f"  GET  /api/v1/logs         - View recent logs")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 70)
    print()
    
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='GreenTech QuickBooks API Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help=f'Port to bind to (default: {DEFAULT_PORT})')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    run_server(host=args.host, port=args.port, debug=args.debug)

