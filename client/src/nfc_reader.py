"""
NFC Reader Module - Communicates with NFC readers (PN532, etc)
Reads UID from Mifare Classic cards and passes them to the server communication module
Uses nfcpy library for NFC communication
"""

import threading
import logging
from typing import Optional, Callable

try:
    import nfc
    import nfc.clf
except ImportError:
    nfc = None

logger = logging.getLogger(__name__)


class NFCReader:
    """
    Handles PN532 NFC scanner communication over UART
    Reads Mifare Classic card UIDs asynchronously
    """

    def __init__(
        self,
        port: str = "usb",
        card_callback: Optional[Callable[[str], None]] = None,
        card_removed_callback: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize NFC Reader

        Args:
            port: NFC device port ('usb' for auto-detect, or specific device path)
            card_callback: Callback function to call when a card is detected
            card_removed_callback: Callback function to call when a card is removed
        """
        self.port = port
        self.card_callback = card_callback
        self.card_removed_callback = card_removed_callback

        self.clf = None
        self.running = False
        self.reader_thread: Optional[threading.Thread] = None
        self.current_uid: Optional[str] = None

    def connect(self) -> bool:
        """
        Establish connection to NFC device using nfcpy

        Returns:
            True if connection successful, False otherwise
        """
        if not nfc:
            logger.error("nfcpy library not installed. Install with: pip install nfcpy")
            return False

        try:
            # Open connection to NFC device
            # Port can be 'usb' for auto-detect, or specific device path
            self.clf = nfc.ContactlessFrontend(self.port)
            logger.info(f"Connected to NFC reader on {self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to NFC reader: {e}")
            return False

    def disconnect(self):
        """Disconnect from NFC device"""
        if self.clf:
            self.clf.close()
            self.clf = None
            logger.info("Disconnected from NFC reader")

    def start(self):
        """Start the NFC reader thread"""
        if not self.running:
            self.running = True
            self.reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
            self.reader_thread.start()
            logger.info("NFC reader thread started")

    def stop(self):
        """Stop the NFC reader thread"""
        self.running = False
        if self.reader_thread:
            self.reader_thread.join(timeout=2)
        self.disconnect()
        logger.info("NFC reader stopped")

    def _reader_loop(self):
        """Main reader loop - runs in separate thread"""
        if not self.connect():
            return

        while self.running:
            try:
                # Use sense() to wait for a card with a timeout
                # sense() detects NFC targets (cards, devices, etc.)
                target = self.clf.sense(nfc.clf.RemoteTarget("106A"), timeout=1.0)

                if target is not None:
                    uid = self._extract_uid(target)
                    if uid and uid != self.current_uid:
                        # New card detected
                        self.current_uid = uid
                        if self.card_callback:
                            self.card_callback(uid)
                        logger.info(f"Card detected: {uid}")
                else:
                    # No card detected
                    if self.current_uid is not None:
                        # Card was removed
                        logger.info(f"Card removed: {self.current_uid}")
                        if self.card_removed_callback:
                            self.card_removed_callback()
                        self.current_uid = None
            except Exception as e:
                logger.error(f"Error reading from NFC reader: {e}")

    def _extract_uid(self, target) -> Optional[str]:
        """
        Extract card UID from nfcpy target object

        Args:
            target: nfcpy RemoteTarget object from card detection

        Returns:
            Card UID as hex string, or None if extraction failed
        """
        try:
            # nfcpy provides the UID via the target's attributes
            # For Type 2 (Mifare Classic), use identifier; for Type 3 use idm

            # Try to get UID from various attributes
            return target.sdd_res.hex().upper()

        except Exception as e:
            logger.error(f"Error extracting card UID: {e}")
            return None

    def is_connected(self) -> bool:
        """
        Check if reader is connected and running

        Returns:
            True if connected and running, False otherwise
        """
        return self.running and self.clf is not None
