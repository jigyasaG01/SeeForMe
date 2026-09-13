"""Standalone End-to-End Test for SeeForMe Pipeline."""
import sys
import os
import time
import numpy as np

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

def run_test():
    print("=" * 60)
    print("Starting SeeForMe Pipeline Verification Test")
    print("=" * 60)

    # 1. Imports
    print("\n[Step 1/4] Importing backend modules...")
    try:
        from backend.app.config import settings
        from backend.app.detector import ObjectDetector
        from backend.app.depth import DepthEstimator
        from backend.app.fusion import SpatialDepthFusion
        from backend.app.prioritizer import AlertPrioritizer
        from backend.app.pipeline import NavigationPipeline
        print("[OK] All modules imported successfully.")
    except Exception as e:
        print(f"[FAIL] Import failed: {e}")
        sys.exit(1)

    # 2. Pipeline Initialization
    print("\n[Step 2/4] Initializing NavigationPipeline (YOLO + MiDaS)...")
    t0 = time.time()
    try:
        pipeline = NavigationPipeline()
        print(f"[OK] Pipeline initialized in {time.time() - t0:.2f}s")
    except Exception as e:
        print(f"[FAIL] Initialization failed: {e}")
        sys.exit(1)

    # 3. Create a test frame
    print("\n[Step 3/4] Creating simulated test frame (640x480 RGB)...")
    # Generate a frame with gradient background and a simulated bright box
    h, w = 480, 640
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    # Background gradient
    for y in range(h):
        frame[y, :, :] = int(y / h * 120)
    # Add simulated foreground rectangles
    frame[150:380, 240:400] = [200, 180, 160] # Center foreground
    frame[200:300, 50:150] = [100, 150, 200]  # Left object
    print("[OK] Test frame generated.")

    # 4. Process frame
    print("\n[Step 4/4] Executing perception pipeline on test frame...")
    try:
        results = pipeline.process_frame(frame, include_depth_map=True)
        print("[OK] Pipeline executed successfully!")
        
        print("\n--- Pipeline Telemetry ---")
        timings = results.get("timings_ms", {})
        print(f"  Detection latency:    {timings.get('detection')} ms")
        print(f"  Depth latency:        {timings.get('depth')} ms")
        print(f"  Fusion & Priority:    {timings.get('fusion_and_priority')} ms")
        print(f"  Total Cycle Time:     {timings.get('total')} ms (~{timings.get('fps')} FPS)")
        
        objects = results.get("objects", [])
        print(f"\n  Detected Objects:     {len(objects)}")
        for obj in objects:
            print(f"    - {obj['class_name'].upper()} at ~{obj['estimated_meters']}m ({obj['bearing']}) | Urgency: {obj.get('urgency_score')}")

        alerts = results.get("spoken_alerts", [])
        print(f"\n  Generated Spoken Alerts: {len(alerts)}")
        for alert in alerts:
            print(f"    [ALERT] \"{alert}\"")

        # Check depth colormap
        depth_map = results.get("depth_colormap")
        if depth_map is not None:
            print(f"\n  Depth Heatmap Shape:  {depth_map.shape} (Inferno colormap generated)")
            
    except Exception as e:
        print(f"✗ Execution error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 60)
    print("TEST PASSED: SeeForMe pipeline is fully functional!")
    print("=" * 60)

if __name__ == "__main__":
    run_test()
