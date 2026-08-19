from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class DetectorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'detector'
    verbose_name = 'Detector de Posturas'

    def ready(self):
        """
        Se ejecuta UNA SOLA VEZ al iniciar Django.
        Aquí cargamos el modelo PKL en memoria.
        """
        from django.conf import settings
        from .ml_model import posture_model

        model_path = str(settings.MODEL_PATH)
        loaded = posture_model.load(model_path)

        if loaded:
            logger.info("🤖 PostureAI: Modelo cargado y listo.")
        else:
            logger.warning(
                "⚠️  PostureAI: Modelo no cargado. "
                f"Coloca tu archivo .pkl en: {model_path}"
            )
