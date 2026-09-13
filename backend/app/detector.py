"""YOLOv8 Object Detector for SeeForMe."""
import logging
from typing import List, Dict, Any
import numpy as np
import torch
from ultralytics import YOLO
from backend.app.config import settings

logger = logging.getLogger(__name__)

class ObjectDetector:
    def __init__(self, model_name: str = None, device: str = None):
        self.model_name = model_name or settings.YOLO_MODEL
        if device is None or device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        logger.info(f"Loading YOLO model '{self.model_name}' on device '{self.device}'...")
        self.model = YOLO(self.model_name)
        # Move model to device
        self.model.to(self.device)
        logger.info("YOLO model loaded successfully.")

    def detect(self, frame_rgb: np.ndarray, conf_threshold: float = None) -> List[Dict[str, Any]]:
        """
        Runs object detection on an RGB frame (H, W, 3).
        Returns a list of detected objects with bounding boxes and classes.
        """
        conf = conf_threshold if conf_threshold is not None else settings.CONFIDENCE_THRESHOLD
        
        results = self.model.predict(
            source=frame_rgb,
            conf=conf,
            device=self.device,
            verbose=False
        )

        detections = []
        if not results or len(results) == 0:
            return detections

        r = results[0]
        boxes = r.boxes
        if boxes is None or len(boxes) == 0:
            return detections

        for box in boxes:
            cls_id = int(box.cls[0].item())
            class_name = r.names.get(cls_id, f"class_{cls_id}")
            confidence = float(box.conf[0].item())
            
            # Coordinates: [x1, y1, x2, y2]
            xyxy = box.xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])
            
            w = max(1.0, x2 - x1)
            h = max(1.0, y2 - y1)
            cx = x1 + w / 2.0
            cy = y1 + h / 2.0

            detections.append({
                "class_name": class_name,
                "confidence": round(confidence, 3),
                "box": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                "center": [round(cx, 1), round(cy, 1)],
                "width": round(w, 1),
                "height": round(h, 1)
            })

        return detections
