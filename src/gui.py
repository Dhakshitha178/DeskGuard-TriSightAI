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
from src.verifier import AssetVerifier


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
        self._display_status(summary)
        self._display_frame(frame)

    def _display_frame(self, frame) -> None:
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        qt_image = QImage(rgb_image.data, w, h, ch * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image).scaled(
            self.video_label.width(), self.video_label.height(), Qt.KeepAspectRatio
        )
        self.video_label.setPixmap(pixmap)

    def _display_status(self, summary: dict) -> None:
        status_text = (
            f"[{utils.get_timestamp()}] Status: {summary['status']}\n"
            f"  Missing: {summary['missing'] or 'None'}\n"
            f"  Unexpected: {summary['unexpected'] or 'None'}\n"
        )
        self.status_box.append(status_text)

    def closeEvent(self, event) -> None:
        self.stop_monitoring()
        event.accept()