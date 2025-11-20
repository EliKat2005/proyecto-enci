from django import template

register = template.Library()


@register.simple_tag
def unread_count(user):
    """Return the number of unread notifications for a user.

    Usage in templates:
      {% load notification_tags %}
      {% unread_count request.user as unread_count %}
    """
    try:
        if not user or user.is_anonymous:
            return 0
        return user.notifications.filter(unread=True).count()
    except Exception:
        return 0
