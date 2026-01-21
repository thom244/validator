import requests
import sys

BASE_URL = "http://localhost:8000/validator"
TOKEN = "test"

def scan_card(card_uid, line_name="SIMULATOR"):
    url = f"{BASE_URL}/scanCardInfo"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}"
    }
    payload = {
        "card_uid": card_uid,
        "line_name": line_name,
        "timestamp": "now"
    }
    
    try:
        print(f"Scanning card: {card_uid}...")
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print("\n--- Card Scan Result ---")
            print(f"Status:  {data.get('status')}")
            print(f"Credits: {data.get('credits')}")
            print(f"Expires: {data.get('expiration_date')}")
            print("------------------------\n")
        elif response.status_code == 404:
            print("\n[!] Card not found.")
        else:
            print(f"\n[!] Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    print("=== Validator Card Simulator ===")
    print("Type 'exit' to quit.")
    
    while True:
        uid = input("Enter Card UID to Scan: ").strip()
        if uid.lower() == "exit":
            break
        if not uid:
            continue
            
        scan_card(uid)
