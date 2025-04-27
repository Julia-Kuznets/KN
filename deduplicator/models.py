
from django.db import models
from django.utils import timezone

class UniqueEvent(models.Model):
    """
    Модель для хранения уникальных событий, прошедших дедупликацию.
    """
    # Отпечаток события, который мы генерируем. Должен быть уникальным.
    fingerprint = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="SHA256 fingerprint of the unique event's key fields."
    )

    # Само тело события в формате JSON.
    event_data = models.JSONField(
        help_text="The full JSON payload of the unique event."
    )

    # Время, когда событие было получено и обработано воркером/консьюмером.
    received_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="Timestamp when the event was processed and saved."
    )

    def __str__(self):
        return f"Event {self.fingerprint[:8]}... received at {self.received_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-received_at']
        verbose_name = "Unique Event"
        verbose_name_plural = "Unique Events"
