"""Spatial-Depth Fusion module for SeeForMe."""
import logging
from typing import List, Dict, Any
import numpy as np
from backend.app.config import settings

logger = logging.getLogger(__name__)

class SpatialDepthFusion:
    def __init__(self, depth_scale: float = None):
        self.depth_scale = depth_scale or settings.DEPTH_CALIBRATION_SCALE

    def fuse(
        self, 
        detections: List[Dict[str, Any]], 
        raw_depth: np.ndarray, 
        frame_width: int, 
        frame_height: int
    ) -> List[Dict[str, Any]]:
        """
        Fuses 2D bounding boxes with monocular depth map to compute relative distance,
        spatial direction (bearing), and walking corridor presence.
        """
        fused_objects = []
        if raw_depth is None or len(detections) == 0:
            return fused_objects

        h, w = raw_depth.shape

        for det in detections:
            x1, y1, x2, y2 = det["box"]
            cx, cy = det["center"]

            # Clamp box to valid frame coordinates
            ix1 = max(0, min(w - 1, int(x1)))
            iy1 = max(0, min(h - 1, int(y1)))
            ix2 = max(0, min(w, int(x2)))
            iy2 = max(0, min(h, int(y2)))

            if ix2 <= ix1 or iy2 <= iy1:
                continue

            # Crop box region with a focused central-lower mask to avoid background bleed
            box_w = ix2 - ix1
            box_h = iy2 - iy1

            sample_x1 = int(ix1 + 0.20 * box_w)
            sample_x2 = int(ix1 + 0.80 * box_w)
            sample_y1 = int(iy1 + 0.30 * box_h)
            sample_y2 = int(iy1 + 0.90 * box_h)

            if sample_x2 > sample_x1 and sample_y2 > sample_y1:
                depth_crop = raw_depth[sample_y1:sample_y2, sample_x1:sample_x2]
            else:
                depth_crop = raw_depth[iy1:iy2, ix1:ix2]

            # In MiDaS disparity, higher value = closer object.
            # Use 75th percentile to capture the foreground object body robustly.
            disparity_val = float(np.percentile(depth_crop, 75)) if depth_crop.size > 0 else 1.0

            # Approximate metric distance in meters (Z = C / disparity)
            # Clamped between realistic navigation ranges: ~0.5m to ~15.0m
            safe_disparity = max(1.0, disparity_val)
            raw_meters = (self.depth_scale / safe_disparity)
            estimated_meters = round(float(np.clip(raw_meters, 0.5, 15.0)), 1)

            # Categorize distance for speech
            if estimated_meters < 1.3:
                distance_phrase = "under 1 meter"
            elif estimated_meters < 2.5:
                distance_phrase = f"{round(estimated_meters)} meters"
            elif estimated_meters < 4.5:
                distance_phrase = f"{round(estimated_meters)} meters"
            elif estimated_meters < 7.0:
                distance_phrase = "about 5 meters"
            else:
                distance_phrase = "in the distance"

            # Determine horizontal bearing (direction)
            norm_cx = cx / float(frame_width)
            if norm_cx < 0.20:
                bearing = "far left"
            elif norm_cx < 0.38:
                bearing = "slightly left"
            elif norm_cx <= 0.62:
                bearing = "directly ahead"
            elif norm_cx <= 0.80:
                bearing = "slightly right"
            else:
                bearing = "far right"

            # Check if in direct walking corridor
            in_corridor = (settings.WALKING_CORRIDOR_LEFT <= norm_cx <= settings.WALKING_CORRIDOR_RIGHT)

            fused_objects.append({
                **det,
                "disparity": round(disparity_val, 2),
                "estimated_meters": estimated_meters,
                "distance_phrase": distance_phrase,
                "bearing": bearing,
                "in_corridor": in_corridor,
                "norm_center_x": round(norm_cx, 3),
            })

        return fused_objects
