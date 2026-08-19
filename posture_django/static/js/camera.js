/**
 * PostureAI — Camera & Analysis Engine
 * Con sistema de alertas posturales por tiempo
 * + Selector de cámara (incluye cámara del celular vía DroidCam/EpocCam)
 */

'use strict';

/* ── Voz ─────────────────────────────────────────────── */
const vozConfig = {
  ultimoMensaje: '',
  ultimoTiempo:  0,
  delaySegundos: 3,
};

function hablar(texto) {
  const ahora          = Date.now();
  const mismoMensaje   = texto === vozConfig.ultimoMensaje;
  const dentroDelDelay = (ahora - vozConfig.ultimoTiempo) < (vozConfig.delaySegundos * 1000);
  if (mismoMensaje && dentroDelDelay) return;

  window.speechSynthesis.cancel();
  const u   = new SpeechSynthesisUtterance(texto);
  u.lang    = 'es-CO';
  u.rate    = 1.0;
  u.pitch   = 1;
  window.speechSynthesis.speak(u);

  vozConfig.ultimoMensaje = texto;
  vozConfig.ultimoTiempo  = ahora;
}

/* ── Mensajes de higiene postural ────────────────────── */
const MENSAJES_BUENA = [
  "Llevas {T} minutos en buena postura. ¡Muy bien! Recuerda tomar un descanso, levántate, estírate un poco y camina.",
  "Han pasado {T} minutos. Tu postura es correcta, pero tu cuerpo necesita moverse. Date un minuto para estirarte.",
  "¡Excelente postura! Pero llevas {T} minutos sentado. Levántate, mueve el cuello de lado a lado y respira profundo.",
];

const MENSAJES_MALA = [
  "Llevas {T} minutos con mala postura. ¡Cuidado! Este tipo de posición puede generar contracturas y dañar tus discos intervertebrales. Corrígela ahora y estira la espalda hacia atrás.",
  "Atención: {T} minutos en postura incorrecta. Las malas posturas prolongadas pueden causar dolor crónico de espalda y cuello. Enderézate, saca el pecho y relaja los hombros.",
  "Tu espalda está en riesgo. Llevas {T} minutos en una posición que sobrecarga la columna. Para y haz este ejercicio: lleva el mentón al pecho, cuenta 5 segundos, y luego mira al techo despacio.",
];

function mensajeAleatorio(lista, minutos) {
  const msg = lista[Math.floor(Math.random() * lista.length)];
  return msg.replace('{T}', minutos);
}

/* ── Contador de tiempo postural ─────────────────────── */
const contador = {
  intervalo:         null,
  segundos:          0,
  limiteSegundos:    5 * 60,   // valor por defecto: 5 min
  estadoActual:      null,     // 'good' | 'danger' | null
  alertaDisparada:   false,
};

function iniciarContador(status) {
  if (status !== contador.estadoActual) {
    reiniciarContador(status);
    return;
  }
  if (contador.intervalo) return;

  contador.intervalo = setInterval(() => {
    contador.segundos++;
    actualizarBarraTiempo();
    if (contador.segundos >= contador.limiteSegundos && !contador.alertaDisparada) {
      contador.alertaDisparada = true;
      dispararAlerta();
    }
  }, 1000);
}

function reiniciarContador(nuevoStatus) {
  clearInterval(contador.intervalo);
  contador.intervalo       = null;
  contador.segundos        = 0;
  contador.estadoActual    = nuevoStatus;
  contador.alertaDisparada = false;
  actualizarBarraTiempo();

  contador.intervalo = setInterval(() => {
    contador.segundos++;
    actualizarBarraTiempo();
    if (contador.segundos >= contador.limiteSegundos && !contador.alertaDisparada) {
      contador.alertaDisparada = true;
      dispararAlerta();
    }
  }, 1000);
}

function detenerContador() {
  clearInterval(contador.intervalo);
  contador.intervalo    = null;
  contador.segundos     = 0;
  contador.estadoActual = null;
  actualizarBarraTiempo();
}

function dispararAlerta() {
  const minutos = Math.floor(contador.limiteSegundos / 60);
  const lista   = contador.estadoActual === 'good' ? MENSAJES_BUENA : MENSAJES_MALA;
  const mensaje = mensajeAleatorio(lista, minutos);

  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(mensaje);
  u.lang  = 'es-CO';
  u.rate  = 0.95;
  window.speechSynthesis.speak(u);

  mostrarToastAlerta(mensaje, contador.estadoActual);

  setTimeout(() => {
    contador.alertaDisparada = false;
    contador.segundos        = 0;
  }, 8000);
}

function actualizarBarraTiempo() {
  const barraEl   = document.getElementById('tiempoFill');
  const textoEl   = document.getElementById('tiempoTexto');
  const wrapperEl = document.getElementById('tiempoWrapper');
  if (!barraEl || !textoEl) return;

  const pct     = Math.min(100, (contador.segundos / contador.limiteSegundos) * 100);
  const minutos = Math.floor(contador.segundos / 60);
  const segs    = (contador.segundos % 60).toString().padStart(2, '0');

  barraEl.style.width = `${pct}%`;

  if (pct >= 90) {
    barraEl.style.background = '#ef4444';
  } else if (pct >= 60) {
    barraEl.style.background = '#f59e0b';
  } else {
    barraEl.style.background = contador.estadoActual === 'good' ? '#22c55e' : '#ef4444';
  }

  textoEl.textContent = `${minutos}:${segs} / ${Math.floor(contador.limiteSegundos / 60)}:00`;

  if (wrapperEl && contador.estadoActual) {
    wrapperEl.style.display = 'block';
  }
}

function mostrarToastAlerta(mensaje, status) {
  const color  = status === 'good' ? '#22c55e' : '#ef4444';
  const icono  = status === 'good' ? 'bi-clock-history' : 'bi-exclamation-triangle-fill';
  const titulo = status === 'good' ? '¡Tiempo de descanso!' : '⚠️ Postura en riesgo';

  const toast = document.createElement('div');
  toast.className = 'toast-postural';
  toast.style.cssText = `
    position:fixed; bottom:24px; right:24px; z-index:9999;
    background:#1a2235; border:1px solid ${color};
    border-left: 4px solid ${color};
    border-radius:12px; padding:16px 20px;
    max-width:360px; box-shadow:0 8px 32px rgba(0,0,0,0.4);
    animation: slideIn 0.3s ease;
  `;
  toast.innerHTML = `
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
      <i class="bi ${icono}" style="color:${color};font-size:18px"></i>
      <strong style="color:${color}">${titulo}</strong>
      <button onclick="this.parentElement.parentElement.remove()"
        style="margin-left:auto;background:none;border:none;color:#6b7280;cursor:pointer;font-size:18px">×</button>
    </div>
    <p style="color:#e8edf5;font-size:13px;line-height:1.5;margin:0">${mensaje}</p>
  `;

  if (!document.getElementById('toastStyle')) {
    const style = document.createElement('style');
    style.id = 'toastStyle';
    style.textContent = `@keyframes slideIn { from { transform: translateX(120%); opacity:0; } to { transform: translateX(0); opacity:1; } }`;
    document.head.appendChild(style);
  }

  document.body.appendChild(toast);
  setTimeout(() => toast.style.opacity = '0', 12000);
  setTimeout(() => toast.remove(),             12400);
}

/* ── Estado ──────────────────────────────────────────── */
const state = {
  stream:        null,
  isStreaming:   false,
  autoInterval:  null,
  isAutoRunning: false,
  autoFrequency: 800,
  isProcessing:  false,
};

const el = {
  video:        () => document.getElementById('videoFeed'),
  canvas:       () => document.getElementById('captureCanvas'),
  placeholder:  () => document.getElementById('cameraPlaceholder'),
  liveDot:      () => document.getElementById('liveDot'),
  btnToggle:    () => document.getElementById('btnToggleCamera'),
  btnCapture:   () => document.getElementById('btnCapture'),
  btnAuto:      () => document.getElementById('btnAuto'),
  cameraLabel:  () => document.getElementById('cameraLabel'),
  autoIcon:     () => document.getElementById('autoIcon'),
  autoLabel:    () => document.getElementById('autoLabel'),
  videoOverlay: () => document.getElementById('videoOverlay'),
  overlayLabel: () => document.getElementById('overlayLabel'),
  annotatedImg: () => document.getElementById('annotatedImg'),
  postureLabel: () => document.getElementById('postureLabel'),
  postureConf:  () => document.getElementById('postureConf'),
  postureRing:  () => document.getElementById('postureRing'),
  postureIcon:  () => document.getElementById('postureIcon'),
  postureHint:  () => document.getElementById('postureHint'),
  confFill:     () => document.getElementById('confFill'),
  confPct:      () => document.getElementById('confPct'),
  resultTs:     () => document.getElementById('resultTs'),
  valEspalda:   () => document.getElementById('valEspalda'),
  valCuello:    () => document.getElementById('valCuello'),
  valInclin:    () => document.getElementById('valInclin'),
  anglesBlock:  () => document.getElementById('anglesBlock'),
  profileBadge: () => document.getElementById('profileBadge'),
  recentList:   () => document.getElementById('recentList'),
};

/* ── Selector de cámara ──────────────────────────────── */
async function listCameras() {
  try {
    // Pedimos permiso primero para que el navegador revele los nombres reales
    await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    const devices = await navigator.mediaDevices.enumerateDevices();
    const cameras = devices.filter(d => d.kind === 'videoinput');
    const select  = document.getElementById('cameraSelect');
    if (!select) return;
    select.innerHTML = '';
    cameras.forEach((cam, i) => {
      const opt       = document.createElement('option');
      opt.value       = cam.deviceId;
      opt.textContent = cam.label || `Cámara ${i + 1}`;
      select.appendChild(opt);
    });
  } catch (err) {
    console.error('No se pudo listar cámaras:', err);
  }
}

function changeCamera(deviceId) {
  if (state.isStreaming) {
    stopCamera();
    // Pequeña pausa para que el stream anterior se libere completamente
    setTimeout(() => startCamera(deviceId), 300);
  }
}

/* ── Cámara ──────────────────────────────────────────── */
async function startCamera(deviceId = null) {
  try {
    // Si se recibe un deviceId específico (cámara seleccionada), lo usa.
    // Si no, usa la cámara frontal por defecto (comportamiento original).
    const videoConstraints = deviceId
      ? { deviceId: { exact: deviceId }, width: { ideal: 640 }, height: { ideal: 480 } }
      : { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' };

    state.stream = await navigator.mediaDevices.getUserMedia({
      video: videoConstraints,
      audio: false,
    });
    const video = el.video();
    video.srcObject = state.stream;
    video.onloadedmetadata = () => {
      video.play();
      state.isStreaming = true;
      showCameraActive();
    };
  } catch (err) { handleCameraError(err); }
}

function stopCamera() {
  if (state.stream) state.stream.getTracks().forEach(t => t.stop());
  state.stream = null;
  stopAutoAnalysis();
  detenerContador();
  state.isStreaming = false;
  showCameraInactive();
}

function toggleCamera() { state.isStreaming ? stopCamera() : startCamera(); }

function showCameraActive() {
  el.video().classList.remove('d-none');
  el.placeholder().classList.add('d-none');
  el.liveDot().classList.add('active');
  el.btnToggle().disabled  = false;
  el.btnCapture().disabled = !MODEL_LOADED;
  el.btnAuto().disabled    = !MODEL_LOADED;
  el.cameraLabel().textContent = 'Detener cámara';
}

function showCameraInactive() {
  el.video().classList.add('d-none');
  el.placeholder().classList.remove('d-none');
  el.liveDot().classList.remove('active');
  el.btnCapture().disabled = true;
  el.btnAuto().disabled    = true;
  el.cameraLabel().textContent = 'Activar cámara';
  el.annotatedImg().classList.add('d-none');
  el.videoOverlay().classList.add('d-none');
  const w = document.getElementById('tiempoWrapper');
  if (w) w.style.display = 'none';
}

function handleCameraError(err) {
  const msgs = {
    NotAllowedError:  'Permiso de cámara denegado.',
    NotFoundError:    'No se encontró ninguna cámara.',
    NotReadableError: 'La cámara está siendo usada por otra aplicación.',
  };
  el.placeholder().innerHTML = `
    <i class="bi bi-exclamation-triangle-fill" style="color:var(--warning);font-size:42px"></i>
    <p style="color:var(--warning);font-size:14px;padding:0 32px;text-align:center;margin:12px 0">
      ${msgs[err.name] || 'No se pudo acceder a la cámara.'}
    </p>
    <button class="btn-start-camera" onclick="startCamera()">
      <i class="bi bi-arrow-clockwise me-2"></i>Reintentar
    </button>`;
}

/* ── Captura ─────────────────────────────────────────── */
function captureFrame() {
  const video = el.video(), canvas = el.canvas();
  if (!video || video.readyState < 2) return null;
  canvas.width  = video.videoWidth  || 640;
  canvas.height = video.videoHeight || 480;
  canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL('image/jpeg', 0.85);
}

async function sendFrame(imageData, save = false) {
  if (state.isProcessing) return null;
  state.isProcessing = true;
  try {
    const res = await fetch(ANALYZE_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
      body: JSON.stringify({ image: imageData, save }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('API error:', err);
    return { success: false, error: err.message };
  } finally { state.isProcessing = false; }
}

async function analyzeFrame() {
  if (!state.isStreaming) return;
  const imageData = captureFrame();
  if (!imageData) return;
  const result = await sendFrame(imageData, false);
  if (result) updateUI(result, false);
}

async function captureAndSave() {
  if (!state.isStreaming || state.isProcessing) return;
  const imageData = captureFrame();
  if (!imageData) return;
  const btn = el.btnCapture();
  btn.disabled = true;
  btn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Guardando...';
  const result = await sendFrame(imageData, true);
  if (result) { updateUI(result, true); if (result.success) addRecentItem(result); }
  btn.disabled = false;
  btn.innerHTML = '<i class="bi bi-camera-fill me-2"></i>Capturar y guardar';
}

function toggleAutoAnalysis() { state.isAutoRunning ? stopAutoAnalysis() : startAutoAnalysis(); }

function startAutoAnalysis() {
  if (!state.isStreaming) return;
  state.isAutoRunning = true;
  state.autoInterval  = setInterval(analyzeFrame, state.autoFrequency);
  el.btnAuto().classList.add('running');
  el.autoIcon().className    = 'bi bi-stop-fill me-2';
  el.autoLabel().textContent = 'Detener auto';
}

function stopAutoAnalysis() {
  if (state.autoInterval) clearInterval(state.autoInterval);
  state.autoInterval  = null;
  state.isAutoRunning = false;
  el.btnAuto().classList.remove('running');
  el.autoIcon().className    = 'bi bi-play-fill me-2';
  el.autoLabel().textContent = 'Análisis continuo';
}

/* ── UI Updates ──────────────────────────────────────── */
function updateUI(result, saved) {
  const {
    success, label, confidence, status, color,
    in_profile, hint, ang_espalda, ang_cuello,
    inclinacion, annotated_image,
  } = result;

  el.videoOverlay().classList.remove('d-none');

  if (!success && result.error) {
    el.overlayLabel().textContent = result.error || 'Error';
    el.overlayLabel().style.color = 'var(--warning)';
    return;
  }

  if (!in_profile) {
    const hintMsg = hint || 'Ponte de perfil izquierdo';
    el.overlayLabel().textContent  = hintMsg;
    el.overlayLabel().style.color  = '#f59e0b';
    el.postureLabel().textContent  = hintMsg;
    el.postureHint().textContent   = hint || '';
    el.postureHint().style.display = hint ? 'block' : 'none';
    el.anglesBlock().style.display  = 'none';
    el.profileBadge().style.display = 'none';
    return;
  }

  /* ── Voz de resultado ── */
  if (success) {
    const textoVoz = status === 'good' ? 'Postura buena' : 'Postura mala';
    hablar(textoVoz);
  }

  /* ── Contador de tiempo postural ── */
  if (success) iniciarContador(status);

  el.overlayLabel().textContent = label;
  el.overlayLabel().style.color = color;
  el.postureLabel().textContent = label;
  el.postureLabel().style.color = color;
  el.postureConf().textContent  = confidence > 0 ? `Confianza: ${confidence}%` : '';
  el.postureConf().style.color  = color;
  el.postureRing().style.borderColor = color;
  el.postureIcon().style.color       = color;
  el.postureIcon().className = status === 'good'
    ? 'bi bi-person-check-fill' : 'bi bi-person-x-fill';
  el.postureHint().style.display = 'none';

  if (ang_espalda != null) {
    el.anglesBlock().style.display = 'grid';
    el.valEspalda().textContent = `${ang_espalda}°`;
    el.valCuello().textContent  = `${ang_cuello}°`;
    el.valInclin().textContent  = `${inclinacion}`;
  }

  el.profileBadge().style.display = 'flex';
  el.profileBadge().textContent   = '✓ Perfil correcto';
  el.profileBadge().style.color   = 'var(--good)';

  const pct = Math.min(100, confidence || 0);
  el.confFill().style.width      = `${pct}%`;
  el.confFill().style.background = color;
  el.confPct().textContent       = `${pct}%`;
  el.resultTs().textContent = new Date().toLocaleTimeString('es-CO');

  if (saved && annotated_image) {
    el.annotatedImg().src = annotated_image;
    el.annotatedImg().classList.remove('d-none');
    el.video().classList.add('d-none');
    setTimeout(() => {
      el.annotatedImg().classList.add('d-none');
      el.video().classList.remove('d-none');
    }, 2500);
  }
}

function addRecentItem(result) {
  const list  = el.recentList();
  const empty = list.querySelector('p');
  if (empty) empty.remove();
  const now  = new Date();
  const ts   = `${now.getDate().toString().padStart(2,'0')}/${(now.getMonth()+1).toString().padStart(2,'0')} ${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}`;
  const item = document.createElement('div');
  item.className = 'recent-item';
  item.innerHTML = `
    <div class="recent-dot" style="background:${result.color}"></div>
    <div class="recent-info">
      <span class="recent-label">${result.label}</span>
      <span class="recent-time">${ts}</span>
    </div>
    <span class="recent-conf">${result.confidence}%</span>`;
  list.insertBefore(item, list.firstChild);
  const items = list.querySelectorAll('.recent-item');
  if (items.length > 5) items[items.length - 1].remove();
}

/* ── Init ────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  listCameras(); // Detecta y llena el selector con todas las cámaras disponibles

  window.addEventListener('beforeunload', stopCamera);

  /* Leer el límite configurado por el usuario */
  const inputLimite = document.getElementById('inputLimiteMinutos');
  if (inputLimite) {
    inputLimite.addEventListener('change', () => {
      const val = parseInt(inputLimite.value, 10);
      if (val >= 1 && val <= 120) {
        contador.limiteSegundos = val * 60;
        contador.segundos       = 0;
        contador.alertaDisparada = false;
        actualizarBarraTiempo();
      }
    });
  }

  document.addEventListener('keydown', e => {
    if (['INPUT','TEXTAREA'].includes(e.target.tagName)) return;
    if (e.key === ' ') { e.preventDefault(); if (state.isStreaming) captureAndSave(); }
    if (e.key === 'a' || e.key === 'A') { if (state.isStreaming) toggleAutoAnalysis(); }
    if (e.key === 'Escape') stopCamera();
  });
});
