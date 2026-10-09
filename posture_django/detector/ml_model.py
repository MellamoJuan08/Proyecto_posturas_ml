"""
PostureAI — Wrapper del modelo Random Forest de postura

Modelo utilizado:
    RandomForestClassifier

Features de entrada (exactamente 3):
    1. espalda      : ángulo hombro → cadera → rodilla
    2. cuello       : ángulo oreja → hombro → cadera
    3. inclinacion  : abs(hombro.x - cadera.x) * 100

Clases utilizadas durante el entrenamiento:
    buena = 0
    mala  = 1

Estas clases corresponden al LabelEncoder utilizado durante
el entrenamiento del Random Forest.
"""

import logging
import numpy as np
import joblib
import cv2
import base64

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# MEDIAPIPE
# ══════════════════════════════════════════════════════════════════════════════

try:

    import mediapipe as mp

    MEDIAPIPE_AVAILABLE = True

    _mp_pose = mp.solutions.pose
    _mp_drawing = mp.solutions.drawing_utils
    _mp_styles = mp.solutions.drawing_styles

except ImportError:

    MEDIAPIPE_AVAILABLE = False

    logger.error(
        "MediaPipe NO está instalado. "
        "Instálalo con: pip install mediapipe"
    )


# ══════════════════════════════════════════════════════════════════════════════
# INFORMACIÓN DE LAS POSTURAS
# ══════════════════════════════════════════════════════════════════════════════

POSTURE_INFO = {

    "buena": {
        "label": "POSTURA BUENA ✅",
        "status": "good",
        "color": "#22c55e",
    },

    "mala": {
        "label": "POSTURA MALA ❌",
        "status": "danger",
        "color": "#ef4444",
    },

}


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN PARA CALCULAR ÁNGULOS
# ══════════════════════════════════════════════════════════════════════════════

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

    cos_angle = np.clip(
        cos_angle,
        -1.0,
        1.0
    )

    return float(
        np.degrees(
            np.arccos(cos_angle)
        )
    )


# ══════════════════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

class PostureModel:

    """
    Wrapper alrededor del modelo Random Forest.

    El modelo espera exactamente estas tres variables:

        [espalda, cuello, inclinacion]

    El entrenamiento utilizó:

        buena = 0
        mala  = 1
    """

    def __init__(self):

        self.model = None
        self.pose = None
        self._loaded = False


    # ══════════════════════════════════════════════════════════════════════════
    # CARGAR MODELO
    # ══════════════════════════════════════════════════════════════════════════

    def load(self, model_path: str) -> bool:

        try:

            self.model = joblib.load(model_path)

            logger.info(
                f"Modelo cargado: {model_path} "
                f"[{type(self.model).__name__}]"
            )

            if not MEDIAPIPE_AVAILABLE:

                raise RuntimeError(
                    "MediaPipe no disponible. "
                    "Instálalo con: pip install mediapipe"
                )


            # ══════════════════════════════════════════════════════════════
            # MEDIAPIPE POSE
            # ══════════════════════════════════════════════════════════════

            self.pose = _mp_pose.Pose(

                static_image_mode=True,

                model_complexity=1,

                enable_segmentation=False,

                min_detection_confidence=0.5,
            )


            logger.info(
                "MediaPipe Pose inicializado correctamente."
            )


            # Mostrar las clases que tiene realmente el modelo

            if hasattr(self.model, "classes_"):

                logger.info(
                    f"Clases del Random Forest: "
                    f"{self.model.classes_}"
                )


            self._loaded = True

            return True


        except FileNotFoundError:

            logger.warning(
                f"Modelo no encontrado en '{model_path}'. "
                "Coloca el archivo .pkl y reinicia el servidor."
            )


        except Exception as e:

            logger.error(
                f"Error al cargar el modelo: {e}",
                exc_info=True
            )


        self._loaded = False

        return False


    # ══════════════════════════════════════════════════════════════════════════
    # ESTADO DEL MODELO
    # ══════════════════════════════════════════════════════════════════════════

    @property
    def is_loaded(self) -> bool:

        return self._loaded


    # ══════════════════════════════════════════════════════════════════════════
    # PREDICCIÓN
    # ══════════════════════════════════════════════════════════════════════════

    def predict(self, image_bytes: bytes) -> dict:

        result = {

            "success": False,

            "label": "Sin detección",

            "raw_prediction": None,

            "confidence": 0.0,

            "status": "unknown",

            "color": "#6b7280",

            "landmarks_detected": False,

            "in_profile": False,

            "ang_espalda": None,

            "ang_cuello": None,

            "inclinacion": None,

            "annotated_image": None,

            "error": None,

            "hint": None,
        }


        # ══════════════════════════════════════════════════════════════════
        # VERIFICAR MODELO
        # ══════════════════════════════════════════════════════════════════

        if not self._loaded:

            result["error"] = (
                "Modelo no cargado. "
                "Verifica la ruta del archivo .pkl."
            )

            return result


        # ══════════════════════════════════════════════════════════════════
        # DECODIFICAR IMAGEN
        # ══════════════════════════════════════════════════════════════════

        try:

            nparr = np.frombuffer(
                image_bytes,
                np.uint8
            )

            frame_bgr = cv2.imdecode(
                nparr,
                cv2.IMREAD_COLOR
            )


            if frame_bgr is None:

                result["error"] = (
                    "No se pudo decodificar la imagen."
                )

                return result


        except Exception as e:

            result["error"] = (
                f"Error al decodificar: {e}"
            )

            return result


        # ══════════════════════════════════════════════════════════════════
        # REDIMENSIONAR
        # ══════════════════════════════════════════════════════════════════

        frame_bgr = cv2.resize(
            frame_bgr,
            (640, 480)
        )

        rgb = cv2.cvtColor(
            frame_bgr,
            cv2.COLOR_BGR2RGB
        )


        # ══════════════════════════════════════════════════════════════════
        # MEDIAPIPE
        # ══════════════════════════════════════════════════════════════════

        resultado_mp = self.pose.process(rgb)


        if not resultado_mp.pose_landmarks:

            result["hint"] = (
                "Colócate de perfil frente a la cámara."
            )

            result["annotated_image"] = self._encode_frame(
                frame_bgr,
                "No detectado",
                (200, 200, 200)
            )

            return result


        result["landmarks_detected"] = True

        lm = resultado_mp.pose_landmarks.landmark


        # ══════════════════════════════════════════════════════════════════
        # HOMBROS
        # ══════════════════════════════════════════════════════════════════

        hombro_izq = lm[
            _mp_pose.PoseLandmark.LEFT_SHOULDER
        ]

        hombro_der = lm[
            _mp_pose.PoseLandmark.RIGHT_SHOULDER
        ]


        # ══════════════════════════════════════════════════════════════════
        # VISIBILIDAD
        # ══════════════════════════════════════════════════════════════════

        if hombro_izq.visibility <= 0.7:

            result["hint"] = (
                "Muestra tu perfil izquierdo."
            )

            result["annotated_image"] = self._encode_frame(
                frame_bgr,
                "Muestra tu perfil izquierdo",
                (0, 0, 255)
            )

            return result


        # ══════════════════════════════════════════════════════════════════
        # VALIDAR PERFIL
        # ══════════════════════════════════════════════════════════════════

        distancia = abs(
            hombro_izq.x -
            hombro_der.x
        )


        if distancia >= 0.1:

            result["hint"] = (
                "Ponte de perfil (más lateral)."
            )

            result["annotated_image"] = self._encode_frame(
                frame_bgr,
                "Ponte de perfil",
                (0, 0, 255)
            )

            return result


        result["in_profile"] = True


        # ══════════════════════════════════════════════════════════════════
        # EXTRAER LANDMARKS
        # ══════════════════════════════════════════════════════════════════

        hombro = [
            lm[11].x,
            lm[11].y
        ]

        cadera = [
            lm[23].x,
            lm[23].y
        ]

        rodilla = [
            lm[25].x,
            lm[25].y
        ]

        oreja = [
            lm[7].x,
            lm[7].y
        ]


        # ══════════════════════════════════════════════════════════════════
        # CALCULAR FEATURES
        # ══════════════════════════════════════════════════════════════════

        ang_espalda = calcular_angulo(
            hombro,
            cadera,
            rodilla
        )

        ang_cuello = calcular_angulo(
            oreja,
            hombro,
            cadera
        )

        inclinacion = abs(
            hombro[0] -
            cadera[0]
        ) * 100


        # Guardar resultados

        result["ang_espalda"] = round(
            ang_espalda,
            1
        )

        result["ang_cuello"] = round(
            ang_cuello,
            1
        )

        result["inclinacion"] = round(
            inclinacion,
            1
        )


        # ══════════════════════════════════════════════════════════════════
        # PREDICCIÓN
        # ══════════════════════════════════════════════════════════════════

        try:

            # IMPORTANTE:
            # Este es exactamente el mismo orden utilizado
            # durante el entrenamiento:
            #
            # espalda
            # cuello
            # inclinacion

            datos = [[
              ang_espalda,
              ang_cuello,
              inclinacion,
              0.0,  # incl_hombros
              0.0,  # incl_cabeza
              0.0,  # desv_lateral
              1     # vista_perfil
              ]]


            prediccion = self.modelo_predict(
                datos
            )


            info = POSTURE_INFO.get(

                prediccion,

                {
                    "label": f"Postura: {prediccion}",

                    "status": "unknown",

                    "color": "#6b7280",
                }
            )


            # ══════════════════════════════════════════════════════════════
            # CONFIANZA
            # ══════════════════════════════════════════════════════════════

            confidence = 0.0


            if hasattr(
                self.model,
                "predict_proba"
            ):

                proba = self.model.predict_proba(
                    datos
                )[0]

                confidence = (
                    float(
                        np.max(proba)
                    ) * 100
                )


            result.update({

                "success": True,

                "label": info["label"],

                "raw_prediction": prediccion,

                "confidence": round(
                    confidence,
                    1
                ),

                "status": info["status"],

                "color": info["color"],
            })


        except Exception as e:

            logger.error(
                f"Error en predict(): {e}",
                exc_info=True
            )

            result["error"] = (
                f"Error al predecir: {e}"
            )

            return result


        # ══════════════════════════════════════════════════════════════════
        # DIBUJAR RESULTADO
        # ══════════════════════════════════════════════════════════════════

        annotated = self._draw_landmarks(
            frame_bgr.copy(),
            resultado_mp
        )


        annotated = self._draw_angles(

            annotated,

            ang_espalda,

            ang_cuello,

            inclinacion

        )


        annotated = self._draw_result(

            annotated,

            result["label"],

            info["color"]

        )


        result["annotated_image"] = (
            self._encode_frame_raw(
                annotated
            )
        )


        return result


    # ══════════════════════════════════════════════════════════════════════════
    # PREDICCIÓN DEL RANDOM FOREST
    # ══════════════════════════════════════════════════════════════════════════

    def modelo_predict(self, datos):

        """
        Ejecuta el Random Forest y convierte las etiquetas numéricas
        utilizadas durante el entrenamiento:

            0 → buena
            1 → mala

        Si en el futuro se utiliza un modelo que ya devuelve strings,
        también será compatible.
        """

        pred = self.model.predict(datos)[0]


        # ──────────────────────────────────────────────────────────────────
        # CASO 1: MODELO ENTRENADO CON LabelEncoder
        # ──────────────────────────────────────────────────────────────────

        if isinstance(
            pred,
            (int, np.integer)
        ):

            if int(pred) == 0:

                return "buena"

            elif int(pred) == 1:

                return "mala"


        # ──────────────────────────────────────────────────────────────────
        # CASO 2: MODELO QUE DEVUELVE FLOAT
        # ──────────────────────────────────────────────────────────────────

        if isinstance(
            pred,
            (float, np.floating)
        ):

            if float(pred) == 0:

                return "buena"

            elif float(pred) == 1:

                return "mala"


        # ──────────────────────────────────────────────────────────────────
        # CASO 3: MODELO QUE YA DEVUELVE STRINGS
        # ──────────────────────────────────────────────────────────────────

        if isinstance(
            pred,
            bytes
        ):

            pred = pred.decode()


        pred = str(
            pred
        ).strip().lower()


        return pred


    # ══════════════════════════════════════════════════════════════════════════
    # DIBUJAR LANDMARKS
    # ══════════════════════════════════════════════════════════════════════════

    def _draw_landmarks(
        self,
        frame,
        mp_result
    ):

        if (
            mp_result
            and mp_result.pose_landmarks
        ):

            _mp_drawing.draw_landmarks(

                frame,

                mp_result.pose_landmarks,

                _mp_pose.POSE_CONNECTIONS,

                landmark_drawing_spec=(
                    _mp_styles
                    .get_default_pose_landmarks_style()
                ),
            )


        return frame


    # ══════════════════════════════════════════════════════════════════════════
    # DIBUJAR ÁNGULOS
    # ══════════════════════════════════════════════════════════════════════════

    def _draw_angles(
        self,
        frame,
        ang_espalda,
        ang_cuello,
        inclinacion
    ):

        texto = (
            f"E:{int(ang_espalda)}  "
            f"C:{int(ang_cuello)}  "
            f"I:{int(inclinacion)}"
        )


        cv2.putText(

            frame,

            texto,

            (20, 50),

            cv2.FONT_HERSHEY_SIMPLEX,

            0.7,

            (0, 255, 0),

            2

        )


        return frame


    # ══════════════════════════════════════════════════════════════════════════
    # CODIFICAR FRAME
    # ══════════════════════════════════════════════════════════════════════════

    def _encode_frame(
        self,
        frame,
        texto,
        color
    ):

        cv2.putText(

            frame,

            texto,

            (20, 120),

            cv2.FONT_HERSHEY_SIMPLEX,

            1,

            color,

            3

        )


        return self._encode_frame_raw(
            frame
        )


    def _encode_frame_raw(
        self,
        frame
    ):

        success, buffer = cv2.imencode(
            ".jpg",
            frame
        )


        if not success:

            return None


        return (
            "data:image/jpeg;base64,"
            + base64.b64encode(
                buffer
            ).decode("utf-8")
        )


    # ══════════════════════════════════════════════════════════════════════════
    # DIBUJAR RESULTADO
    # ══════════════════════════════════════════════════════════════════════════

    def _draw_result(
        self,
        frame,
        label,
        color
    ):

        # Convertir color hexadecimal a BGR

        try:

            hex_color = color.lstrip("#")

            r = int(
                hex_color[0:2],
                16
            )

            g = int(
                hex_color[2:4],
                16
            )

            b = int(
                hex_color[4:6],
                16
            )

            bgr = (
                b,
                g,
                r
            )

        except Exception:

            bgr = (
                255,
                255,
                255
            )


        cv2.putText(

            frame,

            label,

            (20, 120),

            cv2.FONT_HERSHEY_SIMPLEX,

            1,

            bgr,

            3

        )


        return frame
posture_model = PostureModel()