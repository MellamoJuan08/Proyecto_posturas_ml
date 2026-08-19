from django.urls import path
from . import views

app_name = 'detector'

urlpatterns = [
    path('dashboard/',              views.dashboard,        name='dashboard'),
    path('analyze/',                views.analyze_frame,    name='analyze_frame'),
    path('history/',                views.history,          name='history'),
    path('history/<int:pk>/',       views.capture_detail,   name='capture_detail'),
    path('history/<int:pk>/delete/',views.delete_capture,   name='delete_capture'),
    path('model-status/',           views.model_status,     name='model_status'),
]
