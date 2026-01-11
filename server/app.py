"""
Mock Validator Server - Flask application
Implements /validator/pingStatus and /validator/scanCardInfo routes
"""

import json
import os
from datetime import datetime
from flask import Flask, request, jsonify
from functools import wraps

app = Flask(__name__)

# Load cards database
CARDS_FILE = os.path.join(os.path.dirname(__file__), "cards.json")

with open(CARDS_FILE, "r") as f:
    CARDS_DB = json.load(f)


def require_bearer_token(f):
    """Decorator to validate Bearer token"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Missing Authorization header"}), 401
        
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                return jsonify({"error": "Invalid Authorization scheme"}), 401
        except ValueError:
            return jsonify({"error": "Invalid Authorization header"}), 401

        # For mock server, accept any token
        return f(*args, **kwargs)

    return decorated_function


@app.route("/validator/pingStatus", methods=["POST"])
@require_bearer_token
def ping_status():
    """
    Ping endpoint to check server connection status
    
    Expected request body:
    {
        "line_name": "N1",
        "timestamp": "2026-01-11T10:30:00.123456"
    }
    
    Returns:
    {
        "status": "OK",
        "timestamp": "2026-01-11T10:30:00.123456"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Missing request body"}), 400
        
        line_name = data.get("line_name")
        timestamp = data.get("timestamp")
        
        if not line_name:
            return jsonify({"error": "Missing line_name"}), 400
        
        # Log the ping
        print(f"[{timestamp}] Ping from line: {line_name}")
        
        return jsonify({
            "status": "OK",
            "timestamp": datetime.now().isoformat(),
            "server_time": datetime.now().isoformat(),
        }), 200
    
    except Exception as e:
        print(f"Error in ping_status: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/validator/scanCardInfo", methods=["POST"])
@require_bearer_token
def scan_card_info():
    """
    Card validation endpoint
    
    Expected request body:
    {
        "card_uid": "12345678",
        "line_name": "N1",
        "timestamp": "2026-01-11T10:30:00.123456"
    }
    
    Returns:
    {
        "status": "OK",
        "credits": 50,
        "expiration_date": "2026-12-31"
    }
    
    or if card not found:
    {
        "error": "Card not found",
        "status": "INVALID"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Missing request body"}), 400
        
        card_uid = data.get("card_uid")
        line_name = data.get("line_name")
        timestamp = data.get("timestamp")
        
        if not card_uid:
            return jsonify({"error": "Missing card_uid"}), 400
        
        # Convert to uppercase for lookup
        card_uid_upper = card_uid.upper()
        
        # Log the scan
        print(f"[{timestamp}] Card scan on line {line_name}: {card_uid_upper}")
        
        # Look up card in database
        if card_uid_upper in CARDS_DB:
            card_data = CARDS_DB[card_uid_upper]
            response = {
                "status": card_data.get("status", "OK"),
                "credits": card_data.get("credits", 0),
                "expiration_date": card_data.get("expiration_date"),
            }
            print(f"Card found: {card_uid_upper} - {response}")
            return jsonify(response), 200
        else:
            # Card not found
            print(f"Card not found: {card_uid_upper}")
            return jsonify({
                "error": "Card not found",
                "status": "INVALID",
                "credits": 0,
                "expiration_date": None,
            }), 404
    
    except Exception as e:
        print(f"Error in scan_card_info: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "OK"}), 200


if __name__ == "__main__":
    print("Starting Mock Validator Server on http://localhost:8000")
    print(f"Loaded {len(CARDS_DB)} cards from {CARDS_FILE}")
    app.run(host="0.0.0.0", port=8000, debug=True)
