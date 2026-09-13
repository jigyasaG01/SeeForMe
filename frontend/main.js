/**
 * SeeForMe - Shared Landing Page & Multi-page Interactivity
 */

document.addEventListener("DOMContentLoaded", () => {
  // 1. Fetch and Display Engine Status across pages
  const hwNameElem = document.getElementById("hw-name");
  const connDot = document.getElementById("conn-dot");

  async function checkServerStatus() {
    try {
      const res = await fetch("/api/status");
      if (res.ok) {
        const data = await res.json();
        if (hwNameElem) hwNameElem.textContent = `${data.device || "CPU"}`;
        if (connDot) connDot.classList.add("online");
      }
    } catch (err) {
      if (hwNameElem) hwNameElem.textContent = "Offline";
      if (connDot) connDot.classList.remove("online");
    }
  }
  checkServerStatus();

  // 2. Mobile Navigation Toggle
  const mobileMenuBtn = document.getElementById("mobile-menu-btn");
  const navLinks = document.getElementById("nav-links");
  if (mobileMenuBtn && navLinks) {
    mobileMenuBtn.addEventListener("click", () => {
      navLinks.classList.toggle("open");
    });
  }

  // 3. FAQ Accordion Toggle
  const faqItems = document.querySelectorAll(".faq-item");
  faqItems.forEach((item) => {
    const questionBtn = item.querySelector(".faq-question");
    if (questionBtn) {
      questionBtn.addEventListener("click", () => {
        const isOpen = item.classList.contains("open");
        // Close all other open items
        faqItems.forEach((i) => i.classList.remove("open"));
        if (!isOpen) {
          item.classList.add("open");
        }
      });
    }
  });

  // 4. Interactive Pipeline Stepper (for index.html)
  const stepBtns = document.querySelectorAll(".step-btn");
  const stepData = {
    1: {
      title: "1. YOLOv8 Object Detection",
      desc: "Incoming 30 FPS RGB video frames are fed through an optimized YOLOv8 neural network. The detector pinpoints all visible obstacles (pedestrians, vehicles, obstacles, animals), producing bounded coordinate boxes, class classifications, and confidence probabilities in under 25ms.",
      code: "# Ultralytics YOLOv8 inference\nresults = model.predict(frame_rgb, conf=0.40)\nfor box in results[0].boxes:\n    class_name = names[int(box.cls[0])]\n    confidence = float(box.conf[0])\n    x1, y1, x2, y2 = box.xyxy[0]",
      badge: "PYTHON / ULTRALYTICS"
    },
    2: {
      title: "2. MiDaS Monocular Depth Estimation",
      desc: "Simultaneously, the MiDaS vision model estimates relative depth maps directly from a single monocular camera feed. Without needing dual stereo cameras or LiDAR sensors, it computes inverse depth disparities across all pixels.",
      code: "# MiDaS inverse depth estimation\ninput_batch = transform(frame_rgb).to(device)\nwith torch.no_grad():\n    disparity = midas(input_batch)\n# Normalize to relative distance map\nraw_depth = disparity.cpu().numpy()",
      badge: "PYTORCH / MIDAS"
    },
    3: {
      title: "3. Spatial-Depth Sensor Fusion",
      desc: "The system overlays the bounding boxes onto the depth map. Rather than naive whole-box averaging, it takes a ground-contact trimmed sample (the lower 60% of the box) to calculate exact relative distance and directional heading.",
      code: "# Ground-contact depth sampling\ndepth_crop = raw_depth[y_ground:y2, x1:x2]\ndisparity_val = np.percentile(depth_crop, 75)\nestimated_meters = (SCALE / disparity_val)\nbearing = compute_bearing(center_x, frame_width)",
      badge: "NUMPY / SENSOR FUSION"
    },
    4: {
      title: "4. Urgency Ranking & Temporal Debounce",
      desc: "Obstacles directly inside the walking corridor are given immediate priority. A temporal debounce filter suppresses repetitive chatter within a 3-second window unless a hazard approaches significantly closer.",
      code: "# Urgency & Debounce filter\nscore = (proximity * 1.5) + (corridor * 1.2) + (hazard_type * 2.0)\nif should_debounce(hazard_id, distance):\n    suppress_alert()\nelse:\n    trigger_alert(f'{hazard}, {dist}m ahead, {bearing}')",
      badge: "FILTER / PRIORITY LOGIC"
    },
    5: {
      title: "5. Real-time Audio Guidance (TTS)",
      desc: "The top prioritized hazard is synthesized and vocalized via the browser's native Web Speech API (zero-latency, natural tone) or backend TTS engines, guiding the user safely around obstacles.",
      code: "// Web Speech API voice synthesis\nconst utterance = new SpeechSynthesisUtterance('Caution: Person, 2 meters ahead, slightly left.');\nutterance.rate = 1.1;\nwindow.speechSynthesis.speak(utterance);",
      badge: "WEB SPEECH API"
    }
  };

  const stepTitle = document.getElementById("step-title");
  const stepDesc = document.getElementById("step-desc");
  const stepCode = document.getElementById("step-code");
  const stepBadge = document.getElementById("step-badge");

  if (stepBtns.length > 0 && stepTitle && stepDesc && stepCode) {
    stepBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        stepBtns.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        const stepNum = btn.getAttribute("data-step");
        const info = stepData[stepNum];
        if (info) {
          stepTitle.textContent = info.title;
          stepDesc.textContent = info.desc;
          stepCode.textContent = info.code;
          if (stepBadge) stepBadge.textContent = info.badge;
        }
      });
    });
  }
});
