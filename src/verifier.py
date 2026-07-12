"""
verifier.py
-----------
Asset verification logic for DeskGuard.

Compares objects detected by AssetDetector against a FIXED set of
required workspace assets and returns a structured verification
result describing which required assets are present/missing and
which detected objects are unexpected. Logs every verification run
to a CSV file for auditing.

Required workspace assets:
    - Laptop OR Monitor   (YOLO may report a monitor as "tv")
    - Keyboard
    - Mouse
    - Water Bottle        (YOLO class = "bottle")

Verification rules:
    1. Laptop OR Monitor must be present (either one satisfies this).
    2. Keyboard must be present.
    3. Mouse must be present.
    4. Water Bottle must be present.
    5. Duplicate detections of the same object are ignored (presence only).
    6. Confidence scores are ignored when verifying.
    Any detected object that isn't one of the above is "unexpected".

Owned primarily by: Harini
"""

from typing import Any, Dict, List, Set

from loguru import logger

from src import utils

# ----------------------------------------------------------------------
# Fixed requirement definitions.
# Each requirement maps a human-readable display name to the set of
# raw YOLO class labels that satisfy it.
# ----------------------------------------------------------------------
REQUIRED_ASSETS: Dict[str, Dict[str, Any]] = {
    "laptop_or_monitor": {
        "display": "Laptop/Monitor",
        "labels": {"laptop", "monitor", "tv"},  # YOLO may call a monitor "tv"
    },
    "keyboard": {
        "display": "Keyboard",
        "labels": {"keyboard"},
    },
    "mouse": {
        "display": "Mouse",
        "labels": {"mouse"},
    },
    "water_bottle": {
        "display": "Water Bottle",
        "labels": {"bottle"},  # YOLO class = "bottle"
    },
}

# Union of every raw label that counts as "expected" in some requirement.
_ALL_EXPECTED_LABELS: Set[str] = {
    label for info in REQUIRED_ASSETS.values() for label in info["labels"]
}

# Status constants
STATUS_READY = "READY"
STATUS_NOT_READY = "NOT_READY"
STATUS_READY_WITH_WARNINGS = "READY_WITH_WARNINGS"


class AssetVerifier:
    """
    Verifies detected assets against the fixed DeskGuard requirement
    set (Laptop/Monitor, Keyboard, Mouse, Water Bottle) and returns a
    structured verification result.
    """

    def verify(self, detections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare detected items against the fixed required-asset rules.

        Duplicate detections and confidence scores are ignored -
        only unique object labels matter.

        Returns a structured result dict:
            {
                "status": "READY" | "NOT_READY" | "READY_WITH_WARNINGS",
                "detected_assets": [display_name, ...],   # required assets present
                "missing_assets": [display_name, ...],    # required assets missing
                "unexpected_objects": [label, ...],        # non-required detections
            }
        """
        # Rule 5 & 6: ignore duplicates and confidence - reduce to a
        # unique, lowercase set of detected labels.
        unique_labels: Set[str] = {
            str(det.get("label", "")).strip().lower() for det in detections
        }
        unique_labels.discard("")

        detected_assets: List[str] = []
        missing_assets: List[str] = []

        for info in REQUIRED_ASSETS.values():
            if unique_labels & info["labels"]:
                detected_assets.append(info["display"])
            else:
                missing_assets.append(info["display"])

        unexpected_objects = sorted(unique_labels - _ALL_EXPECTED_LABELS)

        status = self._determine_status(missing_assets, unexpected_objects)

        result = {
            "status": status,
            "detected_assets": detected_assets,
            "missing_assets": missing_assets,
            "unexpected_objects": unexpected_objects,
        }

        self._log_result(result)
        return result

    @staticmethod
    def _determine_status(
        missing_assets: List[str], unexpected_objects: List[str]
    ) -> str:
        """Work out overall workspace status from missing/unexpected lists."""
        if missing_assets:
            # CASE 2 and CASE 4 - missing assets always mean Not Ready,
            # regardless of whether unexpected objects are also present.
            return STATUS_NOT_READY
        if unexpected_objects:
            # CASE 3 - nothing missing, but unexpected objects present.
            return STATUS_READY_WITH_WARNINGS
        # CASE 1 - everything required is present, nothing unexpected.
        return STATUS_READY

    def _log_result(self, result: Dict[str, Any]) -> None:
        """Append the verification result to the CSV audit log."""
        row = {
            "timestamp": utils.get_timestamp(),
            "status": result["status"],
            "detected_assets": ", ".join(result["detected_assets"]) or "-",
            "missing_assets": ", ".join(result["missing_assets"]) or "-",
            "unexpected_objects": ", ".join(result["unexpected_objects"]) or "-",
        }
        utils.append_verification_log(row)
        logger.info(f"Verification result: {result['status']} | {row}")