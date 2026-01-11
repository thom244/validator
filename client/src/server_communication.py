"""
Server Communication Module - Handles all communication with the validator server
Manages card validation requests and periodic server health checks
"""

import threading
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any
import time

logger = logging.getLogger(__name__)


class ServerCommunication:
    """
    Handles asynchronous communication with the validator server
    Manages ping health checks and card validation requests
    """

    def __init__(
        self,
        api_url: str,
        api_token: str,
        line_name: str,
        status: Dict[str, Any],
        ping_interval: int = 10,
    ):
        """
        Initialize Server Communication

        Args:
            api_url: Base URL of the validator server (e.g., 'http://localhost:8000')
            api_token: API token for authentication
            line_name: Name of the production line
            status: Shared status dictionary with 'connected' and 'ready' keys
            ping_interval: Seconds between ping requests (default: 10)
        """
        self.api_url = api_url.rstrip("/")
        self.api_token = api_token
        self.line_name = line_name
        self.status = status
        self.ping_interval = ping_interval

        self.running = False
        self.ping_thread: Optional[threading.Thread] = None
        self.consecutive_pings = (
            0  # Track consecutive successful pings for 'ready' status
        )

    def start(self):
        """Start the server communication thread"""
        if not self.running:
            self.running = True
            self.ping_thread = threading.Thread(target=self._ping_loop, daemon=True)
            self.ping_thread.start()
            logger.info("Server communication thread started")

    def stop(self):
        """Stop the server communication thread"""
        self.running = False
        if self.ping_thread:
            self.ping_thread.join(timeout=2)
        logger.info("Server communication stopped")

    def _ping_loop(self):
        """Main ping loop - runs in separate thread"""
        while self.running:
            try:
                success = self._ping_server()
                if success:
                    self.consecutive_pings += 1
                    self.status["connected"] = True
                    self.status["ready"] = True
                else:
                    self.consecutive_pings = 0
                    self.status["connected"] = False
                    self.status["ready"] = False

            except Exception as e:
                logger.error(f"Error in ping loop: {e}")
                self.consecutive_pings = 0
                self.status["connected"] = False
                self.status["ready"] = False

            time.sleep(self.ping_interval)

    def _ping_server(self) -> bool:
        """
        Send ping request to server to check connection status

        Returns:
            True if ping successful, False otherwise
        """
        try:
            endpoint = f"{self.api_url}/validator/pingStatus"
            payload = {
                "line_name": self.line_name,
                "timestamp": datetime.now().isoformat(),
            }
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            }

            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=5,
            )

            if response.status_code == 200:
                logger.debug(f"Ping successful: {response.status_code}")
                return True
            else:
                logger.warning(f"Ping failed with status code: {response.status_code}")
                return False

        except requests.exceptions.Timeout:
            logger.warning("Ping timeout")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error during ping: {e}")
            return False
        except Exception as e:
            logger.error(f"Error during ping: {e}")
            return False

    def validate_card(self, card_uid: str) -> Dict[str, Any]:
        """
        Send card UID to server for validation

        Args:
            card_uid: The card UID as a hex string

        Returns:
            Dictionary with server response data:
            {
                'success': bool,
                'status': str,  # 'OK', 'EXPIRED', 'INVALID', etc.
                'credits': int,  # Credits remaining
                'expiration_date': str,  # ISO format
                'error': str,  # Error message if any
            }
        """
        try:
            endpoint = f"{self.api_url}/validator/scanCardInfo"
            payload = {
                "card_uid": card_uid,
                "line_name": self.line_name,
                "timestamp": datetime.now().isoformat(),
            }
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            }

            logger.info(f"Validating card UID with server: {card_uid}")

            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=5,
            )

            if response.status_code == 200:
                data = response.json()
                logger.info(f"Card validation successful: {card_uid}")
                return {
                    "success": True,
                    "status": data.get("status", "OK"),
                    "credits": data.get("credits", 0),
                    "expiration_date": data.get("expiration_date", None),
                    "error": None,
                }
            elif response.status_code == 404:
                logger.info(f"Card not found: {card_uid}")
                return {
                    "success": False,
                    "status": "UNKNOWN",
                    "credits": 0,
                    "expiration_date": None,
                    "error": "Card not found",
                }
            else:
                logger.warning(
                    f"Card validation failed with status {response.status_code}: {card_uid}"
                )
                return {
                    "success": False,
                    "status": "ERROR",
                    "credits": 0,
                    "expiration_date": None,
                    "error": f"Server returned status {response.status_code}",
                }

        except requests.exceptions.Timeout:
            logger.error(f"Card validation timeout: {card_uid}")
            return {
                "success": False,
                "status": "ERROR",
                "credits": 0,
                "expiration_date": None,
                "error": "Request timeout",
            }
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error validating card: {e}")
            return {
                "success": False,
                "status": "ERROR",
                "credits": 0,
                "expiration_date": None,
                "error": "Connection error",
            }
        except Exception as e:
            logger.error(f"Error validating card {card_uid}: {e}")
            return {
                "success": False,
                "status": "ERROR",
                "credits": 0,
                "expiration_date": None,
                "error": str(e),
            }

    def is_connected(self) -> bool:
        """
        Get current connection status

        Returns:
            True if connected to server, False otherwise
        """
        return self.status.get("connected", False)

    def is_ready(self) -> bool:
        """
        Get current ready status

        Returns:
            True if server is stable (2+ consecutive pings), False otherwise
        """
        return self.status.get("ready", False)
