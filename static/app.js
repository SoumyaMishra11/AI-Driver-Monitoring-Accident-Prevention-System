const $ = (id) => document.getElementById(id);

const runningPill = $("runningPill");
const fpsPill = $("fpsPill");
const hint = $("hint");
const metricsEl = $("metrics");

const startBtn = $("startBtn");
const stopBtn = $("stopBtn");
const applyBtn = $("applyBtn");

const cameraIndex = $("cameraIndex");
const logEnabled = $("logEnabled");
const logPath = $("logPath");
const volume = $("volume");
const cooldown = $("cooldown");

const video = $("video");
const emptyState = $("emptyState");

function setHint(msg, kind) {
  hint.textContent = msg || "";
  hint.classList.remove("error", "ok");
  if (kind) hint.classList.add(kind);
}

function setRunningUI(running) {
  runningPill.textContent = running ? "Running" : "Stopped";
  runningPill.classList.toggle("pill-ok", running);
  runningPill.classList.toggle("pill-bad", !running);

  startBtn.disabled = running;
  stopBtn.disabled = !running;

  if (running) {
    // Bust cache so the browser restarts the MJPEG connection.
    video.src = "/video?ts=" + Date.now();
    emptyState.style.display = "none";
  } else {
    video.removeAttribute("src");
    emptyState.style.display = "flex";
  }
}

function renderMetrics(metrics) {
  if (!metrics) metrics = {};
  const chips = [
    ["FACE", metrics.face_detected ? "OK" : "NO"],
    ["EAR", (metrics.ear ?? 0).toFixed(3)],
    ["POSE", `pitch ${(metrics.pitch ?? 0).toFixed(1)} / yaw ${(metrics.yaw ?? 0).toFixed(1)}`],
    ["GAZE", metrics.gaze ?? "n/a"],
    ["SEATBELT", metrics.seatbelt === true ? "ON" : metrics.seatbelt === false ? "OFF" : "N/A"],
    ["DROWSY", metrics.drowsy ? "YES" : "NO"],
    ["DISTRACT", metrics.distracted ? "YES" : "NO"],
  ];

  metricsEl.innerHTML = chips
    .map(([k, v]) => `<span class="chip"><b>${k}</b>: ${String(v)}</span>`)
    .join("");

  fpsPill.textContent = `FPS: ${metrics.fps ? metrics.fps.toFixed(1) : "—"}`;
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data && data.error ? data.error : `Request failed (${res.status})`;
    throw new Error(msg);
  }
  return data;
}

async function refreshStatus() {
  try {
    const st = await api("/api/status");
    setRunningUI(!!st.running);

    if (st.settings) {
      cameraIndex.value = st.settings.camera_index ?? 0;
      logEnabled.checked = !!st.settings.log_enabled;
      logPath.value = st.settings.log_path ?? "";
      volume.value = st.settings.volume ?? 0.8;
      cooldown.value = st.settings.cooldown ?? 1.2;
    }

    renderMetrics(st.metrics || {});
  } catch (e) {
    setHint(e.message, "error");
  }
}

startBtn.addEventListener("click", async () => {
  setHint("");
  try {
    await api("/api/start", { method: "POST", body: "{}" });
    await refreshStatus();
    setHint("Started.", "ok");
  } catch (e) {
    setHint(e.message, "error");
  }
});

stopBtn.addEventListener("click", async () => {
  setHint("");
  try {
    await api("/api/stop", { method: "POST", body: "{}" });
    await refreshStatus();
    setHint("Stopped.", "ok");
  } catch (e) {
    setHint(e.message, "error");
  }
});

applyBtn.addEventListener("click", async () => {
  setHint("");
  const payload = {
    camera_index: Number(cameraIndex.value),
    log_enabled: !!logEnabled.checked,
    log_path: String(logPath.value || ""),
    volume: Number(volume.value),
    cooldown: Number(cooldown.value),
  };
  try {
    await api("/api/settings", { method: "POST", body: JSON.stringify(payload) });
    await refreshStatus();
    setHint("Settings applied.", "ok");
  } catch (e) {
    setHint(e.message, "error");
  }
});

// Initial
refreshStatus();
setInterval(refreshStatus, 800);

const els = {
  badge: document.getElementById("runningBadge"),
  video: document.getElementById("video"),
  fps: document.getElementById("fpsText"),
  msg: document.getElementById("msg"),

  startBtn: document.getElementById("startBtn"),
  stopBtn: document.getElementById("stopBtn"),
  saveSettingsBtn: document.getElementById("saveSettingsBtn"),

  cameraIndex: document.getElementById("cameraIndex"),
  logEnabled: document.getElementById("logEnabled"),
  logPath: document.getElementById("logPath"),
  volume: document.getElementById("volume"),
  cooldown: document.getElementById("cooldown"),

  mFace: document.getElementById("mFace"),
  mEar: document.getElementById("mEar"),
  mPitch: document.getElementById("mPitch"),
  mYaw: document.getElementById("mYaw"),
  mGaze: document.getElementById("mGaze"),
  mSeatbelt: document.getElementById("mSeatbelt"),
  mDrowsy: document.getElementById("mDrowsy"),
  mDistracted: document.getElementById("mDistracted"),
};

function setMsg(text, ok = true) {
  els.msg.textContent = text;
  els.msg.style.color = ok ? "rgba(231,238,252,0.72)" : "#ff8a8a";
}

async function postJson(url, data = {}) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  const json = await res.json();
  if (!res.ok || json.ok === false) {
    throw new Error(json.error || `Request failed: ${res.status}`);
  }
  return json;
}

function updateBadge(running) {
  els.badge.textContent = running ? "Running" : "Stopped";
  els.badge.classList.toggle("running", !!running);
  els.badge.classList.toggle("stopped", !running);
}

function updateMetrics(m) {
  els.mFace.textContent = m.face_detected ? "OK" : "NO";
  els.mEar.textContent = (m.ear ?? 0).toFixed ? m.ear.toFixed(3) : `${m.ear ?? "—"}`;
  els.mPitch.textContent = (m.pitch ?? 0).toFixed ? m.pitch.toFixed(1) : `${m.pitch ?? "—"}`;
  els.mYaw.textContent = (m.yaw ?? 0).toFixed ? m.yaw.toFixed(1) : `${m.yaw ?? "—"}`;
  els.mGaze.textContent = m.gaze ?? "—";
  els.mSeatbelt.textContent = (m.seatbelt === true) ? "ON" : (m.seatbelt === false ? "OFF" : "N/A");
  els.mDrowsy.textContent = m.drowsy ? "YES" : "NO";
  els.mDistracted.textContent = m.distracted ? "YES" : "NO";
  els.fps.textContent = `FPS: ${m.fps ? m.fps.toFixed(1) : "—"}`;
}

async function refreshStatus() {
  const res = await fetch("/api/status");
  const st = await res.json();
  updateBadge(st.running);

  const s = st.settings || {};
  els.cameraIndex.value = s.camera_index ?? 0;
  els.logEnabled.checked = !!s.log_enabled;
  els.logPath.value = s.log_path ?? "logs/events.csv";
  els.volume.value = s.volume ?? 1.0;
  els.cooldown.value = s.cooldown ?? 1.0;

  updateMetrics(st.metrics || {});

  if (st.running) {
    // MJPEG stream
    els.video.src = "/video";
  } else {
    els.video.removeAttribute("src");
  }
}

els.startBtn.addEventListener("click", async () => {
  try {
    setMsg("Starting…");
    await postJson("/api/start");
    await refreshStatus();
    setMsg("Running.");
  } catch (e) {
    setMsg(e.message, false);
  }
});

els.stopBtn.addEventListener("click", async () => {
  try {
    setMsg("Stopping…");
    await postJson("/api/stop");
    await refreshStatus();
    setMsg("Stopped.");
  } catch (e) {
    setMsg(e.message, false);
  }
});

els.saveSettingsBtn.addEventListener("click", async () => {
  try {
    setMsg("Saving settings…");
    const payload = {
      camera_index: parseInt(els.cameraIndex.value || "0", 10),
      log_enabled: !!els.logEnabled.checked,
      log_path: els.logPath.value,
      volume: parseFloat(els.volume.value || "1.0"),
      cooldown: parseFloat(els.cooldown.value || "1.0"),
    };
    await postJson("/api/settings", payload);
    await refreshStatus();
    setMsg("Saved.");
  } catch (e) {
    setMsg(e.message, false);
  }
});

refreshStatus();
setInterval(refreshStatus, 800);

