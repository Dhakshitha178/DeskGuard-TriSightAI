"""
detector.py
-----------
Object detection module for DeskGuard.

Wraps a YOLO model (via ultralytics) to detect workspace assets
(laptop, monitor, keyboard, mouse, phone, etc.) from a camera feed
or static image.

Owned primarily by: Dhakshitha
"""

from typing import Any, Dict, List, Optional

import cv2
from loguru import logger
from ultralytics import YOLO

from src import config


class AssetDetector:
    """
    Loads a YOLO model and runs inference on frames to detect
    workspace assets.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        confidence_threshold: float = config.CONFIDENCE_THRESHOLD,
        iou_threshold: float = config.IOU_THRESHOLD,
    ) -> None:
        self.model_path = str(model_path or config.MODEL_PATH)
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.model: Optional[YOLO] = None

    def load_model(self) -> None:
        """Load the YOLO model into memory. Call once before running inference."""
        logger.info(f"Loading detection model from: {self.model_path}")
        try:
            self.model = YOLO(self.model_path)
            logger.info("Model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def detect(self, frame) -> List[Dict[str, Any]]:
        """
        Run detection on a single frame.

        Returns a list of detections:
            [{"label": str, "confidence": float, "bbox": (x1, y1, x2, y2)}, ...]
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        results = self.model(
            frame,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            verbose=False,
        )

        detections: List[Dict[str, Any]] = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                cls_id = int(box.cls[0])
                label = self.model.names.get(cls_id, str(cls_id))
                confidence = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detections.append(
                    {
                        "label": label,
                        "confidence": confidence,
                        "bbox": (x1, y1, x2, y2),
                    }
                )

        return detections

    def detect_from_source(self, source: int = config.CAMERA_INDEX):
        """
        Generator that yields (frame, detections) tuples from a live
        camera source. Useful for quick standalone testing of the detector.
        """
        cap = cv2.VideoCapture(source)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

        if not cap.isOpened():
            raise RuntimeError(f"Could not open camera source: {source}")

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    logger.warning("Failed to read frame from camera.")
                    break
                detections = self.detect(frame)
                yield frame, detections
        finally:
            cap.release()


if __name__ == "__main__":
    # Simple manual test: run detector on the default camera and print results.
    detector = AssetDetector()
    detector.load_model()
    for frame, detections in detector.detect_from_source():
        logger.info(f"Detections: {detections}")
        cv2.imshow("DeskGuard Detector Test", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cv2.destroyAllWindows()