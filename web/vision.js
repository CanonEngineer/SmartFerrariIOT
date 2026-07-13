/**
 * Visão computacional leve: gesto de partida (movimento) + QR (jsQR via CDN se disponível).
 */
const FerrariVision = (() => {
  let stream, video, canvas, ctx, running = false, lastGray = null;
  let onEvent = () => {};

  function setHandler(fn) { onEvent = fn; }

  async function start(videoEl, canvasEl) {
    video = videoEl; canvas = canvasEl; ctx = canvas.getContext("2d", { willReadFrequently: true });
    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false });
    video.srcObject = stream;
    await video.play();
    running = true;
    loop();
  }

  function stop() {
    running = false;
    if (stream) stream.getTracks().forEach((t) => t.stop());
    stream = null;
  }

  function loop() {
    if (!running) return;
    const w = 320, h = 240;
    canvas.width = w; canvas.height = h;
    ctx.drawImage(video, 0, 0, w, h);
    const img = ctx.getImageData(0, 0, w, h);
    detectMotion(img);
    detectQR(img);
    requestAnimationFrame(loop);
  }

  function detectMotion(img) {
    const data = img.data;
    let sum = 0, n = 0;
    const gray = new Float32Array(img.width * img.height);
    for (let i = 0, p = 0; i < data.length; i += 4, p++) {
      gray[p] = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
    }
    if (lastGray && lastGray.length === gray.length) {
      for (let i = 0; i < gray.length; i += 8) {
        sum += Math.abs(gray[i] - lastGray[i]);
        n++;
      }
      const motion = sum / n;
      if (motion > 28) {
        onEvent({ kind: "gesture_start", confidence: Math.min(1, motion / 60), detail: `motion=${motion.toFixed(1)}` });
      }
    }
    lastGray = gray;
  }

  function detectQR(img) {
    if (typeof jsQR !== "function") return;
    const code = jsQR(img.data, img.width, img.height, { inversionAttempts: "dontInvert" });
    if (code && /track|ferrari|gps/i.test(code.data)) {
      onEvent({ kind: "qr_track", confidence: 1, detail: code.data });
    }
  }

  return { start, stop, setHandler };
})();
