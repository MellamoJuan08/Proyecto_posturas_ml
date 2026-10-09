"""
Vistas del módulo detector de posturas.
Adaptadas a la lógica exacta del modelo (7 features, perfil).
"""
import base64
import json
import logging
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .ml_model import posture_model
from .models import PostureCapture, UserStats

logger = logging.getLogger(__name__)


@login_required
def dashboard(request):
    stats, _  = UserStats.objects.get_or_create(user=request.user)
    recent    = PostureCapture.objects.filter(user=request.user)[:5]
    context   = {
        'stats':           stats,
        'recent_captures': recent,
        'model_loaded':    posture_model.is_loaded,
        'page_title':      'Dashboard — PostureAI',
    }
    return render(request, 'detector/dashboard.html', context)


@login_required
@require_http_methods(['POST'])
def analyze_frame(request):
    """
    Recibe una imagen Base64, ejecuta MediaPipe + Random Forest
    y devuelve la predicción al frontend.
    """

    try:
        # ==========================================================
        # RECIBIR JSON
        # ==========================================================

        body = json.loads(request.body)

        image_data = body.get('image', '')
        save_capture = body.get('save', False)

        if not image_data:
            return JsonResponse(
                {
                    'success': False,
                    'error': 'No se recibió imagen.'
                },
                status=400
            )

        # ==========================================================
        # DECODIFICAR IMAGEN BASE64
        # ==========================================================

        if ',' in image_data:
            image_data = image_data.split(',', 1)[1]

        image_bytes = base64.b64decode(image_data)

        # ==========================================================
        # VALIDAR TAMAÑO
        # ==========================================================

        from django.conf import settings

        if len(image_bytes) > settings.MAX_IMAGE_SIZE:
            return JsonResponse(
                {
                    'success': False,
                    'error': 'Imagen demasiado grande.'
                },
                status=400
            )

        # ==========================================================
        # EJECUTAR MODELO
        # ==========================================================

        result = posture_model.predict(image_bytes)

        # ==========================================================
        # IMAGEN ANOTADA
        # ==========================================================

        annotated_b64 = result.get('annotated_image')

        # ==========================================================
        # GUARDAR CAPTURA
        # ==========================================================

        capture_id = None

        if save_capture and result.get('success'):

            ts = timezone.now().strftime('%Y%m%d_%H%M%S')
            uname = request.user.username

            # ------------------------------------------------------
            # CREAR CAPTURE PRIMERO
            # ------------------------------------------------------

            capture = PostureCapture(
                user=request.user,
                label=result['label'],
                raw_prediction=result.get(
                    'raw_prediction',
                    ''
                ),
                confidence=result['confidence'],
                status=result['status'],
                color=result['color'],
                landmarks_detected=result[
                    'landmarks_detected'
                ],
                in_profile=result.get(
                    'in_profile',
                    False
                ),
                ang_espalda=result.get(
                    'ang_espalda'
                ),
                ang_cuello=result.get(
                    'ang_cuello'
                ),
                inclinacion=result.get(
                    'inclinacion'
                ),
            )

            # ------------------------------------------------------
            # GUARDAR IMAGEN ORIGINAL
            # ------------------------------------------------------

            capture.image.save(
                f"{uname}_{ts}.jpg",
                ContentFile(image_bytes),
                save=False,
            )

            # ------------------------------------------------------
            # GUARDAR IMAGEN ANOTADA
            # ------------------------------------------------------

            if annotated_b64:

                annotated_data = annotated_b64

                # Quitar:
                # data:image/jpeg;base64,

                if ',' in annotated_data:
                    annotated_data = annotated_data.split(
                        ',',
                        1
                    )[1]

                annotated_bytes = base64.b64decode(
                    annotated_data
                )

                capture.annotated_img.save(
                    f"{uname}_{ts}_ann.jpg",
                    ContentFile(annotated_bytes),
                    save=False,
                )

            # ------------------------------------------------------
            # GUARDAR CAPTURA EN BASE DE DATOS
            # ------------------------------------------------------

            capture.save()

            capture_id = capture.id

            # ------------------------------------------------------
            # ACTUALIZAR ESTADÍSTICAS
            # ------------------------------------------------------

            stats, _ = UserStats.objects.get_or_create(
                user=request.user
            )

            stats.update(
                result['status']
            )

        # ==========================================================
        # RESPUESTA JSON
        # ==========================================================

        return JsonResponse(
            {
                'success': result['success'],
                'label': result['label'],
                'raw_prediction': result.get(
                    'raw_prediction'
                ),
                'confidence': result['confidence'],
                'status': result['status'],
                'color': result['color'],
                'landmarks_detected': result[
                    'landmarks_detected'
                ],
                'in_profile': result.get(
                    'in_profile',
                    False
                ),
                'ang_espalda': result.get(
                    'ang_espalda'
                ),
                'ang_cuello': result.get(
                    'ang_cuello'
                ),
                'inclinacion': result.get(
                    'inclinacion'
                ),
                'hint': result.get(
                    'hint'
                ),
                'annotated_image': annotated_b64,
                'capture_id': capture_id,
                'error': result.get(
                    'error'
                ),
            }
        )

    # ==============================================================
    # ERRORES
    # ==============================================================

    except json.JSONDecodeError:

        return JsonResponse(
            {
                'success': False,
                'error': 'JSON inválido.'
            },
            status=400
        )

    except Exception as e:

        logger.error(
            f"Error en analyze_frame: {e}",
            exc_info=True
        )

        return JsonResponse(
            {
                'success': False,
                'error': 'Error interno del servidor.'
            },
            status=500
        )


@login_required
def history(request):
    captures_qs   = PostureCapture.objects.filter(user=request.user)
    status_filter = request.GET.get('status', '')
    if status_filter in ('good', 'danger'):
        captures_qs = captures_qs.filter(status=status_filter)

    paginator = Paginator(captures_qs, 12)
    page_obj  = paginator.get_page(request.GET.get('page'))
    stats, _  = UserStats.objects.get_or_create(user=request.user)

    return render(request, 'detector/history.html', {
        'page_obj':      page_obj,
        'stats':         stats,
        'status_filter': status_filter,
        'page_title':    'Historial — PostureAI',
    })


@login_required
def capture_detail(request, pk):
    capture = get_object_or_404(PostureCapture, pk=pk, user=request.user)
    return render(request, 'detector/capture_detail.html', {
        'capture':    capture,
        'page_title': f'Captura #{pk} — PostureAI',
    })


@login_required
@require_http_methods(['POST'])
def delete_capture(request, pk):
    capture = get_object_or_404(PostureCapture, pk=pk, user=request.user)
    capture.delete()
    return redirect('detector:history')


@login_required
def model_status(request):
    return JsonResponse({
    'loaded': posture_model.is_loaded,
    'mediapipe': posture_model.pose is not None,
    'features': 7,
    'classes': ['buena', 'mala'],
    })
