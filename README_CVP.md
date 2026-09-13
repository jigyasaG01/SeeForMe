# Assistive Navigation for the Visually Impaired

A computer vision system that helps visually impaired users navigate their surroundings by detecting obstacles, estimating distances, and delivering real-time spoken alerts through a phone or smart-glasses camera feed.

## Overview

This project combines object detection, monocular depth estimation, and text-to-speech into a real-time pipeline that acts like a "sighted companion" — announcing hazards such as people, vehicles, curbs, and stairs as the user walks.

**Example alert:** *"Person, 2 meters ahead, slightly left."*

## Why This Project

Roughly 40 million people worldwide are blind and 250 million have low vision. Existing aids (canes, guide dogs) help with immediate physical obstacles but don't identify objects, read signage, or provide contextual distance information. This project prototypes the core software pipeline for that gap — it is a learning/portfolio project, not a replacement for products like OrCam or Envision Glasses.

## Pipeline Architecture

```
Camera Frame
   │
   ├─► YOLO: object detection → bounding boxes + class + confidence
   │
   ├─► MiDaS: depth estimation → relative distance map
   │
   ├─► Fusion: sample depth map inside each YOLO box → distance per object
   │
   ├─► Prioritization: filter to walking path, rank by urgency, debounce repeats
   │
   └─► TTS: speak top 1–2 alerts per cycle
```

## Tech Stack

| Component | Tool |
|---|---|
| Object detection | YOLOv8n / YOLOv8s (Ultralytics) |
| Depth estimation | MiDaS (small / DPT-Hybrid) |
| Text-to-speech | Coqui TTS / Android TTS / iOS AVSpeechSynthesizer |
| Backend (prototype) | FastAPI |
| Frontend (dev/debug) | React (bounding box + depth overlay) |
| Frontend (end user) | Flutter / React Native — minimal audio-first UI |
| On-device deployment | TensorFlow Lite (Android) / CoreML (iOS) |

## Datasets

- **COCO** — https://cocodataset.org/#download — general object classes (people, vehicles, etc.)
- **Mapillary Vistas** — https://www.mapillary.com/dataset/vistas — sidewalks, curbs, poles
- **BDD100K** — https://bdd-data.berkeley.edu/ — supplementary road-scene data
- **Cityscapes** — https://www.cityscapes-dataset.com/ — fine-grained urban scene segmentation
- **NYU Depth V2** — https://cs.nyu.edu/~fergus/datasets/nyu_depth_v2.html — indoor depth (optional)
- **KITTI** — https://www.cvlibs.net/datasets/kitti/ — outdoor depth benchmark (optional)
- **Roboflow Universe** — https://universe.roboflow.com/ — community datasets for potholes, stairs, etc.
- **CVAT** — https://www.cvat.ai/ — annotation tool for self-collected hazard images

## Project Status

🚧 Prototype stage — see [Roadmap](#roadmap) below.

## Roadmap

- [ ] Stage 1: Backend prototype — YOLOv8n + MiDaS running on webcam feed via FastAPI
- [ ] Stage 2: Add TTS output for detected alerts
- [ ] Stage 3: Add prioritization/debounce logic (walking-path filter, urgency ranking)
- [ ] Stage 4: Build minimal frontend (webcam view + audio output)
- [ ] Stage 5: Measure end-to-end latency (target: 300–500ms)
- [ ] Stage 6: Convert models to TFLite/CoreML for on-device deployment
- [ ] Stage 7 (stretch): Fine-tune on custom hazard classes (curbs, stairs, potholes)
- [ ] Stage 8 (stretch): User test with visually impaired users

## Setup

```bash
# Clone the repo
git clone <your-repo-url>
cd assistive-navigation

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# Run backend (webcam prototype)
python backend/main.py

# Run frontend (dev dashboard)
cd frontend
npm install
npm start
```

## Known Limitations

- MiDaS provides **relative**, not metric, depth — distances are approximate without calibration.
- Curb/stair detection is not well covered by public datasets and will need custom-labeled data.
- Phone-in-hand form factor is a prototyping stand-in; the target deployment is hands-free (chest harness, clip-on camera, or smart glasses).
- Not validated with real visually impaired users yet — treat all alerts as experimental.

## Disclaimer

This is a prototype/educational project and has not been tested for safety-critical, real-world navigation use. Do not rely on it as a substitute for a cane, guide dog, or orientation & mobility training.

## License

Add your chosen license here (e.g., MIT).
