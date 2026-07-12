"""
verifier.py
-----------
Asset verification logic for DeskGuard.

Compares objects detected by AssetDetector against a registered
list of expected workspace assets, and reports missing / unexpected
items. Logs every verification run to a CSV file for auditing.

Owned primarily by: Harini
"""

from collections import Counter
from typing import Any, Dict, List

from loguru import logger

from src import config, utils


class AssetVerifier:
    """
    Verifies detected assets against a registered asset list stored
    in config.REGISTERED_ASSETS_FILE.

    Registered assets file format (JSON):
        {
            "laptop": 1,
            "monitor": 2,
            "keyboard": 1,
            "mouse": 1
        }
    """

    def __init__(self, registered_assets_file=config.REGISTERED_ASSETS_FILE) -> None:
        self.registered_assets_file = registered_assets_file
        self.registered_assets: Dict[str, int] = {}
        self.load_registered_assets()

    def load_registered_assets(self) -> None:
        """Load the registered asset list from disk."""
        self.registered_assets = utils.load_json(self.registered_assets_file, default={})
        logger.info(f"Loaded {len(self.registered_assets)} registered asset types.")

    def save_registered_assets(self) -> None:
        """Persist the current registered asset list to disk."""
        utils.save_json(self.registered_assets_file, self.registered_assets)
        logger.info("Registered asset list saved.")

    def register_asset(self, label: str, quantity: int = 1) -> None:
        """Add or update an expected asset and its expected quantity."""
        self.registered_assets[label] = quantity
        self.save_registered_assets()

    def remove_asset(self, label: str) -> None:
        """Remove an asset from the registered list."""
        if label in self.registered_assets:
            del self.registered_assets[label]
            self.save_registered_assets()

    def verify(self, detections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare detected items against the registered asset list.

        Returns a summary dict:
            {
                "missing": {label: expected_count, ...},
                "unexpected": {label: detected_count, ...},
                "matched": {label: count, ...},
                "status": "PASS" | "FAIL"
            }
        """
        detected_counts = Counter(det["label"] for det in detections)
        registered = self.registered_assets

        missing: Dict[str, int] = {}
        matched: Dict[str, int] = {}

        for label, expected_qty in registered.items():
            detected_qty = detected_counts.get(label, 0)
            if detected_qty < expected_qty:
                missing[label] = expected_qty - detected_qty
            else:
                matched[label] = expected_qty

        unexpected: Dict[str, int] = {
            label: count
            for label, count in detected_counts.items()
            if label not in registered
        }

        status = "PASS" if not missing else "FAIL"

        summary = {
            "missing": missing,
            "unexpected": unexpected,
            "matched": matched,
            "status": status,
        }

        self._log_result(summary)
        return summary

    def _log_result(self, summary: Dict[str, Any]) -> None:
        """Append the verification result to the CSV audit log."""
        row = {
            "timestamp": utils.get_timestamp(),
            "status": summary["status"],
            "missing": ", ".join(summary["missing"].keys()) or "-",
            "unexpected": ", ".join(summary["unexpected"].keys()) or "-",
        }
        utils.append_verification_log(row)
        logger.info(f"Verification result: {summary['status']} | {row}")