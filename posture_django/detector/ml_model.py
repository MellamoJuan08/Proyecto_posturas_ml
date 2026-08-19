"""
PostureAI — Wrapper del modelo PKL de postura
Lógica extraída directamente del script original del usuario.

Features de entrada (exactamente 3):
  1. ang_espalda  : ángulo hombro→cadera→rodilla
  2. ang_cuello   : ángulo oreja→hombro→cadera
  3. inclinacion  : abs(hombro.x - cadera.x) * 100

Clases de salida: "buena" | "mala"
"""

import logging
import numpy as np
import joblib
import cv2
import base64

logger = logging.getLogger(__name__)

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
    _mp_pose      = mp.solutions.pose
    _mp_drawing   = mp.solutions.drawing_utils
    _mp_styles    = mp.solutions.drawing_styles
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    logger.error("❌ MediaPipe NO está instalado. Instálalo con: pip install mediapipe")


# ── Constantes ────────────────────────────────────────────────────────────────

POSTURE_INFO = {
    "buena": {
        "label":  "POSTURA BUENA ✅",
        "status": "good",
        "color":  "#22c55e",
    },
    "mala": {
        "label":  "POSTURA MALA ❌",
        "status": "danger",
        "color":  "#ef4444",
    },
}


# ── Función auxiliar: calcular ángulo (idéntica al script original) ───────────

def calcular_angulo(a, b, c):
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    ba = a - b
    bc = c - b

    denominador = np.linalg.norm(ba) * np.linalg.norm(bc)
    if denominador == 0:
        return 0.0

    cos_angle = np.dot(ba, bc) / denominador
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_angle)))


# ── Clase principal ────────────────────────────────────────────────────────────

class PostureModel:
    """
    Wrapper alrededor del modelo PKL.
    Se carga UNA SOLA VEZ al iniciar Django (en DetectorConfig.ready).
    """

    def __init__(self):
        self.model        = None
        self.pose         = None
        self._loaded      = False

    # ── Carga ─────────────────────────────────────────────────────────────────

    def load(self, model_path: str) -> bool:
        try:
            self.model = joblib.load(model_path)
            logger.info(f"✅ Modelo cargado: {model_path}  [{type(self.model).__name__}]")

            if not MEDIAPIPE_AVAILABLE:
                raise RuntimeError("MediaPipe no disponible — instálalo con: pip install mediapipe")

            # Mismo Pose que el script original
            self.pose = _mp_pose.Pose(
                static_image_mode=True,
                model_complexity=1,
                enable_segmentation=False,
                min_detection_confidence=0.5,
            )
            logger.info("✅ MediaPipe Pose inicializado.")
            self._loaded = True
            return True

        except FileNotFoundError:
            logger.warning(
                f"⚠️  Modelo no encontrado en '{model_path}'. "
                "Coloca tu archivo .pkl y reinicia el servidor."
            )
        except Exception as e:
            logger.error(f"❌ Error al cargar el modelo: {e}", exc_info=True)

        self._loaded = False
        return False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    # ── Predicción ────────────────────────────────────────────────────────────

    def predict(self, image_bytes: bytes) -> dict:
        """
        Recibe imagen como bytes.
        Aplica la misma lógica del script original (perfil izquierdo).
        Retorna dict con resultado completo.
        """
        result = {
            "success":            False,
            "label":              "Sin detección",
            "raw_prediction":     None,
            "confidence":         0.0,
            "status":             "unknown",
            "color":              "#6b7280",
            "landmarks_detected": False,
            "in_profile":         False,
            "ang_espalda":        None,
            "ang_cuello":         None,
            "inclinacion":        None,
            "annotated_image":    None,
            "error":              None,
            "hint":               None,
        }

        if not self._loaded:
            result["error"] = "Modelo no cargado. Verifica la ruta del archivo .pkl."
            return result

        # ── Decodificar imagen ─────────────────────────────────────────────
        try:
            nparr     = np.frombuffer(image_bytes, np.uint8)
            frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame_bgr is None:
                result["error"] = "No se pudo decodificar la imagen."
                return result
        except Exception as e:
            result["error"] = f"Error al decodificar: {e}"
            return result

        # ── Redimensionar (igual que el script original) ──────────────────
        frame_bgr = cv2.resize(frame_bgr, (640, 480))
        rgb       = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        # ── Procesar con MediaPipe ─────────────────────────────────────────
        resultado_mp = self.pose.process(rgb)

        if not resultado_mp.pose_landmarks:
            result["hint"]  = "Colócate de perfil frente a la cámara."
            result["annotated_image"] = self._encode_frame(frame_bgr, "No detectado", (200, 200, 200))
            return result

        result["landmarks_detected"] = True
        lm = resultado_mp.pose_landmarks.landmark

        hombro_izq = lm[_mp_pose.PoseLandmark.LEFT_SHOULDER]
        hombro_der = lm[_mp_pose.PoseLandmark.RIGHT_SHOULDER]

        # ── Validar visibilidad del perfil izquierdo ──────────────────────
        if hombro_izq.visibility <= 0.7:
            result["hint"] = "Muestra tu perfil izquierdo."
            result["annotated_image"] = self._encode_frame(
                frame_bgr, "Muestra tu perfil izquierdo", (0, 0, 255)
            )
            return result

        # ── Validar que es perfil (distancia horizontal entre hombros) ────
        distancia = abs(hombro_izq.x - hombro_der.x)
        if distancia >= 0.1:
            result["hint"] = "Ponte de perfil (más lateral)."
            result["annotated_image"] = self._encode_frame(
                frame_bgr, "Ponte de perfil", (0, 0, 255)
            )
            return result

        result["in_profile"] = True

        # ── Extraer puntos (igual que el script original) ─────────────────
        hombro   = [lm[11].x, lm[11].y]
        cadera   = [lm[23].x, lm[23].y]
        rodilla  = [lm[25].x, lm[25].y]
        oreja    = [lm[7].x,  lm[7].y]

        ang_espalda  = calcular_angulo(hombro, cadera, rodilla)
        ang_cuello   = calcular_angulo(oreja,  hombro, cadera)
        inclinacion  = abs(hombro[0] - cadera[0]) * 100

        result["ang_espalda"] = round(ang_espalda, 1)
        result["ang_cuello"]  = round(ang_cuello,  1)
        result["inclinacion"] = round(inclinacion,  1)

        # ── Predicción ────────────────────────────────────────────────────
        try:
            datos      = [[ang_espalda, ang_cuello, inclinacion]]
            prediccion = self.modelo_predict(datos)

            info = POSTURE_INFO.get(prediccion, {
                "label":  f"Postura: {prediccion}",
                "status": "unknown",
                "color":  "#6b7280",
            })

            # Probabilidad si el modelo la soporta
            confidence = 0.0
            if hasattr(self.model, "predict_proba"):
                proba      = self.model.predict_proba(datos)[0]
                confidence = float(np.max(proba)) * 100

            result.update({
                "success":         True,
                "label":           info["label"],
                "raw_prediction":  prediccion,
                "confidence":      round(confidence, 1),
                "status":          info["status"],
                "color":           info["color"],
            })

        except Exception as e:
            logger.error(f"Error en predict(): {e}", exc_info=True)
            result["error"] = f"Error al predecir: {e}"
            return result

        # ── Imagen anotada ────────────────────────────────────────────────
        annotated = self._draw_landmarks(frame_bgr.copy(), resultado_mp)
        annotated = self._draw_angles(annotated, ang_espalda, ang_cuello, inclinacion)
        annotated = self._draw_result(annotated, result["label"], info["color"])
        result["annotated_image"] = self._encode_frame_raw(annotated)

        return result

    # ── Helpers ───────────────────────────────────────────────────────────────

    def modelo_predict(self, datos):
        """Wrapper seguro alrededor de model.predict."""
        pred = self.model.predict(datos)[0]
        # Normalizar por si el modelo retorna bytes/int en vez de str
        if isinstance(pred, bytes):
            pred = pred.decode()
        return str(pred).strip().lower()

    def _draw_landmarks(self, frame, mp_result):
        if mp_result and mp_result.pose_landmarks:
            _mp_drawing.draw_landmarks(
                frame,
                mp_result.pose_landmarks,
                _mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=_mp_styles.get_default_pose_landmarks_style(),
            )
        return frame

    def _draw_angles(self, frame, ang_espalda, ang_cuello, inclinacion):
        """Dibuja los ángulos en pantalla (igual que el script original)."""
        texto = f"E:{int(ang_espalda)}  C:{int(ang_cuello)}  I:{int(inclinacion)}"
        cv2.putText(
            frame, texto, (20, 50),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
        )
        return frame

    def _draw_result(self, frame, mensaje, hex_color):
        """Convierte color HEX → BGR y escribe el resultado."""
        try:
            h = hex_color.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            bgr = (b, g, r)
        except Exception:
            bgr = (255, 255, 255)

        cv2.putText(
            frame, mensaje, (20, 120),
            cv2.FONT_HERSHEY_SIMPLEX, 1, bgr, 3
        )
        return frame

    def _encode_frame(self, frame, mensaje, bgr_color):
        """Escribe mensaje y retorna JPEG bytes."""
        frame = frame.copy()
        cv2.putText(frame, mensaje, (20, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, bgr_color, 3)
        return self._encode_frame_raw(frame)

    def _encode_frame_raw(self, frame):
        """Retorna JPEG bytes."""
        try:
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return buf.tobytes()
        except Exception:
            return None


# ── Singleton global ──────────────────────────────────────────────────────────
posture_model = PostureModel()
