"""
Mock Validator Server - Flask application
Implements /validator/pingStatus and /validator/scanCardInfo routes
"""

import json
import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from functools import wraps

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

app = Flask(__name__, static_url_path='', static_folder='../web')
CORS(app)  # Enable CORS for all routes

# Initialize Firebase
# Expects serviceAccountKey.json in the same directory or parent
cred_path = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")
if os.path.exists(cred_path):
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    print("Warning: serviceAccountKey.json not found. Database operations will fail.")
    db = None


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
        doc_ref = db.collection("cards").document(card_uid_upper)
        doc = doc_ref.get()

        if doc.exists:
            card_data = doc.to_dict()
            current_status = card_data.get("status", "OK")
            current_credits = card_data.get("credits", 0)
            expiration_date = card_data.get("expiration_date", "")
            card_name = card_data.get("name", "")
            last_scan = card_data.get("last_scan", "")
            
            # Expiration Check
            if expiration_date and current_status == "VALID":
                try:
                    exp_date = datetime.strptime(expiration_date, "%Y-%m-%d").date()
                    if exp_date < datetime.now().date():
                        current_status = "EXPIRED"
                        doc_ref.update({"status": "EXPIRED"})
                        print(f"Card expired on {expiration_date}")
                except ValueError:
                    print(f"Invalid expiration date format: {expiration_date}")
            
            # 1-hour Cooldown Check
            should_deduct = True
            if last_scan and current_status == "VALID":
                try:
                    last_scan_time = datetime.fromisoformat(last_scan)
                    time_diff = datetime.now() - last_scan_time
                    if time_diff.total_seconds() < 3600:  # 1 hour = 3600 seconds
                        should_deduct = False
                        remaining_mins = int((3600 - time_diff.total_seconds()) / 60)
                        print(f"Cooldown active. {remaining_mins} minutes remaining.")
                except ValueError:
                    pass
            
            # Credit Logic (only if VALID and not in cooldown)
            if current_status == "VALID" and should_deduct:
                if current_credits > 0:
                    current_credits -= 1
                    doc_ref.update({
                        "credits": current_credits,
                        "last_scan": datetime.now().isoformat()
                    })
                    print(f"Deducted 1 credit. Remaining: {current_credits}")
                else:
                    current_status = "INVALID"
                    doc_ref.update({"status": "INVALID"})
                    print(f"Insufficient credits. Card invalidated.")
            
            response = {
                "status": current_status,
                "credits": current_credits,
                "expiration_date": card_data.get("expiration_date"),
                "name": card_name,
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



@app.route("/validator/cards/<card_uid>/status", methods=["POST"])
@require_bearer_token
def update_card_status(card_uid):
    """
    Update card status endpoint
    
    Expected request body:
    {
        "status": "VALID" | "INVALID" | "EXPIRED"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing request body"}), 400
            
        new_status = data.get("status")
        if not new_status:
            return jsonify({"error": "Missing status"}), 400
            
        card_uid_upper = card_uid.upper()
        doc_ref = db.collection("cards").document(card_uid_upper)
        doc = doc_ref.get()
        
        if not doc.exists:
            return jsonify({"error": "Card not found"}), 404
        
        # Check if trying to validate an expired card
        if new_status == "VALID":
            card_data = doc.to_dict()
            expiration_date = card_data.get("expiration_date", "")
            if expiration_date:
                try:
                    exp_date = datetime.strptime(expiration_date, "%Y-%m-%d").date()
                    if exp_date < datetime.now().date():
                        return jsonify({"error": "Cannot validate expired card. Update expiration date first."}), 400
                except ValueError:
                    pass
            
        doc_ref.update({"status": new_status})
        
        print(f"Updated card {card_uid_upper} status to {new_status}")
        return jsonify({"status": "OK", "new_status": new_status}), 200
        
    except Exception as e:
        print(f"Error in update_card_status: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/validator/cards/<card_uid>/expiration", methods=["POST"])
def update_card_expiration(card_uid):
    """
    Update card expiration date endpoint
    
    Expected request body:
    {
        "expiration_date": "2027-12-31"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing request body"}), 400
            
        expiration_date = data.get("expiration_date")
        if not expiration_date:
            return jsonify({"error": "Missing expiration_date"}), 400
            
        card_uid_upper = card_uid.upper()
        doc_ref = db.collection("cards").document(card_uid_upper)
        
        if not doc_ref.get().exists:
            return jsonify({"error": "Card not found"}), 404
            
        doc_ref.update({"expiration_date": expiration_date})
        
        print(f"Updated card {card_uid_upper} expiration to {expiration_date}")
        return jsonify({"status": "OK", "expiration_date": expiration_date}), 200
        
    except Exception as e:
        print(f"Error in update_card_expiration: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/validator/cards/<card_uid>/name", methods=["POST"])
def update_card_name(card_uid):
    """
    Update card name endpoint
    
    Expected request body:
    {
        "name": "John Doe"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing request body"}), 400
            
        name = data.get("name", "")
            
        card_uid_upper = card_uid.upper()
        doc_ref = db.collection("cards").document(card_uid_upper)
        
        if not doc_ref.get().exists:
            return jsonify({"error": "Card not found"}), 404
            
        doc_ref.update({"name": name})
        
        print(f"Updated card {card_uid_upper} name to {name}")
        return jsonify({"status": "OK", "name": name}), 200
        
    except Exception as e:
        print(f"Error in update_card_name: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/validator/cards", methods=["GET"])
def get_all_cards():
    """List all cards endpoint"""
    try:
        cards_ref = db.collection("cards")
        docs = cards_ref.stream()
        
        cards_list = []
        for doc in docs:
            card = doc.to_dict()
            card["uid"] = doc.id
            cards_list.append(card)
            
        return jsonify({"cards": cards_list}), 200
    except Exception as e:
        print(f"Error in get_all_cards: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/validator/cards/<card_uid>/topup", methods=["POST"])
def top_up_card(card_uid):
    """
    Top up card credits endpoint
    
    Expected request body:
    {
        "amount": 10
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing request body"}), 400
            
        amount = data.get("amount")
        if not isinstance(amount, int) or amount <= 0:
            return jsonify({"error": "Invalid amount"}), 400
            
        card_uid_upper = card_uid.upper()
        doc_ref = db.collection("cards").document(card_uid_upper)
        doc = doc_ref.get()
        
        if not doc.exists:
            return jsonify({"error": "Card not found"}), 404
            
        # Transaction could be better here, but keep it simple for now
        current_credits = doc.to_dict().get("credits", 0)
        new_credits = current_credits + amount
        
        # Also re-validate if it was invalid due to 0 credits? 
        # For now just update credits.
        doc_ref.update({"credits": new_credits})
        
        # Optional: Auto-validate if credits added?
        # Let's say yes, if it was INVALID (assuming due to credits), make it VALID.
        if doc.to_dict().get("status") == "INVALID":
             doc_ref.update({"status": "VALID"})
             print(f"Auto-validated card {card_uid_upper} after topup")

        print(f"Added {amount} credits to {card_uid_upper}. New balance: {new_credits}")
        return jsonify({"status": "OK", "new_credits": new_credits}), 200
        
    except Exception as e:
        print(f"Error in top_up_card: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/validator/cards", methods=["POST"])
def create_card():
    """
    Create a new card endpoint
    
    Expected request body:
    {
        "uid": "ABC12345",
        "credits": 100,
        "expiration_date": "2027-12-31"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing request body"}), 400
            
        uid = data.get("uid")
        if not uid:
            return jsonify({"error": "Missing uid"}), 400
            
        uid_upper = uid.upper()
        credits = data.get("credits", 0)
        expiration_date = data.get("expiration_date", "")
        name = data.get("name", "")
        
        # Validation
        if credits < 0:
            return jsonify({"error": "Credits cannot be negative"}), 400
        
        if expiration_date:
            try:
                exp_date = datetime.strptime(expiration_date, "%Y-%m-%d").date()
                if exp_date < datetime.now().date():
                    return jsonify({"error": "Expiration date cannot be in the past"}), 400
            except ValueError:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
        
        # Check if card already exists
        doc_ref = db.collection("cards").document(uid_upper)
        if doc_ref.get().exists:
            return jsonify({"error": "Card already exists"}), 409
        
        # Create the card
        doc_ref.set({
            "status": "VALID",
            "credits": credits,
            "expiration_date": expiration_date,
            "name": name
        })
        
        print(f"Created new card: {uid_upper}")
        return jsonify({"status": "OK", "uid": uid_upper}), 201
        
    except Exception as e:
        print(f"Error in create_card: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/validator/cards/<card_uid>", methods=["DELETE"])
def delete_card(card_uid):
    """Delete a card endpoint"""
    try:
        card_uid_upper = card_uid.upper()
        doc_ref = db.collection("cards").document(card_uid_upper)
        
        if not doc_ref.get().exists:
            return jsonify({"error": "Card not found"}), 404
            
        doc_ref.delete()
        
        print(f"Deleted card: {card_uid_upper}")
        return jsonify({"status": "OK"}), 200
        
    except Exception as e:
        print(f"Error in delete_card: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "OK"}), 200


@app.route("/")
def index():
    return app.send_static_file("index.html")

if __name__ == "__main__":
    print("Starting Mock Validator Server on http://localhost:8000")
    if db:
        print("Connected to Firestore")
    app.run(host="0.0.0.0", port=8000, debug=True)
