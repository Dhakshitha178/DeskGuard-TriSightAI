"""
utils.py
--------
Shared helper functions used across the DeskGuard system:
- Logging setup
- JSON read/write helpers
- CSV logging for verification events
- Image annotation helpers
- Timestamp utilities

Owned primarily by: Harini (with contributions from all members)
"""
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cv2
from loguru import logger

from src import config


# ----------------------------
# Logging
# ----------------------------
def setup_logger() -> None:
    """
    Configure loguru to write to both console and a rotating log file
    inside the output/ directory. Call this once at application startup.
    """
    log_file = config.OUTPUT_DIR / "deskguard.log"
    logger.remove()  # remove default handler to avoid duplicate console logs
    logger.add(
        log_file,
        rotation="5 MB",
        retention="10 days",
        level="DEBUG" if config.DEBUG_MODE else "INFO",
    )
    logger.add(
        lambda msg: print(msg, end=""),
        level="DEBUG" if config.DEBUG_MODE else "INFO",
    )


def get_timestamp() -> str:
    """Return current timestamp as a formatted string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ----------------------------
# JSON helpers
# ----------------------------
def load_json(file_path: Path, default: Any = None) -> Any:
    """
    Load JSON data from a file. Returns `default` if the file
    does not exist or cannot be parsed.
    """
    if not file_path.exists():
        return default if default is not None else {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Failed to load JSON from {file_path}: {e}")
        return default if default is not None else {}


def save_json(file_path: Path, data: Any) -> None:
    """Save data as JSON to the given file path, creating parent dirs if needed."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# ----------------------------
# CSV logging (verification events)
# ----------------------------
def append_verification_log(row: Dict[str, Any]) -> None:
    """
    Append a single verification result row to the CSV log defined
    in config.VERIFICATION_LOG_FILE. Creates the file with headers
    if it does not already exist.
    """
    log_file = config.VERIFICATION_LOG_FILE
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_exists = log_file.exists()

    with open(log_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


# ----------------------------
# Image annotation helpers
# ----------------------------
def draw_detections(frame, detections: List[Dict[str, Any]]):
    """
    Draw bounding boxes and labels on a frame for the given detections.

    Each detection dict is expected to have:
        {"label": str, "confidence": float, "bbox": (x1, y1, x2, y2)}
    """
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        label = det["label"]
        conf = det["confidence"]

        color = (0, 200, 0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        text = f"{label} {conf:.2f}"
        cv2.putText(
            frame, text, (x1, max(y1 - 10, 0)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2,
        )
    return frame


def save_screenshot(frame, prefix: str = "capture") -> Path:
    """Save the given frame to the screenshots/ directory with a timestamped name."""
    filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    config.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = config.SCREENSHOTS_DIR / filename
    cv2.imwrite(str(filepath), frame)
    logger.info(f"Screenshot saved: {filepath}")
    return filepath
