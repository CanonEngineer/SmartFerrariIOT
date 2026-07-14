/**
 * Demo Lab standalone (GitHub Pages) — simulação 100% no browser.
 * Não depende do backend Python; ideal para botão "Abrir Interface" no README.
 */
(() => {
  const $ = (sel) => document.querySelector(sel);
  const logList = $("#log-list");
  const expList = $("#exp-list");
  let gpsAngle = 0;
  let prevAudio = { engine: false, alarm: false, horn: false, lock: true };
  let audioPrimed = false;
  let hornTimer = null;
  let wheelsSpinning = false;
  let hil = { enabled: false, delay_ms: 0, loss_rate: 0, recent: [], sent: 0, delivered: 0, dropped: 0 };
  let syncPulse = 0;
  let sqi = 94;

  const state = {
    sensors: {
      rpm: 800, speed_kmh: 0, engine_temp: 78, battery: 92, fuel: 68,
      lat: -23.5505, lon: -46.6333, power_w: 0,
    },
    actuators: {
      door: { driver: false, passenger: false },
      roof: false, engine: false, sound: false, headlight: false,
      tracking: false, alarm: false, spoiler: false, climate: false,
      horn: false, sport_mode: false, lock: true,
    },
    boards: {
      arduino: { online: true, sync: true },
      raspberry: { online: true, sync: true },
    },
    last_event: "Demo Lab (modo browser)",
    sync_pulse: 0,
    sync_quality_index: 94,
    twin: { mode: "IDLE" },
    energy: { power_w: 0, battery_pct: 92, fuel_pct: 68 },
    hil: { qos: { sent: 0, delivered: 0, dropped: 0, delivery_ratio: 1, mean_latency_ms: 0, consistency: "ok" }, recent: [] },
    audit_tip: "demo" + Math.random().toString(16).slice(2, 10),
  };

  function pushLog(text) {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${new Date().toLocaleTimeString()}</strong> — ${text}`;
    logList.prepend(li);
    while (logList.children.length > 40) logList.removeChild(logList.lastChild);
  }

  function setPill(el, online, onText, offText) {
    el.classList.toggle("online", online);
    el.classList.toggle("offline", !online);
    el.textContent = online ? onText : offText;
  }

  function setBtnActive(id, on) {
    const el = document.getElementById(id);
    if (el) el.classList.toggle("active-on", !!on);
  }

  function triggerHornVisual() {
    const car = $("#car");
    if (!car) return;
    car.classList.add("horn-blast");
    clearTimeout(hornTimer);
    hornTimer = setTimeout(() => car.classList.remove("horn-blast"), 600);
  }

  function drawSpectrum() {
    const canvas = $("#spectrum");
    if (!canvas || !window.FerrariAudio) return;
    const ctx = canvas.getContext("2d");
    const data = FerrariAudio.getSpectrum();
    const w = canvas.width, h = canvas.height;
    ctx.fillStyle = "#0a0a0b";
    ctx.fillRect(0, 0, w, h);
    if (!data.length) return;
    const barW = w / data.length;
    for (let i = 0; i < data.length; i++) {
      const bh = (data[i] / 255) * (h - 4);
      ctx.fillStyle = i % 3 === 0 ? "#e10600" : "#f5c518";
      ctx.fillRect(i * barW, h - bh, Math.max(1, barW - 1), bh);
    }
  }

  function drawQosChart(recent) {
    const canvas = $("#qos-chart");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width, h = canvas.height;
    ctx.fillStyle = "#0a0a0b";
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = "#8a8580";
    ctx.font = "11px sans-serif";
    ctx.fillText("HIL latency (ms) · vermelho = drop", 8, 14);
    if (!recent.length) return;
    const lats = recent.map((e) => (e.status === "DROPPED" ? null : Number(e.latency_ms || 0)));
    const max = Math.max(1, ...lats.filter((x) => x != null));
    const step = w / Math.max(1, recent.length - 1);
    ctx.beginPath();
    let started = false;
    recent.forEach((e, i) => {
      const x = i * step;
      if (e.status === "DROPPED") {
        ctx.fillStyle = "#e10600";
        ctx.fillRect(x - 2, 20, 4, h - 28);
        started = false;
        return;
      }
      const y = h - 8 - ((e.latency_ms || 0) / max) * (h - 30);
      if (!started) { ctx.moveTo(x, y); started = true; }
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = "#f5c518";
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }

  function syncAudio(a, s) {
    if (!window.FerrariAudio) return;
    if (!audioPrimed) {
      prevAudio = {
        engine: !!a.engine, alarm: !!a.alarm, horn: !!a.horn, lock: !!a.lock,
      };
      audioPrimed = true;
      return;
    }
    if (a.engine !== prevAudio.engine) FerrariAudio.setEngine(!!a.engine, s.rpm || 1200);
    if (a.engine) FerrariAudio.updateRpm(s.rpm || 0);
    if (a.alarm !== prevAudio.alarm) FerrariAudio.setAlarm(!!a.alarm);
    if (a.horn && !prevAudio.horn) {
      FerrariAudio.horn();
      triggerHornVisual();
    }
    if (a.lock !== prevAudio.lock) {
      if (a.lock) FerrariAudio.lockClick();
      else FerrariAudio.unlockClick();
    }
    prevAudio = {
      engine: !!a.engine, alarm: !!a.alarm, horn: !!a.horn, lock: !!a.lock,
    };
  }

  function applyTelemetry() {
    $("#r-sqi").textContent = sqi.toFixed(1);
    $("#sqi-status").textContent = `SQI ${sqi.toFixed(0)}`;
    $("#r-p50").textContent = `${(6 + Math.random() * 5).toFixed(1)} ms`;
  }

  function applyState() {
    const s = state.sensors;
    const a = state.actuators;
    const boards = state.boards;

    $("#m-rpm").textContent = `${Math.round(s.rpm ?? 0)}`;
    $("#m-speed").textContent = `${Number(s.speed_kmh ?? 0).toFixed(0)} km/h`;
    $("#m-temp").textContent = `${Number(s.engine_temp ?? 0).toFixed(0)}°C`;
    $("#m-fuel").textContent = `${Number(s.fuel ?? 0).toFixed(0)}%`;
    $("#last-event").textContent = state.last_event || "—";
    const synced = boards.arduino?.sync && boards.raspberry?.sync;
    $("#sync-status").textContent = synced ? `SYNC OK #${state.sync_pulse ?? 0}` : "SYNC OFF";
    $("#sqi-status").textContent = `SQI ${sqi.toFixed(0)}`;
    $("#r-sqi").textContent = sqi.toFixed(1);

    $("#door-driver").classList.toggle("open", !!a.door?.driver);
    $("#door-passenger").classList.toggle("open", !!a.door?.passenger);
    $("#roof-panel").classList.toggle("open", !!a.roof);
    document.querySelectorAll(".roof-panel").forEach((el) => el.classList.toggle("open", !!a.roof));
    $("#spoiler").classList.toggle("out", !!a.spoiler);

    const car = $("#car");
    if (car) {
      car.classList.toggle("engine-on", !!a.engine);
      car.classList.toggle("sport-on", !!a.sport_mode);
      car.classList.toggle("climate-on", !!a.climate);
      car.classList.toggle("locked", !!a.lock);
      car.classList.toggle("alarm-on", !!a.alarm);
    }
    if (!!a.engine !== wheelsSpinning) {
      wheelsSpinning = !!a.engine;
      document.querySelectorAll(".wheel-spin").forEach((anim) => {
        try {
          if (wheelsSpinning) anim.beginElement();
          else anim.endElement();
        } catch (_) {}
      });
    }
    const climateLabel = $("#climate-label");
    if (climateLabel) climateLabel.setAttribute("opacity", a.climate ? "0.95" : "0.15");

    setBtnActive("btn-sport-on", !!a.sport_mode);
    setBtnActive("btn-spoiler-on", !!a.spoiler);
    setBtnActive("btn-ac-on", !!a.climate);
    setBtnActive("btn-lock", !!a.lock);
    setBtnActive("btn-alarm-on", !!a.alarm);

    const hl = a.headlight ? "#ffe082" : "#3d3428";
    $("#hl-left").setAttribute("fill", hl);
    $("#hl-right").setAttribute("fill", a.headlight ? "#ffe082" : "#3d3428");
    const beam = $("#hl-beam");
    if (beam) beam.setAttribute("opacity", a.headlight ? "0.55" : "0");
    if (a.headlight) {
      $("#hl-left").setAttribute("filter", "url(#glow)");
      $("#hl-right").setAttribute("filter", "url(#glow)");
    } else {
      $("#hl-left").removeAttribute("filter");
      $("#hl-right").removeAttribute("filter");
    }
    const tail = $("#taillight");
    if (tail) tail.setAttribute("fill", a.engine ? "#ff1744" : "#5a0000");

    $("#exhaust").setAttribute("opacity", a.engine ? "0.85" : "0.12");
    $("#sound-waves").setAttribute("opacity", a.sound ? "0.95" : "0");
    $("#gps-dot").setAttribute("opacity", a.tracking ? "1" : "0.15");

    if (a.tracking) {
      gpsAngle += 0.12;
      $("#gps-dot").setAttribute("cx", 70 + 62 * Math.cos(gpsAngle));
      $("#gps-dot").setAttribute("cy", 55 + 32 * Math.sin(gpsAngle));
    }

    $("#arduino-status-text").textContent = boards.arduino?.online ? "ONLINE" : "OFFLINE";
    $("#raspberry-status-text").textContent = boards.raspberry?.online ? "ONLINE" : "OFFLINE";
    $("#sync-line").setAttribute("opacity", synced ? "0.85" : "0.15");
    $("#sync-dot").style.display = synced ? "block" : "none";

    state.twin.mode = a.alarm ? "SECURE" : a.engine ? (a.sport_mode ? "SPORT" : "RUNNING") : a.lock ? "IDLE" : "READY";
    $("#r-twin").textContent = state.twin.mode;
    const power = a.engine ? (a.sport_mode ? 420 : 180) + (a.headlight ? 40 : 0) + (a.climate ? 60 : 0) : (a.lock ? 8 : 15);
    state.energy.power_w = power;
    state.sensors.power_w = power;
    $("#r-power").textContent = `${power} W`;
    $("#energy-stats").textContent =
      `Energia P=${power}W · bat=${state.sensors.battery}% · fuel=${Number(state.sensors.fuel).toFixed(0)}%`;

    const q = {
      sent: hil.sent, delivered: hil.delivered, dropped: hil.dropped,
      delivery_ratio: hil.sent ? (hil.delivered / hil.sent).toFixed(2) : "1.00",
      mean_latency_ms: hil.enabled ? hil.delay_ms + Math.round(Math.random() * 8) : 4,
      consistency: hil.enabled && hil.loss_rate > 0.2 ? "degraded" : "ok",
    };
    $("#hil-stats").textContent =
      `QoS sent=${q.sent} del=${q.delivered} drop=${q.dropped} ratio=${q.delivery_ratio}` +
      ` · lat=${q.mean_latency_ms}ms · ${q.consistency}`;
    drawQosChart(hil.recent);
    $("#audit-stats").textContent = `Audit tip ${String(state.audit_tip).slice(0, 18)}…`;

    syncAudio(a, s);
    applyTelemetry();
  }

  function pulse(event) {
    syncPulse = (syncPulse + 1) % 1000;
    state.sync_pulse = syncPulse;
    state.last_event = event;
    state.sync_quality_index = sqi;
    hil.sent += 1;
    const drop = hil.enabled && Math.random() < hil.loss_rate;
    if (drop) {
      hil.dropped += 1;
      hil.recent.push({ status: "DROPPED", latency_ms: 0 });
    } else {
      hil.delivered += 1;
      const lat = (hil.enabled ? hil.delay_ms : 0) + 3 + Math.random() * 10;
      hil.recent.push({ status: "OK", latency_ms: lat });
    }
    if (hil.recent.length > 40) hil.recent.shift();
    sqi = Math.max(55, Math.min(99, sqi + (Math.random() * 3 - 1)));
    pushLog(event);
    applyState();
  }

  function applyAction(payload) {
    const a = state.actuators;
    const s = state.sensors;
    if (payload.action === "door") {
      a.door[payload.door_id] = !!payload.open;
      if (payload.open) a.lock = false;
    }
    if (payload.action === "roof") a.roof = !!payload.on;
    if (payload.action === "engine") {
      a.engine = !!payload.on;
      if (a.engine) {
        a.alarm = false;
        a.lock = false;
        s.rpm = a.sport_mode ? 4200 : 1800;
        s.speed_kmh = a.sport_mode ? 95 : 35;
      } else {
        s.rpm = 800;
        s.speed_kmh = 0;
        a.sport_mode = false;
      }
    }
    if (payload.action === "sound") a.sound = !!payload.on;
    if (payload.action === "headlight") a.headlight = !!payload.on;
    if (payload.action === "track") a.tracking = !!payload.on;
    if (payload.action === "alarm") {
      a.alarm = !!payload.on;
      if (a.alarm) {
        a.engine = false;
        a.lock = true;
        s.rpm = 800;
        s.speed_kmh = 0;
      }
    }
    if (payload.action === "spoiler") a.spoiler = !!payload.on;
    if (payload.action === "climate") a.climate = !!payload.on;
    if (payload.action === "horn") {
      a.horn = true;
      if (window.FerrariAudio) { FerrariAudio.resume(); FerrariAudio.horn(); }
      triggerHornVisual();
      setTimeout(() => { a.horn = false; }, 400);
    }
    if (payload.action === "sport") {
      a.sport_mode = !!payload.on;
      if (a.sport_mode && a.engine) {
        a.spoiler = true;
        s.rpm = 4500;
        s.speed_kmh = 120;
      }
    }
    if (payload.action === "lock") {
      a.lock = !!payload.on;
      if (a.lock) {
        a.door.driver = false;
        a.door.passenger = false;
      }
    }
    if (payload.action === "simulate") runScenario(payload.scenario);
    else pulse(payload.action === "door"
      ? `Porta ${payload.door_id} ${payload.open ? "aberta" : "fechada"}`
      : `${payload.action} → ${payload.on}`);
  }

  function runScenario(name) {
    const a = state.actuators;
    const s = state.sensors;
    if (name === "startup") {
      a.alarm = false; a.lock = false; a.engine = true; a.headlight = true; a.sound = true;
      s.rpm = 2200; s.speed_kmh = 40;
    } else if (name === "track_day") {
      a.alarm = false; a.engine = true; a.sport_mode = true; a.spoiler = true;
      a.tracking = true; a.roof = true; a.lock = false;
      s.rpm = 5200; s.speed_kmh = 145;
    } else if (name === "valet") {
      a.engine = false; a.door.driver = true; a.climate = true; a.sound = true; a.lock = false;
      s.rpm = 800; s.speed_kmh = 0;
    } else if (name === "secure") {
      a.engine = false; a.roof = false; a.door.driver = false; a.door.passenger = false;
      a.lock = true; a.alarm = true; a.headlight = false; a.sound = false; a.tracking = false;
      a.sport_mode = false; a.spoiler = false;
      s.rpm = 800; s.speed_kmh = 0;
    } else if (name === "sync_test") {
      let n = 0;
      const tick = () => {
        a.headlight = !a.headlight;
        n += 1;
        state.boards.arduino.sync = true;
        state.boards.raspberry.sync = true;
        pulse(`Sync test #${n}`);
        if (n < 8) setTimeout(tick, 280);
      };
      tick();
      return;
    }
    pulse(`Cenário ${name}`);
  }

  function runExperiment(name) {
    if (name === "fault_injection") sqi = 58;
    if (name === "sync_latency") sqi = 96;
    if (name === "actuator_chain") {
      applyAction({ action: "engine", on: true });
      setTimeout(() => applyAction({ action: "headlight", on: true }), 200);
      setTimeout(() => applyAction({ action: "spoiler", on: true }), 400);
    }
    if (name === "tracking_stability") applyAction({ action: "track", on: true });
    const id = Math.random().toString(16).slice(2, 8);
    const li = document.createElement("li");
    li.innerHTML = `<strong>${name}</strong> · SQI ${sqi.toFixed(0)} · demo-id ${id}`;
    expList.prepend(li);
    pulse(`Experimento ${name}`);
  }

  document.querySelectorAll("button[data-action]").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (window.FerrariAudio) FerrariAudio.resume();
      const action = btn.dataset.action;
      const payload = { action };
      if (action === "door") {
        payload.door_id = btn.dataset.door;
        payload.open = btn.dataset.open === "true";
      } else {
        payload.on = btn.dataset.on === "true";
      }
      applyAction(payload);
    });
  });

  $("#btn-both-doors-open")?.addEventListener("click", () => {
    applyAction({ action: "door", door_id: "driver", open: true });
    setTimeout(() => applyAction({ action: "door", door_id: "passenger", open: true }), 120);
  });
  $("#btn-both-doors-close")?.addEventListener("click", () => {
    applyAction({ action: "door", door_id: "driver", open: false });
    setTimeout(() => applyAction({ action: "door", door_id: "passenger", open: false }), 120);
  });

  document.querySelectorAll("button[data-scenario]").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (window.FerrariAudio) FerrariAudio.resume();
      runScenario(btn.dataset.scenario);
    });
  });

  document.querySelectorAll("button[data-experiment]").forEach((btn) => {
    btn.addEventListener("click", () => runExperiment(btn.dataset.experiment));
  });

  $("#hil-enable")?.addEventListener("click", () => {
    hil.enabled = true;
    hil.delay_ms = Number($("#hil-delay").value || 0);
    hil.loss_rate = Number($("#hil-loss").value || 0) / 100;
    pushLog(`HIL ON delay=${hil.delay_ms} loss=${hil.loss_rate}`);
    applyState();
  });
  $("#hil-disable")?.addEventListener("click", () => {
    hil.enabled = false;
    hil.delay_ms = 0;
    hil.loss_rate = 0;
    pushLog("HIL OFF");
    applyState();
  });

  $("#btn-paper")?.addEventListener("click", () => {
    const tex = [
      "% Ferrari Lab — Paper Pack (demo GitHub Pages)",
      "\\section{Sync Quality Index}",
      `SQI demo = ${sqi.toFixed(1)}`,
      "\\section{Audit}",
      `tip = ${state.audit_tip}`,
    ].join("\n");
    const blob = new Blob([tex], { type: "text/plain" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "ferrari-paper-pack-demo.tex";
    a.click();
    pushLog("Paper pack (demo) baixado");
  });

  $("#vision-start")?.addEventListener("click", () => {
    pushLog("Webcam: no Demo Lab use a versão local (start.ps1) para visão completa");
  });
  $("#vision-stop")?.addEventListener("click", () => pushLog("Webcam off"));

  // Sensor drift + heartbeat visual
  setInterval(() => {
    const t = Date.now() / 1000;
    const a = state.actuators;
    const s = state.sensors;
    if (a.engine) {
      s.rpm = (a.sport_mode ? 3800 : 1600) + 400 * Math.sin(t / 2);
      s.speed_kmh = Math.max(0, (a.sport_mode ? 90 : 30) + 15 * Math.sin(t / 3));
      s.engine_temp = 85 + 8 * Math.sin(t / 20);
      s.fuel = Math.max(5, s.fuel - 0.002);
    } else {
      s.rpm = 780 + 30 * Math.sin(t / 5);
      s.engine_temp = 72 + 3 * Math.sin(t / 30);
    }
    syncPulse++;
    state.sync_pulse = syncPulse % 1000;
    applyState();
  }, 1800);

  setPill($("#ws-status"), true, "DEMO online", "offline");
  pushLog("Demo Lab pronto (GitHub Pages)");
  applyState();
  setInterval(drawSpectrum, 80);
})();
