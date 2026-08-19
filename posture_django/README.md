# PostureAI — Django App

Interfaz web profesional para tu modelo PKL de detección de posturas.
Basado en tu script original con **MediaPipe + 3 features angulares**.

---

## 🧠 Cómo funciona tu modelo

Tu modelo recibe exactamente **3 features** extraídos del perfil izquierdo:

| Feature        | Cálculo                                 |
|----------------|-----------------------------------------|
| `ang_espalda`  | ángulo(hombro → cadera → rodilla)       |
| `ang_cuello`   | ángulo(oreja  → hombro → cadera)        |
| `inclinacion`  | `abs(hombro.x - cadera.x) * 100`        |

Predice: `"buena"` ✅ o `"mala"` ❌

**Requisito:** el usuario debe colocarse de **perfil izquierdo** con distancia horizontal entre hombros < 0.1 (es decir, perfil, no de frente).

---

## 🚀 Instalación

### 1. Entorno virtual

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 2. Dependencias

```bash
pip install -r requirements.txt
```

> ⚠️ `mediapipe` requiere **Python 3.8 – 3.11**. No es compatible con Python 3.12+.
> Comprueba tu versión con `python --version`.

### 3. Colocar el modelo PKL

Copia tu archivo `.pkl` a la raíz del proyecto:

```bash
# Debe quedar en:
posture_django/modelo_postura.pkl
```

O cambia la ruta en `.env`:
```ini
MODEL_PATH=C:\Users\Juan\ruta\a\tu\modelo_postura (2).pkl
```

### 4. Migraciones

```bash
cd posture_django
python manage.py migrate
```

### 5. Arrancar

```bash
python manage.py runserver
```

Abre: **http://localhost:8000**
Regístrate → Dashboard → ¡activa la cámara!

---

## 📁 Estructura

```
posture_django/
├── manage.py
├── modelo_postura.pkl          ← TU MODELO AQUÍ
├── requirements.txt
├── .env.example                ← copia a .env
├── posture_project/settings.py
├── accounts/                   ← login / registro
└── detector/
    ├── ml_model.py             ← wrapper exacto de tu script
    ├── models.py               ← guarda ang_espalda, ang_cuello, inclinacion
    ├── views.py
    └── templates/detector/
        ├── dashboard.html      ← cámara + ángulos en tiempo real
        ├── history.html
        └── capture_detail.html
```

---

## ⌨️ Atajos en el Dashboard

| Tecla     | Acción                   |
|-----------|--------------------------|
| `ESPACIO` | Capturar y guardar       |
| `A`       | Análisis continuo on/off |
| `ESC`     | Apagar cámara            |

---

## 🔧 .env (opcional)

```ini
SECRET_KEY=cambia-esto-en-produccion
DEBUG=True
MODEL_PATH=modelo_postura.pkl
```

---

## 🐛 Problemas frecuentes

**`FileNotFoundError: modelo_postura.pkl`**
→ El archivo debe estar en `posture_django/` (junto a `manage.py`)
→ O configura `MODEL_PATH` en `.env` con la ruta completa.

**`mediapipe` no instala en Python 3.12**
→ Usa Python 3.10 o 3.11. Crea un venv con esa versión.

**La cámara no funciona**
→ En Chrome/Firefox, `getUserMedia` requiere HTTPS en producción.
→ En `localhost` funciona sin HTTPS.

**"Ponte de perfil" siempre**
→ Posiciónate de lado (perfil izquierdo), no de frente a la cámara.
→ Como en tu script original.
