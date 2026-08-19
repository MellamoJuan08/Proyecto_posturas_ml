from django.db import models
from django.contrib.auth.models import User


class PostureCapture(models.Model):
    STATUS_CHOICES = [
        ('good',    'Buena postura'),
        ('danger',  'Postura mala'),
        ('unknown', 'Sin determinar'),
    ]

    user               = models.ForeignKey(User, on_delete=models.CASCADE, related_name='captures')
    label              = models.CharField(max_length=120, verbose_name="Etiqueta mostrada")
    raw_prediction     = models.CharField(max_length=50,  verbose_name="Predicción del modelo", default='')
    confidence         = models.FloatField(default=0.0,   verbose_name="Confianza (%)")
    status             = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown')
    color              = models.CharField(max_length=10, default='#6b7280')
    landmarks_detected = models.BooleanField(default=False)
    in_profile         = models.BooleanField(default=False, verbose_name="En perfil correcto")
    # Los 3 features del modelo
    ang_espalda        = models.FloatField(null=True, blank=True, verbose_name="Ángulo espalda")
    ang_cuello         = models.FloatField(null=True, blank=True, verbose_name="Ángulo cuello")
    inclinacion        = models.FloatField(null=True, blank=True, verbose_name="Inclinación")
    # Imágenes
    image              = models.ImageField(upload_to='captures/%Y/%m/%d/', blank=True, null=True)
    annotated_img      = models.ImageField(upload_to='annotated/%Y/%m/%d/', blank=True, null=True)
    created_at         = models.DateTimeField(auto_now_add=True)
    notes              = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Captura de postura'
        verbose_name_plural = 'Capturas de postura'

    def __str__(self):
        return f"{self.user.username} — {self.label} ({self.created_at:%d/%m/%Y %H:%M})"


class UserStats(models.Model):
    user            = models.OneToOneField(User, on_delete=models.CASCADE, related_name='stats')
    total_captures  = models.PositiveIntegerField(default=0)
    good_postures   = models.PositiveIntegerField(default=0)
    bad_postures    = models.PositiveIntegerField(default=0)
    last_activity   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Estadísticas de usuario'

    def __str__(self):
        return f"Stats de {self.user.username}"

    @property
    def good_percentage(self):
        if self.total_captures == 0:
            return 0
        return round((self.good_postures / self.total_captures) * 100, 1)

    def update(self, status: str):
        self.total_captures += 1
        if status == 'good':
            self.good_postures += 1
        elif status == 'danger':
            self.bad_postures += 1
        self.save()
