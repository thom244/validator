import json
import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# Initialize Firebase
# Expects serviceAccountKey.json in the same directory or parent
CRED_PATH = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")

if not os.path.exists(CRED_PATH):
    print(f"Error: {CRED_PATH} not found.")
    print("Please place your Firebase serviceAccountKey.json in the server directory.")
    exit(1)

cred = credentials.Certificate(CRED_PATH)
firebase_admin.initialize_app(cred)

db = firestore.client()

# Load cards.json
CARDS_FILE = os.path.join(os.path.dirname(__file__), "cards.json")

if not os.path.exists(CARDS_FILE):
    print(f"Error: {CARDS_FILE} not found.")
    exit(1)

with open(CARDS_FILE, "r") as f:
    cards_data = json.load(f)

print(f"Loaded {len(cards_data)} cards from JSON. Migrating to Firestore...")

batch = db.batch()
collection_ref = db.collection("cards")

count = 0
for card_uid, card_info in cards_data.items():
    doc_ref = collection_ref.document(card_uid)
    batch.set(doc_ref, card_info)
    count += 1
    
    # Firestore batches are limited to 500 writes
    if count % 400 == 0:
        batch.commit()
        batch = db.batch()
        print(f"Committed {count} cards...")

if count % 400 != 0:
    batch.commit()

print(f"Successfully migrated {count} cards to Firestore.")
