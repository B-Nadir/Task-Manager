from .models import Notification

def global_context(request):
    """
    Adds unread notification count and chat unread count globally to all templates.
    """
    if not request.user.is_authenticated:
        return {
            "notifications_unread": 0,
            "chat_unread_count": 0,
        }

    return {
        "notifications_unread": Notification.objects.filter(user=request.user, is_read=False).count(),
            }
