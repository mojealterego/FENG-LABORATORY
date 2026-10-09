"use strict";
const $ = id => document.getElementById(id);
const state = {devices: [], history: []};
const fmt = (value, digits = 1) => Number.isFinite(value) ? value.toFixed(digits) : "—";

async function getJSON(path) {
  const response = await fetch(path, {cache: "no-store"});
  if (!response.ok) throw new Error(`Odczyt HTTP ${response.status}`);
  return response.json();
}

function drawHistory() {
  const canvas = $("chart");
  const ctx = canvas.getContext("2d");
  const {width, height} = canvas;
  ctx.clearRect(0, 0, width, height);
  const rows = state.history.filter(row => Number.isFinite(row.temperature_c));
  if (!rows.length) {
    $("graph-message").textContent = "Brak dostępnych próbek temperatury.";
    return;
  }
  $("graph-message").textContent = `${rows.length} próbek; oś X oznacza kolejne rekordy.`;
  const values = rows.map(row => row.temperature_c);
  const ymin = Math.min(...values) - 1;
  const ymax = Math.max(...values) + 1;
  const left = 54, right = width - 26, top = 30, bottom = height - 35;
  ctx.lineWidth = 1;
  ctx.font = "12px system-ui";
  for (let i = 0; i <= 4; i++) {
    const y = top + (bottom - top) * i / 4;
    ctx.strokeStyle = "#263b51";
    ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(right, y); ctx.stroke();
    ctx.fillStyle = "#a0b4d2";
    ctx.fillText(fmt(ymax - (ymax - ymin) * i / 4) + "°", 6, y + 3);
  }
  const xCoord = index => left + (right - left) * index / Math.max(1, rows.length - 1);
  const yCoord = value => bottom - (value - ymin) * (bottom - top) / (ymax - ymin);
  ctx.beginPath();
  rows.forEach((row, i) => i === 0 ? ctx.moveTo(xCoord(i), yCoord(row.temperature_c)) : ctx.lineTo(xCoord(i), yCoord(row.temperature_c)));
  ctx.strokeStyle = "#58c6ef"; ctx.lineWidth = 3; ctx.stroke();
  rows.forEach((row, i) => {
    if (row.state !== "anomaly_candidate") return;
    ctx.beginPath(); ctx.arc(xCoord(i), yCoord(row.temperature_c), 5, 0, 2 * Math.PI);
    ctx.fillStyle = "#f6b756"; ctx.fill();
  });
}

async function loadHistory() {
  const chosen = state.devices[Number($("device").value)];
  if (!chosen) {
    state.history = [];
    ["temperature", "voltage", "packets", "anomalies"].forEach(id => $(id).textContent = "—");
    drawHistory();
    return;
  }
  const query = new URLSearchParams({app: chosen.app_id, device: chosen.device_id, limit: "100"});
  const response = await getJSON("/api/history?" + query.toString());
  state.history = response.history;
  const latest = state.history[state.history.length - 1];
  $("temperature").textContent = latest ? fmt(latest.temperature_c) : "—";
  $("voltage").textContent = latest ? fmt(latest.capacitor_voltage_v, 3) : "—";
  $("packets").textContent = String(chosen.total);
  $("anomalies").textContent = String(chosen.candidate_anomalies);
  drawHistory();
}

async function refresh() {
  $("refresh").disabled = true;
  $("status").textContent = "Ładowanie…";
  try {
    const previous = state.devices[Number($("device").value)];
    const data = await getJSON("/api/devices");
    state.devices = data.devices;
    const select = $("device");
    select.replaceChildren();
    state.devices.forEach((device, index) => {
      const option = document.createElement("option");
      option.value = String(index);
      option.textContent = `${device.app_id} / ${device.device_id}`;
      select.appendChild(option);
    });
    const selected = state.devices.findIndex(device => previous &&
      device.app_id === previous.app_id && device.device_id === previous.device_id);
    select.value = String(Math.max(0, selected));
    select.disabled = state.devices.length === 0;
    if (!state.devices.length) {
      const option = document.createElement("option"); option.textContent = "Brak danych"; select.appendChild(option);
    }
    await loadHistory();
    $("status").textContent = "Odczyt lokalny · aktywny";
    $("update").textContent = "Odświeżono " + new Date().toLocaleTimeString("pl-PL");
  } catch (error) {
    $("status").textContent = "Błąd odczytu";
    $("graph-message").textContent = `Nie udało się wczytać danych: ${error.message}`;
  } finally {
    $("refresh").disabled = false;
  }
}

$("refresh").addEventListener("click", refresh);
$("device").addEventListener("change", () => loadHistory().catch(error => {
  $("status").textContent = "Błąd historii";
  $("graph-message").textContent = error.message;
}));
refresh();
setInterval(refresh, 15000);
