"""Unified Perception & Navigation Pipeline for SeeForMe."""
import logging
import time
from typing import Dict, Any, Optional
import numpy as np
from backend.app.detector import ObjectDetector
from backend.app.depth import DepthEstimator
from backend.app.fusion import SpatialDepthFusion
from backend.app.prioritizer import AlertPrioritizer

logger = logging.getLogger(__name__)

class NavigationPipeline:
    def __init__(self, yolo_model: Optional[str] = None, midas_model: Optional[str] = None, device: Optional[str] = None):
        logger.info("Initializing SeeForMe perception pipeline...")
        self.detector = ObjectDetector(model_name=yolo_model, device=device)
        self.depth_estimator = DepthEstimator(model_type=midas_model, device=device)
        self.fusion = SpatialDepthFusion()
        self.prioritizer = AlertPrioritizer()
        logger.info("Perception pipeline fully initialized and ready.")

    def process_frame(
        self, 
        frame_rgb: np.ndarray, 
        conf_threshold: Optional[float] = None,
        include_depth_map: bool = True
    ) -> Dict[str, Any]:
        """
        Executes perception cycle:
        1. Object Detection (YOLO)
        2. Monocular Depth Estimation (MiDaS)
        3. Spatial-Depth Fusion
        4. Urgency Ranking & Alert Debounce
        """
        t_start = time.perf_counter()
        h, w, _ = frame_rgb.shape

        # Step 1: Object Detection
        t_det_start = time.perf_counter()
        detections = self.detector.detect(frame_rgb, conf_threshold=conf_threshold)
        t_det = round((time.perf_counter() - t_det_start) * 1000, 1)

        # Step 2: Depth Estimation
        t_depth_start = time.perf_counter()
        raw_depth, depth_colormap = self.depth_estimator.estimate(frame_rgb)
        t_depth = round((time.perf_counter() - t_depth_start) * 1000, 1)

        # Step 3: Fusion
        t_fusion_start = time.perf_counter()
        fused_objects = self.fusion.fuse(detections, raw_depth, frame_width=w, frame_height=h)
        
        # Step 4: Prioritization & Debouncing
        ranked_objects, spoken_alerts = self.prioritizer.process(fused_objects)
        t_fusion = round((time.perf_counter() - t_fusion_start) * 1000, 1)

        t_total = round((time.perf_counter() - t_start) * 1000, 1)

        return {
            "objects": ranked_objects,
            "spoken_alerts": spoken_alerts,
            "depth_colormap": depth_colormap if include_depth_map else None,
            "frame_size": {"width": w, "height": h},
            "timings_ms": {
                "detection": t_det,
                "depth": t_depth,
                "fusion_and_priority": t_fusion,
                "total": t_total,
                "fps": round(1000.0 / max(1.0, t_total), 1)
            }
        }
