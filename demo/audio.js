/**
 * Web Audio Lab — buzina, sirene, ronco (RPM), clique de trava + espectro.
 */
const FerrariAudio = (() => {
  let ctx, master, analyser, engineOsc, engineGain, alarmNodes = [], dataArray;
  let engineOn = false, alarmOn = false;

  function ensure() {
    if (ctx) return;
    ctx = new (window.AudioContext || window.webkitAudioContext)();
    master = ctx.createGain();
    master.gain.value = 0.4;
    analyser = ctx.createAnalyser();
    analyser.fftSize = 256;
    dataArray = new Uint8Array(analyser.frequencyBinCount);
    master.connect(analyser);
    analyser.connect(ctx.destination);
  }

  async function resume() {
    ensure();
    if (ctx.state === "suspended") await ctx.resume();
  }

  function beep(freq, dur, type = "square", gain = 0.2, slideTo = null) {
    ensure();
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = type;
    o.frequency.value = freq;
    if (slideTo != null) {
      o.frequency.setValueAtTime(freq, ctx.currentTime);
      o.frequency.exponentialRampToValueAtTime(Math.max(40, slideTo), ctx.currentTime + dur);
    }
    g.gain.value = gain;
    o.connect(g); g.connect(master);
    o.start();
    g.gain.setValueAtTime(gain, ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + dur);
    o.stop(ctx.currentTime + dur + 0.03);
  }

  /** Dual-tone car horn */
  function horn() {
    resume();
    const t = ctx.currentTime;
    // fundamental + fifth
    [380, 480].forEach((f, i) => {
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.type = "sawtooth";
      o.frequency.value = f;
      g.gain.value = 0.001;
      o.connect(g); g.connect(master);
      o.start(t);
      g.gain.exponentialRampToValueAtTime(0.22 - i * 0.04, t + 0.02);
      g.gain.setValueAtTime(0.2 - i * 0.04, t + 0.28);
      g.gain.exponentialRampToValueAtTime(0.001, t + 0.55);
      o.stop(t + 0.58);
    });
    // short echo blip
    setTimeout(() => beep(360, 0.12, "sawtooth", 0.12), 120);
  }

  function lockClick() {
    resume();
    beep(1900, 0.035, "square", 0.14);
    setTimeout(() => beep(950, 0.05, "triangle", 0.1), 45);
    setTimeout(() => beep(1400, 0.03, "square", 0.08), 110);
  }

  function unlockClick() {
    resume();
    beep(900, 0.04, "triangle", 0.1);
    setTimeout(() => beep(1600, 0.05, "square", 0.12), 60);
  }

  /** Alternating police-style siren while armed */
  function setAlarm(on) {
    resume();
    alarmOn = on;
    alarmNodes.forEach((n) => { try { n.stop(); } catch (_) {} });
    alarmNodes = [];
    if (!on || !ctx) return;

    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = "square";
    o.frequency.value = 780;
    g.gain.value = 0.14;
    o.connect(g); g.connect(master);
    o.start();

    // Sweep siren via LFO on frequency
    const lfo = ctx.createOscillator();
    const lfoGain = ctx.createGain();
    lfo.type = "triangle";
    lfo.frequency.value = 2.2;
    lfoGain.gain.value = 220;
    lfo.connect(lfoGain);
    lfoGain.connect(o.frequency);
    lfo.start();

    const o2 = ctx.createOscillator();
    const g2 = ctx.createGain();
    o2.type = "sawtooth";
    o2.frequency.value = 980;
    g2.gain.value = 0.07;
    o2.connect(g2); g2.connect(master);
    o2.start();
    const lfo2 = ctx.createOscillator();
    const lfo2g = ctx.createGain();
    lfo2.frequency.value = 2.2;
    lfo2g.gain.value = 180;
    lfo2.connect(lfo2g); lfo2g.connect(o2.frequency);
    lfo2.start();

    alarmNodes = [o, lfo, o2, lfo2];
  }

  function setEngine(on, rpm = 1200) {
    resume();
    engineOn = on;
    if (!on) {
      if (engineOsc) { try { engineOsc.stop(); } catch (_) {} engineOsc = null; }
      if (engineGain) { try { engineGain.disconnect(); } catch (_) {} engineGain = null; }
      return;
    }
    if (!engineOsc) {
      engineOsc = ctx.createOscillator();
      engineGain = ctx.createGain();
      engineOsc.type = "sawtooth";
      engineGain.gain.value = 0.05;
      engineOsc.connect(engineGain); engineGain.connect(master);
      engineOsc.start();
    }
    updateRpm(rpm);
  }

  function updateRpm(rpm) {
    if (!engineOn || !engineOsc || !ctx) return;
    const f = 45 + (Number(rpm) || 0) / 40;
    engineOsc.frequency.setTargetAtTime(f, ctx.currentTime, 0.08);
    if (engineGain) engineGain.gain.setTargetAtTime(0.04 + Math.min(0.12, rpm / 20000), ctx.currentTime, 0.1);
  }

  function getSpectrum() {
    if (!analyser || !dataArray) return [];
    analyser.getByteFrequencyData(dataArray);
    return Array.from(dataArray);
  }

  return { resume, horn, lockClick, unlockClick, setAlarm, setEngine, updateRpm, getSpectrum };
})();
