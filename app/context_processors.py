from django.db import models
from django.utils.translation import get_language
from .models import Notification
from .translations import TRANSLATIONS


def notification_count(request):
    """Add unread notification count to all templates"""
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(
            models.Q(user=request.user) | models.Q(user__isnull=True),
            is_read=False
        ).count()
        return {'unread_notifications_count': unread_count}
    return {'unread_notifications_count': 0}


def translations(request):
    """Add translations to all templates"""
    # Use Django's get_language() which checks session, cookies, and accepts language header
    language = get_language()
    
    # Extract just the language code (e.g., 'en' from 'en-us')
    if language and '-' in language:
        language = language.split('-')[0]
    
    # Default to English if language not in our translations
    if not language or language not in TRANSLATIONS:
        language = 'en'
    
    return {
        'translations': TRANSLATIONS[language],
        'current_language': language
    }
