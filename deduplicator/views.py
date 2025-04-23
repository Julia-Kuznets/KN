
import json
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

# Импортируем инстанс дедупликатора из settings
event_deduplicator = settings.EVENT_DEDUPLICATOR_INSTANCE
if not event_deduplicator:
    logging.critical("Event Deduplicator не инициализирован!")
    # TODO: Implement fallback strategy if needed

logger = logging.getLogger(__name__)

# csrf_exempt все еще может быть полезен, если нет другой аутентификации/авторизации
@method_decorator(csrf_exempt, name='dispatch')
class EventCheckView(APIView):
    """
    API View для проверки дубликации событий.
    Принимает POST запросы с JSON телом.
    """


    async def post(self, request, *args, **kwargs):
        if not event_deduplicator:
            logger.error("Запрос получен, но дедупликатор не доступен.")
            return Response(
                {"error": "Deduplication service unavailable", "is_duplicate": False},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # DRF автоматически парсит JSON тело в request.data для POST/PUT/PATCH
        event_data_raw = request.data

        # Ожидаем структуру как в примере: список с одним словарем внутри
        if isinstance(event_data_raw, list) and len(event_data_raw) == 1 and isinstance(event_data_raw[0], dict):
            event_data = event_data_raw[0]
        # Или просто один словарь? Обработаем и это.
        elif isinstance(event_data_raw, dict):
             event_data = event_data_raw
             logger.debug("Принят одиночный объект JSON в теле запроса.") # Добавим лог
        else:
             logger.warning(f"Неожиданный формат JSON в теле: {type(event_data_raw)}")
             # DRF обычно сам возвращает 400 Bad Request при невалидном JSON,
             # но мы добавим свою проверку на ожидаемую структуру.
             return Response(
                {"error": "Invalid JSON format in body. Expected a single event object or a list containing one event object."},
                status=status.HTTP_400_BAD_REQUEST
             )

        # Выполняем проверку на дубликацию
        try:
            is_duplicate, fingerprint = await event_deduplicator.check_duplication(event_data)
            logger.info(f"Событие обработано. Fingerprint: {fingerprint}, Is Duplicate: {is_duplicate}")

            return Response(
                {
                    "is_duplicate": is_duplicate,
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
             logger.exception(f"Непредвиденная ошибка при проверке дубликации: {e}")
             return Response(
                 {"error": "Internal server error during deduplication check", "is_duplicate": False},
                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
             )