import os
import logging
from gui import ValidatorAppGui
from nfc_reader import NFCReader
from server_communication import ServerCommunication

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("validator.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

config = {
    "screen_width": 320,
    "screen_height": 480,
    "fps": 10,
    "text_color": (255, 255, 255),
    "background_color": (0, 0, 0),
    "operator_name": "RATT",
    "line_name": os.getenv("VALIDATOR_LINE_NAME", "T1"),
    "api_url": os.getenv("VALIDATOR_API_URL", "http://localhost:8000"),
    "api_token": os.getenv("VALIDATOR_API_TOKEN", "$$$$.DEFAULT.0000"),
    "nfc_port": os.getenv("VALIDATOR_NFC_PORT", "com:4:pn532"),
}

lang_strings = {
    "loading": "Please wait...",
    "contact_server": "Contacting server...",
    "no_connection": "No connection to server.",
    "error": "An error has occurred.",
    "line_label": "Line",
    "scan_card": "Scan your card",
    "scan_card_again": "Try again",
    "validating": "Validating card...",
    "have_a_nice_day": "Have a good trip!",
    "invalid_card": "Invalid card",
    "expired_card": "Expired card",
    "insufficient_credits": "Insufficient credits",
}

status = {
    "connected": False,
    "ready": False,
    "last_card_uid": None,
    "last_validation": None,
    "card_status": "",
    "card_active": False,
}


def on_card_detected(card_uid: str):
    """Callback when a card is detected by NFC reader"""
    logger.info(f"Card detected in main: {card_uid}")
    status["last_card_uid"] = card_uid
    status["card_active"] = True
    status["card_status"] = "LOADING"
    # Validate card with server
    result = server_comm.validate_card(card_uid)
    status["last_validation"] = result
    status["card_status"] = result.get("status", "UNKNOWN")
    logger.info(f"Card validation result: {result}")


def on_card_removed():
    """Callback when a card is removed"""
    logger.info("Card removed")
    status["card_active"] = False
    status["card_status"] = ""


# Initialize components
logger.info("Initializing Validator Application")

# Initialize server communication (starts background ping thread)
server_comm = ServerCommunication(
    api_url=config["api_url"],
    api_token=config["api_token"],
    line_name=config["line_name"],
    status=status,
    ping_interval=10,
)
server_comm.start()
logger.info("Server communication started")

# Initialize NFC reader with callback
nfc_reader = NFCReader(
    port=config["nfc_port"],
    card_callback=on_card_detected,
    card_removed_callback=on_card_removed,
)
nfc_reader.start()
logger.info("NFC reader started")

# Initialize and run GUI (blocks until app closes)
try:
    app_gui = ValidatorAppGui(config, lang_strings, status)
    app_gui.run()
finally:
    # Cleanup on exit
    logger.info("Shutting down components")
    nfc_reader.stop()
    server_comm.stop()
    logger.info("Application closed")
