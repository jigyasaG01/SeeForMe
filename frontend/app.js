/**
 * SeeForMe - Interactive Assistive Navigation Client
 */

class SeeForMeApp {
  constructor() {
    // Media & Canvas elements
    this.video = document.getElementById("webcam");
    this.previewImg = document.getElementById("preview-img");
    this.canvas = document.getElementById("overlay-canvas");
    this.ctx = this.canvas.getContext("2d");
    this.depthImg = document.getElementById("depth-img");
    this.idleCover = document.getElementById("idle-cover");
    
    // Status elements
    this.connDot = document.getElementById("conn-dot");
    this.connStatus = document.getElementById("conn-status");
    this.hwName = document.getElementById("hw-name");
    this.fpsVal = document.getElementById("fps-val");
    
    // Telemetry
    this.tYolo = document.getElementById("t-yolo");
    this.tDepth = document.getElementById("t-depth");
    this.tFusion = document.getElementById("t-fusion");
    this.tTotal = document.getElementById("t-total");

    // Controls & Buttons
    this.startCamBtn = document.getElementById("start-cam-btn");
    this.camToggleStreamBtn = document.getElementById("cam-toggle-stream-btn");
    this.camToggleText = document.getElementById("cam-toggle-text");
    this.camFlipBtn = document.getElementById("cam-flip-btn");
    this.toggleDepthBtn = document.getElementById("toggle-depth-btn");
    this.audioToggleBtn = document.getElementById("audio-toggle-btn");
    this.audioBtnText = document.getElementById("audio-btn-text");
    this.testSpeechBtn = document.getElementById("test-speech-btn");
    this.fileInput = document.getElementById("file-input");

    // Lists
    this.alertsLog = document.getElementById("alerts-log");
    this.alertsCount = document.getElementById("alerts-count");
    this.objectsList = document.getElementById("objects-list");
    this.objectsCount = document.getElementById("objects-count");
    this.voiceToast = document.getElementById("voice-toast");
    this.voiceToastMsg = document.getElementById("voice-toast-msg");

    // Sliders & Endpoint
    this.confSlider = document.getElementById("conf-slider");
    this.confValLabel = document.getElementById("conf-val-label");
    this.rateSlider = document.getElementById("rate-slider");
    this.rateValLabel = document.getElementById("rate-val-label");
    this.backendInput = document.getElementById("backend-url-input");

    // Internal state
    this.backendUrl = localStorage.getItem("seeforme_backend_url") || "";
    if (!this.backendUrl && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")) {
      this.backendUrl = window.location.origin;
    }

    this.stream = null;
    this.ws = null;
    this.isStreaming = false;
    this.isProcessing = false;
    this.showDepth = false;
    this.audioEnabled = true;
    this.facingMode = "environment";
    this.totalAlertsCount = 0;
    this.speechRate = 1.1;
    this.lastSpokenText = "";
    this.lastSpokenTime = 0;

    // Temporary canvas for capturing frame to JPEG
    this.captureCanvas = document.createElement("canvas");
    this.captureCtx = this.captureCanvas.getContext("2d");

    this.init();
  }

  async init() {
    this.setupEventListeners();
    await this.fetchServerStatus();
    this.connectWebSocket();
  }

  setupEventListeners() {
    if (this.startCamBtn) this.startCamBtn.addEventListener("click", () => this.startCamera());
    if (this.camToggleStreamBtn) this.camToggleStreamBtn.addEventListener("click", () => this.toggleStream());
    if (this.camFlipBtn) this.camFlipBtn.addEventListener("click", () => this.flipCamera());
    if (this.toggleDepthBtn) this.toggleDepthBtn.addEventListener("click", () => this.toggleDepthOverlay());
    if (this.audioToggleBtn) this.audioToggleBtn.addEventListener("click", () => this.toggleAudio());
    if (this.testSpeechBtn) this.testSpeechBtn.addEventListener("click", () => this.speakAlert("Audio guidance is active. System ready."));

    if (this.confSlider) {
      this.confSlider.addEventListener("input", (e) => {
        if (this.confValLabel) this.confValLabel.textContent = `${e.target.value}%`;
      });
    }

    if (this.rateSlider) {
      this.rateSlider.addEventListener("input", (e) => {
        this.speechRate = parseFloat(e.target.value);
        if (this.rateValLabel) this.rateValLabel.textContent = `${this.speechRate.toFixed(1)}x`;
      });
    }

    if (this.backendInput) {
      this.backendInput.value = this.backendUrl;
      this.backendInput.addEventListener("change", (e) => {
        this.backendUrl = e.target.value.trim().replace(/\/+$/, "");
        localStorage.setItem("seeforme_backend_url", this.backendUrl);
        this.fetchServerStatus();
        if (this.ws) {
          try { this.ws.close(); } catch (_) {}
        }
        this.connectWebSocket();
      });
    }

    if (this.fileInput) {
      this.fileInput.addEventListener("change", (e) => this.handleImageUpload(e));
    }

    window.addEventListener("resize", () => this.resizeCanvas());
  }

  async fetchServerStatus() {
    const targetUrl = this.backendUrl ? `${this.backendUrl}/api/status` : "/api/status";
    try {
      const res = await fetch(targetUrl);
      if (res.ok) {
        const data = await res.json();
        if (this.hwName) this.hwName.textContent = data.device || "CPU";
        if (this.connDot) this.connDot.classList.add("active");
        if (this.connStatus) this.connStatus.textContent = "Server Ready";
      } else {
        throw new Error("HTTP " + res.status);
      }
    } catch (err) {
      console.warn("Server status check failed:", err);
      if (this.hwName) {
        this.hwName.textContent = window.location.hostname.includes("vercel.app") ? "Vercel Preview" : "Offline";
      }
      if (this.connStatus) {
        this.connStatus.textContent = window.location.hostname.includes("vercel.app") ? "Cloud Demo Mode" : "Server Offline";
      }
    }
  }

  connectWebSocket() {
    let wsUrl;
    if (this.backendUrl) {
      const wsProto = this.backendUrl.startsWith("https") ? "wss:" : "ws:";
      const host = this.backendUrl.replace(/^https?:\/\//, "");
      wsUrl = `${wsProto}//${host}/ws/stream`;
    } else {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      wsUrl = `${protocol}//${window.location.host}/ws/stream`;
    }

    if (this.connStatus && !window.location.hostname.includes("vercel.app")) {
      this.connStatus.textContent = "Connecting WS...";
    }
    
    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        if (this.connDot) this.connDot.classList.add("active");
        if (this.connStatus) this.connStatus.textContent = "Live Stream Connected";
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleInferenceResult(data);
        } catch (err) {
          console.error("Failed to parse WS message:", err);
        }
        this.isProcessing = false;
      };

      this.ws.onclose = () => {
        if (this.connDot) this.connDot.classList.remove("active");
        if (this.connStatus && !window.location.hostname.includes("vercel.app")) {
          this.connStatus.textContent = "Disconnected (Retrying...)";
        }
        setTimeout(() => {
          if (!this.backendUrl && window.location.hostname.includes("vercel.app")) return;
          this.connectWebSocket();
        }, 5000);
      };

      this.ws.onerror = (err) => {
        console.warn("WebSocket status:", err);
      };
    } catch (err) {
      console.warn("WebSocket init error:", err);
    }
  }

  async startCamera() {
    try {
      const constraints = {
        video: {
          facingMode: this.facingMode,
          width: { ideal: 640 },
          height: { ideal: 480 }
        },
        audio: false
      };

      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.video.srcObject = this.stream;
      await this.video.play();

      // Show video, hide preview image layer
      if (this.previewImg) this.previewImg.style.display = "none";
      if (this.video) this.video.style.display = "block";
      if (this.idleCover) this.idleCover.style.display = "none";
      if (this.camToggleStreamBtn) this.camToggleStreamBtn.disabled = false;

      this.isStreaming = true;
      if (this.camToggleText) this.camToggleText.textContent = "Pause Stream";

      this.resizeCanvas();
      this.speakAlert("Camera active. Assistive navigation started.");
      this.startStreamingLoop();
    } catch (err) {
      console.error("Camera access error:", err);
      alert(`Could not access webcam: ${err.message}. Ensure camera permissions are allowed.`);
    }
  }

  toggleStream() {
    this.isStreaming = !this.isStreaming;
    if (this.isStreaming) {
      if (this.camToggleText) this.camToggleText.textContent = "Pause Stream";
      this.startStreamingLoop();
    } else {
      if (this.camToggleText) this.camToggleText.textContent = "Resume Stream";
    }
  }

  async flipCamera() {
    this.facingMode = this.facingMode === "user" ? "environment" : "user";
    if (this.stream) {
      this.stream.getTracks().forEach(t => t.stop());
      await this.startCamera();
    }
  }

  toggleDepthOverlay() {
    this.showDepth = !this.showDepth;
    if (this.depthImg) {
      this.depthImg.style.display = this.showDepth ? "block" : "none";
    }
    if (this.toggleDepthBtn) {
      this.toggleDepthBtn.classList.toggle("btn-primary", this.showDepth);
    }
  }

  toggleAudio() {
    this.audioEnabled = !this.audioEnabled;
    if (this.audioToggleBtn) {
      this.audioToggleBtn.classList.toggle("active-audio", this.audioEnabled);
    }
    if (this.audioBtnText) {
      this.audioBtnText.textContent = this.audioEnabled ? "Voice: ON" : "Voice: OFF";
    }
    if (!this.audioEnabled && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  }

  resizeCanvas() {
    if (this.video && this.video.style.display !== "none" && this.video.videoWidth > 0) {
      this.canvas.width = this.video.videoWidth;
      this.canvas.height = this.video.videoHeight;
    } else if (this.previewImg && this.previewImg.style.display !== "none" && this.previewImg.naturalWidth > 0) {
      this.canvas.width = this.previewImg.naturalWidth;
      this.canvas.height = this.previewImg.naturalHeight;
    }
  }

  startStreamingLoop() {
    const loop = () => {
      if (!this.isStreaming) return;

      if (!this.isProcessing && this.ws && this.ws.readyState === WebSocket.OPEN && this.video.videoWidth > 0) {
        this.sendVideoFrame();
      }
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  sendVideoFrame() {
    this.isProcessing = true;
    const w = this.video.videoWidth;
    const h = this.video.videoHeight;

    if (this.captureCanvas.width !== w || this.captureCanvas.height !== h) {
      this.captureCanvas.width = w;
      this.captureCanvas.height = h;
    }

    this.captureCtx.drawImage(this.video, 0, 0, w, h);
    const jpegDataUrl = this.captureCanvas.toDataURL("image/jpeg", 0.65);
    this.ws.send(jpegDataUrl);
  }

  handleInferenceResult(data) {
    if (!data) return;

    // Update Telemetry
    if (data.timings) {
      if (this.tYolo) this.tYolo.textContent = `${data.timings.detection} ms`;
      if (this.tDepth) this.tDepth.textContent = `${data.timings.depth} ms`;
      if (this.tFusion) this.tFusion.textContent = `${data.timings.fusion_and_priority} ms`;
      if (this.tTotal) this.tTotal.textContent = `${data.timings.total} ms`;
      if (this.fpsVal) this.fpsVal.textContent = data.timings.fps.toFixed(1);
    }

    // Update Depth Map image
    if (data.depth_map && this.depthImg) {
      this.depthImg.src = data.depth_map;
      if (this.showDepth) {
        this.depthImg.style.display = "block";
      }
    }

    // Render Bounding Boxes on Overlay Canvas
    this.renderOverlay(data.objects || []);

    // Update Objects List
    this.updateObjectsList(data.objects || []);

    // Handle Spoken Alerts
    if (data.spoken_alerts && data.spoken_alerts.length > 0) {
      for (const alertStr of data.spoken_alerts) {
        this.addAlertToLog(alertStr);
        if (this.audioEnabled) {
          this.speakAlert(alertStr);
        }
      }
    }
  }

  renderOverlay(objects) {
    const w = this.canvas.width;
    const h = this.canvas.height;
    if (w === 0 || h === 0) return;

    // Clear transparent overlay without touching the underlying video or preview image element
    this.ctx.clearRect(0, 0, w, h);

    // Draw Walking Corridor overlay lines
    const leftX = w * 0.30;
    const rightX = w * 0.70;

    this.ctx.save();
    this.ctx.strokeStyle = "rgba(6, 182, 212, 0.25)";
    this.ctx.lineWidth = 2;
    this.ctx.setLineDash([6, 6]);

    this.ctx.beginPath();
    this.ctx.moveTo(leftX, 0);
    this.ctx.lineTo(leftX, h);
    this.ctx.moveTo(rightX, 0);
    this.ctx.lineTo(rightX, h);
    this.ctx.stroke();
    this.ctx.restore();

    // Draw detected object bounding boxes
    for (const obj of objects) {
      const [x1, y1, x2, y2] = obj.box;
      const boxW = x2 - x1;
      const boxH = y2 - y1;
      const dist = obj.estimated_meters;

      // Urgency color coding
      let color = "#10b981"; // Emerald for safe / far
      if (dist <= 1.4) {
        color = "#f43f5e"; // Rose / Red for immediate hazard
      } else if (dist <= 3.0) {
        color = "#f59e0b"; // Amber for approaching hazard
      }

      this.ctx.save();
      // Glowing outline
      this.ctx.strokeStyle = color;
      this.ctx.lineWidth = 3;
      this.ctx.shadowColor = color;
      this.ctx.shadowBlur = 10;
      this.ctx.strokeRect(x1, y1, boxW, boxH);

      // Label Pill
      const label = `${obj.class_name.toUpperCase()} • ${dist}m (${obj.bearing})`;
      this.ctx.font = "bold 13px Outfit, sans-serif";
      const textMetrics = this.ctx.measureText(label);
      const textW = textMetrics.width;

      this.ctx.shadowBlur = 0;
      this.ctx.fillStyle = "rgba(10, 13, 20, 0.85)";
      this.ctx.fillRect(x1, Math.max(0, y1 - 24), textW + 16, 24);

      this.ctx.fillStyle = color;
      this.ctx.fillText(label, x1 + 8, Math.max(16, y1 - 7));
      this.ctx.restore();
    }
  }

  updateObjectsList(objects) {
    if (!this.objectsList) return;
    if (this.objectsCount) this.objectsCount.textContent = objects.length;
    
    if (objects.length === 0) {
      this.objectsList.innerHTML = `<div class="empty-state"><p>Path clear. No obstacles detected.</p></div>`;
      return;
    }

    let html = "";
    for (const obj of objects) {
      const isClose = obj.estimated_meters <= 1.5;
      html += `
        <div class="object-pill">
          <span class="obj-name">${obj.class_name}</span>
          <div class="obj-meta">
            <span class="bearing-tag">${obj.bearing}</span>
            <span class="dist-tag ${isClose ? 'close' : ''}">${obj.estimated_meters}m</span>
          </div>
        </div>
      `;
    }
    this.objectsList.innerHTML = html;
  }

  addAlertToLog(alertText) {
    if (!this.alertsLog) return;
    const emptyPlaceholder = document.getElementById("empty-alerts-placeholder");
    if (emptyPlaceholder) {
      emptyPlaceholder.remove();
    }

    this.totalAlertsCount++;
    if (this.alertsCount) this.alertsCount.textContent = this.totalAlertsCount;

    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const isUrgent = alertText.toLowerCase().includes("caution") || alertText.includes("under 1 meter");

    const item = document.createElement("div");
    item.className = `alert-item ${isUrgent ? 'urgent' : ''}`;
    item.innerHTML = `
      <span class="alert-time">${timeStr}</span>
      <span class="alert-text">${alertText}</span>
    `;

    this.alertsLog.prepend(item);

    // Limit log size to 30 items
    if (this.alertsLog.children.length > 30) {
      this.alertsLog.removeChild(this.alertsLog.lastChild);
    }

    // Display visual toast
    if (this.voiceToastMsg && this.voiceToast) {
      this.voiceToastMsg.textContent = alertText;
      this.voiceToast.style.display = "flex";
      clearTimeout(this.toastTimeout);
      this.toastTimeout = setTimeout(() => {
        this.voiceToast.style.display = "none";
      }, 3500);
    }
  }

  speakAlert(text) {
    if (!window.speechSynthesis) return;

    // Prevent immediate stutter repeats
    const now = Date.now();
    if (text === this.lastSpokenText && (now - this.lastSpokenTime) < 2500) {
      return;
    }
    this.lastSpokenText = text;
    this.lastSpokenTime = now;

    // Cancel pending utterances for immediate responsiveness
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = this.speechRate;
    utterance.pitch = 1.0;
    
    // Choose high quality English voice if available
    const voices = window.speechSynthesis.getVoices();
    const naturalVoice = voices.find(v => v.lang.startsWith("en") && (v.name.includes("Natural") || v.name.includes("Google") || v.name.includes("Siri")));
    if (naturalVoice) {
      utterance.voice = naturalVoice;
    }

    window.speechSynthesis.speak(utterance);
  }

  async handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    if (this.connStatus) this.connStatus.textContent = "Analyzing image...";
    
    // Switch display to uploaded photo preview
    if (this.stream) {
      this.stream.getTracks().forEach(t => t.stop());
      this.stream = null;
    }
    this.isStreaming = false;

    const objectUrl = URL.createObjectURL(file);
    if (this.previewImg) {
      this.previewImg.src = objectUrl;
      this.previewImg.style.display = "block";
    }
    if (this.video) {
      this.video.style.display = "none";
    }
    if (this.idleCover) {
      this.idleCover.style.display = "none";
    }

    // Update canvas size once image dimensions load
    this.previewImg.onload = () => {
      this.canvas.width = this.previewImg.naturalWidth;
      this.canvas.height = this.previewImg.naturalHeight;
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    };

    const formData = new FormData();
    formData.append("file", file);
    const confVal = this.confSlider ? (parseInt(this.confSlider.value) / 100).toString() : "0.40";
    formData.append("confidence", confVal);
    formData.append("return_depth_map", "true");

    try {
      const targetUrl = this.backendUrl ? `${this.backendUrl}/api/process-frame` : "/api/process-frame";
      const res = await fetch(targetUrl, {
        method: "POST",
        body: formData
      });
      if (!res.ok) throw new Error("HTTP error " + res.status);
      const data = await res.json();

      if (data.frame_size) {
        this.canvas.width = data.frame_size.width;
        this.canvas.height = data.frame_size.height;
      }

      if (data.depth_colormap_base64) {
        data.depth_map = `data:image/jpeg;base64,${data.depth_colormap_base64}`;
      }

      if (this.connStatus) this.connStatus.textContent = "Analysis Complete";
      this.handleInferenceResult(data);
    } catch (err) {
      console.error("Image processing error:", err);
      alert(`Processing error: ${err.message}`);
      if (this.connStatus) this.connStatus.textContent = "Error processing image";
    }
  }
}

// Initialize when DOM is loaded
window.addEventListener("DOMContentLoaded", () => {
  window.seeForMeApp = new SeeForMeApp();
});
