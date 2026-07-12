"""
gui.py
------
PyQt5 desktop interface for DeskGuard.

Displays the live camera feed with detection overlays, a status
panel showing verification results, and controls to start/stop
monitoring and capture screenshots.

Owned primarily by: Sadurthiya
"""

from typing import Optional

import cv2
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from loguru import logger

from src import config, utils
from src.detector import AssetDetector
from src.verifier import AssetVerifier, REQUIRED_ASSETS


class MainWindow(QMainWindow):
    """Main application window for DeskGuard."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{config.APP_NAME} - TriSight AI")
        self.resize(1000, 650)

        self.detector = AssetDetector()
        self.verifier = AssetVerifier()
        self.capture: Optional[cv2.VideoCapture] = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        self._build_ui()

    # ----------------------------
    # UI construction
    # ----------------------------
    def _build_ui(self) -> None:
        central_widget = QWidget()
        main_layout = QHBoxLayout()

        # Video feed panel
        self.video_label = QLabel("Camera feed not started")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("background-color: #111; color: #eee;")

        # Control + status panel
        side_panel = QVBoxLayout()

        self.start_btn = QPushButton("Start Monitoring")
        self.start_btn.clicked.connect(self.start_monitoring)

        self.stop_btn = QPushButton("Stop Monitoring")
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.stop_btn.setEnabled(False)

        self.screenshot_btn = QPushButton("Save Screenshot")
        self.screenshot_btn.clicked.connect(self.save_screenshot)
        self.screenshot_btn.setEnabled(False)

        self.status_box = QTextEdit()
        self.status_box.setReadOnly(True)
        self.status_box.setPlaceholderText("Verification results will appear here...")

        side_panel.addWidget(self.start_btn)
        side_panel.addWidget(self.stop_btn)
        side_panel.addWidget(self.screenshot_btn)
        side_panel.addWidget(QLabel("Verification Status:"))
        side_panel.addWidget(self.status_box)

        main_layout.addWidget(self.video_label, stretch=3)
        main_layout.addLayout(side_panel, stretch=1)

        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self._current_frame = None

    # ----------------------------
    # Monitoring control
    # ----------------------------
    def start_monitoring(self) -> None:
        try:
            self.detector.load_model()
        except Exception as e:
            self.status_box.append(f"[ERROR] Could not load model: {e}")
            return

        self.capture = cv2.VideoCapture(config.CAMERA_INDEX)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

        if not self.capture.isOpened():
            self.status_box.append("[ERROR] Could not open camera.")
            return

        self.timer.start(30)  # ~33 FPS UI refresh
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.screenshot_btn.setEnabled(True)
        self.status_box.append("Monitoring started.")
        logger.info("Monitoring started via GUI.")

    def stop_monitoring(self) -> None:
        self.timer.stop()
        if self.capture is not None:
            self.capture.release()
            self.capture = None

        self.video_label.setText("Camera feed stopped")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.screenshot_btn.setEnabled(False)
        self.status_box.append("Monitoring stopped.")
        logger.info("Monitoring stopped via GUI.")

    def save_screenshot(self) -> None:
        if self._current_frame is not None:
            path = utils.save_screenshot(self._current_frame, prefix="deskguard")
            self.status_box.append(f"Screenshot saved: {path.name}")

    # ----------------------------
    # Frame update loop
    # ----------------------------
    def update_frame(self) -> None:
        if self.capture is None:
            return

        ret, frame = self.capture.read()
        if not ret:
            self.status_box.append("[WARNING] Failed to read frame.")
            return

        detections = self.detector.detect(frame)
        frame = utils.draw_detections(frame, detections)
        self._current_frame = frame

        summary = self.verifier.verify(detections)
        self._display_status(summary, detections)
        self._display_frame(frame)

    def _display_frame(self, frame) -> None:
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        qt_image = QImage(rgb_image.data, w, h, ch * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image).scaled(
            self.video_label.width(), self.video_label.height(), Qt.KeepAspectRatio
        )
        self.video_label.setPixmap(pixmap)

    def _display_status(self, summary: dict, detections: list) -> None:
        """
        Render the structured verification result returned by
        AssetVerifier.verify() into the four DeskGuard status formats:
        Ready / Not Ready / Ready with Warnings - including each
        detected item's confidence score.
        """
        status_text = self._format_verification_message(summary, detections)
        self.status_box.setPlainText(status_text)

    @staticmethod
    def _build_confidence_lookup(detections: list) -> dict:
        """
        Build a {label: best_confidence} map from raw detections.
        Labels are lowercased/stripped to match AssetVerifier's own
        normalization, and if the same label appears more than once
        the highest confidence score is kept.
        """
        confidence_by_label: dict = {}
        for det in detections:
            label = str(det.get("label", "")).strip().lower()
            if not label:
                continue
            confidence = float(det.get("confidence", 0.0))
            if label not in confidence_by_label or confidence > confidence_by_label[label]:
                confidence_by_label[label] = confidence
        return confidence_by_label

    @classmethod
    def _format_verification_message(cls, summary: dict, detections: list) -> str:
        """Build the display text for a verification result, per DeskGuard's
        four defined cases (Ready / Not Ready / Ready with Warnings),
        with each detected item's confidence score shown alongside it.

        Note: confidence is display-only here - it plays no part in the
        PASS/FAIL decision itself, which AssetVerifier computes purely
        from presence/absence (per DeskGuard rule: "ignore confidence
        scores while verifying").
        """
        missing_assets = summary.get("missing_assets", [])
        unexpected_objects = summary.get("unexpected_objects", [])
        status = summary.get("status")

        confidence_by_label = cls._build_confidence_lookup(detections)

        # Detected required assets, with the confidence of whichever raw
        # label satisfied that requirement (e.g. "laptop" or "monitor"
        # for the Laptop/Monitor requirement).
        detected_lines = []
        for info in REQUIRED_ASSETS.values():
            matched_labels = info["labels"] & confidence_by_label.keys()
            if not matched_labels:
                continue
            best_label = max(matched_labels, key=lambda l: confidence_by_label[l])
            confidence_pct = confidence_by_label[best_label] * 100
            detected_lines.append(f"\u2713 {info['display']} ({confidence_pct:.0f}%)")

        missing_block = (
            "\n".join(f"- {name}" for name in missing_assets) or "None"
        )
        unexpected_block = (
            "\n".join(
                f"- {label} ({confidence_by_label.get(label, 0.0) * 100:.0f}%)"
                for label in unexpected_objects
            )
            or "None"
        )
        detected_block = "\n".join(detected_lines) or "None"

        if status == "READY":
            header = "\U0001F7E2 Workspace Ready"
            footer = "Everything is set for the work to be done."
        elif status == "READY_WITH_WARNINGS":
            header = "\U0001F7E1 Workspace Ready with Warnings"
            footer = (
                "Everything is set for the work to be done.\n\n"
                "Warning:\n"
                "Unexpected objects detected on the workspace."
            )
        else:  # NOT_READY
            header = "\U0001F534 Workspace Not Ready"
            if missing_assets and unexpected_objects:
                footer = (
                    "Please place the missing assets and remove unexpected "
                    "objects before starting work."
                )
            else:
                footer = "Please place the missing assets before starting work."

        return (
            f"[{utils.get_timestamp()}]\n"
            f"{header}\n\n"
            f"Detected Assets:\n{detected_block}\n\n"
            f"Missing Assets:\n{missing_block}\n\n"
            f"Unexpected Objects:\n{unexpected_block}\n\n"
            f"{footer}\n"
        )

    def closeEvent(self, event) -> None:
        self.stop_monitoring()
        event.accept()
