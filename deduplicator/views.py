
import json
import logging

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny


from .tasks import process_event

logger = logging.getLogger(__name__)



@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def check_event_api(request):
    logger.info("--- Вход в СИНХРОННУЮ API view (check_event_api) ---")

    event_data_raw = request.data
    event_data = None

    # Парсим данные
    if isinstance(event_data_raw, list) and len(event_data_raw) == 1 and isinstance(event_data_raw[0], dict):
        event_data = event_data_raw[0]
    elif isinstance(event_data_raw, dict):
         event_data = event_data_raw
         logger.debug("Принят одиночный объект JSON в теле запроса.")
    else:
         logger.warning(f"Неожиданный формат JSON в теле: {type(event_data_raw)}")
         return Response(
            {"error": "Invalid JSON format in body."},
            status=status.HTTP_400_BAD_REQUEST
         )

    if event_data is None:
        logger.error("Не удалось извлечь event_data из запроса.")
        return Response({"error": "Failed to parse event data"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # --- Отправляем задачу в Celery ---
        process_event.delay(event_data=event_data)
        # ------------------------------------
        logger.info(f"Событие отправлено в очередь для обработки: {str(event_data)[:100]}...")

        return Response({"message": "Event accepted for processing"}, status=status.HTTP_202_ACCEPTED)

    except Exception as e:
         # Ошибка может возникнуть, если Celery брокер недоступен
         logger.exception(f"Ошибка при отправке задачи в Celery: {e}")
         return Response(
             {"error": "Failed to queue event for processing"},
             status=status.HTTP_500_INTERNAL_SERVER_ERROR
         )






