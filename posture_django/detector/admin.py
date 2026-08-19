from django.contrib import admin
from .models import PostureCapture, UserStats


@admin.register(PostureCapture)
class PostureCaptureAdmin(admin.ModelAdmin):
    list_display = ('user', 'label', 'raw_prediction', 'confidence', 'status', 'in_profile', 'created_at')
    list_filter = ('status', 'in_profile', 'created_at')
    search_fields = ('user__username', 'label')
    readonly_fields = ('created_at',)


@admin.register(UserStats)
class UserStatsAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_captures', 'good_postures', 'bad_postures', 'last_activity')
    readonly_fields = ('last_activity',)