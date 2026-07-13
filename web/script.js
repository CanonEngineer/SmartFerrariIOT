(() => {
  const $ = (sel) => document.querySelector(sel);
  const logList = $("#log-list");
  const expList = $("#exp-list");
  let ws, reconnectTimer, gpsAngle = 0;
  let lastVision = 0;
  let prevAudio = { engine: false, alarm: false, horn: false, lock: true };
  let audioPrimed = false;
  let hornTimer = null;
  let wheelsSpinning = false;

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

  function triggerHornVisual() {
    const car = $("#car");
    if (!car) return;
    car.classList.add("horn-blast");
    clearTimeout(hornTimer);
    hornTimer = setTimeout(() => car.classList.remove("horn-blast"), 600);
  }

  function setBtnActive(id, on) {
    const el = document.getElementById(id);
    if (el) el.classList.toggle("active-on", !!on);
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

  function applyTelemetry(tel) {
    if (!tel) return;
    $("#r-sqi").textContent = Number(tel.sync_quality_index ?? 0).toFixed(1);
    $("#sqi-status").textContent = `SQI ${Number(tel.sync_quality_index ?? 0).toFixed(0)}`;
    $("#r-p50").textContent = tel.command_latency_ms?.p50 == null ? "—" : `${tel.command_latency_ms.p50} ms`;
  }

  function applyState(state, telemetry) {
    if (!state) return;
    const s = state.sensors || {};
    const a = state.actuators || {};
    const boards = state.boards || {};

    $("#m-rpm").textContent = `${Math.round(s.rpm ?? 0)}`;
    $("#m-speed").textContent = `${Number(s.speed_kmh ?? 0).toFixed(0)} km/h`;
    $("#m-temp").textContent = `${Number(s.engine_temp ?? 0).toFixed(0)}°C`;
    $("#m-fuel").textContent = `${Number(s.fuel ?? 0).toFixed(0)}%`;
    $("#last-event").textContent = state.last_event || "—";
    const synced = boards.arduino?.sync && boards.raspberry?.sync;
    $("#sync-status").textContent = synced ? `SYNC OK #${state.sync_pulse ?? 0}` : "SYNC OFF";
    if (typeof state.sync_quality_index === "number") {
      $("#sqi-status").textContent = `SQI ${state.sync_quality_index.toFixed(0)}`;
      $("#r-sqi").textContent = state.sync_quality_index.toFixed(1);
    }

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
    // SMIL wheel spin — só liga/desliga na transição
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

    if (state.twin) $("#r-twin").textContent = state.twin.mode || "—";
    if (state.energy) {
      $("#r-power").textContent = `${Number(state.energy.power_w || 0).toFixed(0)} W`;
      $("#energy-stats").textContent =
        `Energia P=${state.energy.power_w}W · bat=${state.energy.battery_pct}% · fuel=${state.energy.fuel_pct}%`;
    }
    if (state.hil) {
      const q = state.hil.qos || {};
      $("#hil-stats").textContent =
        `QoS sent=${q.sent} del=${q.delivered} drop=${q.dropped} ratio=${q.delivery_ratio}` +
        (q.mean_latency_ms != null ? ` · lat=${q.mean_latency_ms}ms` : "") +
        ` · ${q.consistency}`;
      drawQosChart(state.hil.recent || []);
    }
    if (state.audit_tip) {
      $("#audit-stats").textContent = `Audit tip ${String(state.audit_tip).slice(0, 18)}…`;
    }

    syncAudio(a, s);
    if (telemetry) applyTelemetry(telemetry);
  }

  function send(payload) {
    FerrariAudio.resume();
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(payload));
      return;
    }
    const map = {
      door: "/api/door", roof: "/api/roof", engine: "/api/engine", sound: "/api/sound",
      headlight: "/api/headlight", track: "/api/track", alarm: "/api/alarm", spoiler: "/api/spoiler",
      climate: "/api/climate", horn: "/api/horn", sport: "/api/sport", lock: "/api/lock",
      simulate: "/api/simulate",
    };
    const url = map[payload.action];
    if (!url) return;
    const body = { ...payload };
    delete body.action;
    if (payload.action === "simulate") body.scenario = payload.scenario;
    fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(async (r) => {
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail?.message || data.detail || r.statusText);
        if (data.state) applyState(data.state);
        pushLog(payload.action);
      })
      .catch((e) => pushLog(`BLOQUEADO: ${e.message || e}`));
  }

  function connectWs() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/api/ws`);
    ws.onopen = () => { setPill($("#ws-status"), true, "WS online", "WS offline"); pushLog("WebSocket conectado"); };
    ws.onclose = () => {
      setPill($("#ws-status"), false, "WS online", "WS offline");
      reconnectTimer = setTimeout(connectWs, 1500);
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "state") {
          applyState(msg.data);
          if (msg.data?.last_event) pushLog(msg.data.last_event);
        } else if (msg.type === "invariant_violation") {
          pushLog(`INV ${msg.invariant}: ${msg.message}`);
        } else if (msg.type === "error") {
          pushLog(`Erro: ${msg.message}`);
        }
      } catch (_) {}
    };
  }

  document.querySelectorAll("button[data-action]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const action = btn.dataset.action;
      const payload = { action };
      if (action === "door") {
        payload.door_id = btn.dataset.door;
        payload.open = btn.dataset.open === "true";
      } else {
        payload.on = btn.dataset.on === "true";
      }
      // Immediate feedback for horn / alarm sound (before WS round-trip)
      if (action === "horn" && payload.on) {
        FerrariAudio.resume();
        FerrariAudio.horn();
        triggerHornVisual();
      }
      if (action === "alarm" && payload.on) {
        FerrariAudio.resume();
        FerrariAudio.setAlarm(true);
        prevAudio.alarm = true;
      }
      if (action === "alarm" && !payload.on) {
        FerrariAudio.setAlarm(false);
        prevAudio.alarm = false;
      }
      if (action === "lock") {
        FerrariAudio.resume();
        if (payload.on) FerrariAudio.lockClick();
        else FerrariAudio.unlockClick();
        prevAudio.lock = !!payload.on;
      }
      send(payload);
    });
  });

  $("#btn-both-doors-open")?.addEventListener("click", () => {
    send({ action: "door", door_id: "driver", open: true });
    setTimeout(() => send({ action: "door", door_id: "passenger", open: true }), 120);
    pushLog("Abrir ambas as portas");
  });
  $("#btn-both-doors-close")?.addEventListener("click", () => {
    send({ action: "door", door_id: "driver", open: false });
    setTimeout(() => send({ action: "door", door_id: "passenger", open: false }), 120);
    pushLog("Fechar ambas as portas");
  });

  document.querySelectorAll("button[data-scenario]").forEach((btn) => {
    btn.addEventListener("click", () => {
      send({ action: "simulate", scenario: btn.dataset.scenario });
      pushLog(`Cenário: ${btn.dataset.scenario}`);
    });
  });

  document.querySelectorAll("button[data-experiment]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const name = btn.dataset.experiment;
      pushLog(`Experimento: ${name}`);
      fetch("/api/research/experiments/run", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, params: {} }),
      })
        .then((r) => r.json())
        .then((data) => {
          if (!data.ok) throw new Error("falha");
          const id = data.result.experiment_id;
          const li = document.createElement("li");
          li.innerHTML = `<strong>${name}</strong> · SQI ${data.result.metrics?.sync_quality_index ?? "—"} ·
            <a href="/api/research/experiments/${id}/export.csv" target="_blank">CSV</a>`;
          expList.prepend(li);
          applyTelemetry(data.result.metrics);
        })
        .catch((e) => pushLog(`Exp falhou: ${e.message || e}`));
    });
  });

  $("#hil-enable")?.addEventListener("click", () => {
    const delay_ms = Number($("#hil-delay").value || 0);
    const loss_rate = Number($("#hil-loss").value || 0) / 100;
    fetch("/api/research/hil", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: true, delay_ms, loss_rate }),
    }).then((r) => r.json()).then((d) => {
      pushLog(`HIL ON delay=${d.delay_ms} loss=${d.loss_rate}`);
      $("#hil-stats").textContent = `QoS ratio=${d.qos.delivery_ratio}`;
    });
  });
  $("#hil-disable")?.addEventListener("click", () => {
    fetch("/api/research/hil", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: false, delay_ms: 0, loss_rate: 0 }),
    }).then(() => pushLog("HIL OFF"));
  });

  $("#btn-paper")?.addEventListener("click", () => {
    fetch("/api/research/paper-pack", { method: "POST" })
      .then((r) => r.json())
      .then(() => { pushLog("Paper pack gerado"); window.open("/api/research/paper-pack.tex", "_blank"); });
  });

  FerrariVision.setHandler((ev) => {
    const now = Date.now();
    if (now - lastVision < 2500) return;
    lastVision = now;
    pushLog(`Visão: ${ev.kind} (${ev.detail})`);
    fetch("/api/research/vision/event", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(ev),
    }).then((r) => r.json()).then((d) => { if (d.state) applyState(d.state); });
  });

  $("#vision-start")?.addEventListener("click", async () => {
    try {
      await FerrariAudio.resume();
      await FerrariVision.start($("#vision-video"), $("#vision-canvas"));
      pushLog("Webcam ativa");
    } catch (e) {
      pushLog(`Webcam: ${e.message || e}`);
    }
  });
  $("#vision-stop")?.addEventListener("click", () => { FerrariVision.stop(); pushLog("Webcam off"); });

  fetch("/api/status").then((r) => r.json()).then((d) => applyState(d.state, d.telemetry)).catch(() => pushLog("Falha status"));
  fetch("/api/research/telemetry").then((r) => r.json()).then(applyTelemetry).catch(() => {});
  connectWs();
  setInterval(() => fetch("/api/research/telemetry").then((r) => r.json()).then(applyTelemetry).catch(() => {}), 2500);
  setInterval(drawSpectrum, 80);
})();
