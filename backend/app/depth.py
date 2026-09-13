"""MiDaS Monocular Depth Estimator for SeeForMe."""
import logging
from typing import Tuple
import cv2
import numpy as np
import torch
from backend.app.config import settings

logger = logging.getLogger(__name__)

class DepthEstimator:
    def __init__(self, model_type: str = None, device: str = None):
        self.model_type = model_type or settings.MIDAS_MODEL_TYPE
        if device is None or device == "auto":
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        logger.info(f"Loading MiDaS depth model '{self.model_type}' on '{self.device}'...")
        try:
            # Load model from torch hub
            self.model = torch.hub.load("intel-isl/MiDaS", self.model_type, trust_repo=True)
            self.model.to(self.device)
            self.model.eval()

            # Load transforms
            midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms", trust_repo=True)
            if self.model_type in ["DPT_Large", "DPT_Hybrid"]:
                self.transform = midas_transforms.dpt_transform
            else:
                self.transform = midas_transforms.small_transform

            logger.info("MiDaS depth model and transform initialized.")
        except Exception as e:
            logger.error(f"Failed to load MiDaS from torch hub: {e}. Fallback might be needed.", exc_info=True)
            raise

    def estimate(self, frame_rgb: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Estimates depth from an RGB frame (H, W, 3).
        Returns:
            raw_depth: (H, W) float32 disparity map (higher values = closer objects).
            depth_colormap: (H, W, 3) uint8 colored heatmap (for visual frontend/debug).
        """
        h, w, _ = frame_rgb.shape

        # Transform frame for model
        input_batch = self.transform(frame_rgb).to(self.device)

        with torch.no_grad():
            prediction = self.model(input_batch)

            # Prediction is disparity: resize to original resolution
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=(h, w),
                mode="bicubic",
                align_corners=False,
            ).squeeze()

        raw_depth = prediction.cpu().numpy().astype(np.float32)

        # Normalize to 0-255 for visualization
        depth_min = float(raw_depth.min())
        depth_max = float(raw_depth.max())
        if depth_max > depth_min:
            depth_norm = (255 * (raw_depth - depth_min) / (depth_max - depth_min)).astype(np.uint8)
        else:
            depth_norm = np.zeros((h, w), dtype=np.uint8)

        # Apply Inferno colormap (hot colors = close, cool colors = far)
        depth_colormap = cv2.applyColorMap(depth_norm, cv2.COLORMAP_INFERNO)
        depth_colormap = cv2.cvtColor(depth_colormap, cv2.COLOR_BGR2RGB)

        return raw_depth, depth_colormap
