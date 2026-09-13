"""Configuration settings for SeeForMe navigation pipeline."""
from pydantic import BaseModel
from typing import Set, Dict

class Settings(BaseModel):
    # Model settings
    YOLO_MODEL: str = "yolov8n.pt"
    MIDAS_MODEL_TYPE: str = "MiDaS_small"  # Options: MiDaS_small, DPT_Hybrid
    DEVICE: str = "auto"  # 'auto', 'cuda', or 'cpu'

    # Detection & Spatial Settings
    CONFIDENCE_THRESHOLD: float = 0.40
    WALKING_CORRIDOR_LEFT: float = 0.30   # Left boundary of walking path (fraction of frame width)
    WALKING_CORRIDOR_RIGHT: float = 0.70  # Right boundary of walking path (fraction of frame width)

    # Urgency & Debounce Settings
    DEBOUNCE_COOLDOWN_SEC: float = 3.0     # Time before repeating the exact same object alert
    DISTANCE_CHANGE_THRESHOLD_M: float = 0.7 # If distance drops by this much, alert immediately
    MAX_ALERTS_PER_CYCLE: int = 2

    # Depth calibration approximation (Relative MiDaS depth -> Estimated meters)
    # MiDaS outputs inverse depth (disparity). Distance ~ A / (depth_val + B)
    DEPTH_CALIBRATION_SCALE: float = 1200.0

    # Obstacle categorization
    CRITICAL_HAZARDS: Set[str] = {
        "person", "car", "bus", "truck", "motorcycle", "bicycle", 
        "stop sign", "fire hydrant", "dog", "chair", "couch"
    }

    HAZARD_BASE_URGENCY: Dict[str, float] = {
        "car": 1.0,
        "bus": 1.0,
        "truck": 1.0,
        "motorcycle": 0.9,
        "bicycle": 0.8,
        "person": 0.7,
        "dog": 0.6,
        "chair": 0.5,
        "fire hydrant": 0.5,
        "stop sign": 0.4,
    }

settings = Settings()
