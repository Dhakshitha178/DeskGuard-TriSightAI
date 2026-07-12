"""
config.py
---------
Centralized configuration for the DeskGuard system.
Holds paths, model settings, and runtime constants used
across detector.py, verifier.py, gui.py, and app.py.
"""

import os
from pathlib import Path

# ----------------------------
# Base Project Paths
# ----------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

ASSETS_DIR = BASE_DIR / "assets"
DOCS_DIR = BASE_DIR / "docs"
OUTPUT_DIR = BASE_DIR / "output"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"

# ----------------------------
# Model Configuration
# ----------------------------
MODEL_NAME = "yolov8n.pt"          # placeholder, update once model is finalized
MODEL_PATH = ASSETS_DIR / "models" / MODEL_NAME
CONFIDENCE_THRESHOLD = 0.30
IOU_THRESHOLD = 0.45

# ----------------------------
# Camera / Input Configuration
# ----------------------------
CAMERA_INDEX = 0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# ----------------------------
# Asset Verification Settings
# ----------------------------
REGISTERED_ASSETS_FILE = OUTPUT_DIR / "registered_assets.json"
VERIFICATION_LOG_FILE = OUTPUT_DIR / "verification_log.csv"

# ----------------------------
# Application Settings
# ----------------------------
APP_NAME = "DeskGuard"
APP_VERSION = "0.1.0"
DEBUG_MODE = os.getenv("DESKGUARD_DEBUG", "False") == "True"