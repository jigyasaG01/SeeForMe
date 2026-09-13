"""FastAPI Application & Streaming Server for SeeForMe."""
import base64
import io
import logging
from contextlib import asynccontextmanager
from typing import Optional

import cv2
import numpy as np
import torch
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from backend.app.config import settings
from backend.app.pipeline import NavigationPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("SeeForMe")

# Global pipeline instance
pipeline: Optional[NavigationPipeline] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline
    logger.info("Initializing SeeForMe AI Pipeline during startup...")
    try:
        pipeline = NavigationPipeline()
        logger.info("SeeForMe Pipeline loaded and ready for inference.")
    except Exception as e:
        logger.error(f"Error initializing pipeline: {e}", exc_info=True)
    yield
    logger.info("Shutting down SeeForMe server...")

app = FastAPI(
    title="SeeForMe Navigation API",
    description="Real-time Assistive Vision Pipeline for Obstacle Detection & Audio Guidance",
    version="0.1.0",
    lifespan=lifespan
)

# Enable CORS for browser frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def encode_image_to_base64_jpeg(image_rgb: np.ndarray, quality: int = 70) -> str:
    """Encodes an RGB numpy array to base64 JPEG string."""
    image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    success, buffer = cv2.imencode(".jpg", image_bgr, encode_params)
    if not success:
        return ""
    return base64.b64encode(buffer).decode("utf-8")

@app.get("/api/status")
async def get_status():
    """Returns runtime status and hardware information."""
    cuda_available = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_available else "CPU"
    return {
        "status": "online",
        "pipeline_ready": pipeline is not None,
        "device": device_name,
        "cuda_available": cuda_available,
        "torch_version": torch.__version__,
        "config": {
            "yolo_model": settings.YOLO_MODEL,
            "midas_model": settings.MIDAS_MODEL_TYPE,
            "confidence_threshold": settings.CONFIDENCE_THRESHOLD,
            "corridor": [settings.WALKING_CORRIDOR_LEFT, settings.WALKING_CORRIDOR_RIGHT]
        }
    }

@app.post("/api/process-frame")
async def process_frame_endpoint(
    file: UploadFile = File(...),
    confidence: Optional[float] = Form(None),
    return_depth_map: bool = Form(True)
):
    """Processes an uploaded camera frame image file."""
    if pipeline is None:
        return JSONResponse(status_code=503, content={"error": "Pipeline initializing"})

    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    frame_rgb = np.array(image)

    result = pipeline.process_frame(
        frame_rgb,
        conf_threshold=confidence,
        include_depth_map=return_depth_map
    )

    depth_b64 = None
    if return_depth_map and result.get("depth_colormap") is not None:
        depth_b64 = encode_image_to_base64_jpeg(result["depth_colormap"])

    return {
        "objects": result["objects"],
        "spoken_alerts": result["spoken_alerts"],
        "timings_ms": result["timings_ms"],
        "frame_size": result["frame_size"],
        "depth_colormap_base64": depth_b64
    }

@app.websocket("/ws/stream")
async def websocket_stream_endpoint(websocket: WebSocket):
    """
    High-frequency WebSocket endpoint for real-time video stream processing.
    Accepts: Base64 JPEG data URL or binary JPEG frame.
    Returns: JSON with detections, distances, alerts, timings, and optional depth map.
    """
    await websocket.accept()
    logger.info("WebSocket client connected to /ws/stream")
    try:
        while True:
            # Receive either text (base64) or bytes
            message = await websocket.receive()
            if "bytes" in message and message["bytes"]:
                data = message["bytes"]
                img_array = np.frombuffer(data, dtype=np.uint8)
                frame_bgr = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                if frame_bgr is None:
                    continue
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            elif "text" in message and message["text"]:
                text_data = message["text"]
                # If header exists (e.g. data:image/jpeg;base64,...)
                if "," in text_data:
                    text_data = text_data.split(",", 1)[1]
                image_bytes = base64.b64decode(text_data)
                img_array = np.frombuffer(image_bytes, dtype=np.uint8)
                frame_bgr = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                if frame_bgr is None:
                    continue
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            else:
                continue

            if pipeline is None:
                await websocket.send_json({"error": "Pipeline loading"})
                continue

            # Process frame
            result = pipeline.process_frame(frame_rgb, include_depth_map=True)

            depth_b64 = ""
            if result.get("depth_colormap") is not None:
                depth_b64 = encode_image_to_base64_jpeg(result["depth_colormap"], quality=65)

            payload = {
                "objects": result["objects"],
                "spoken_alerts": result["spoken_alerts"],
                "timings": result["timings_ms"],
                "depth_map": f"data:image/jpeg;base64,{depth_b64}" if depth_b64 else None
            }
            await websocket.send_json(payload)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)

# Mount frontend directory for web access
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
