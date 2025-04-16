import json
import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

event_deduplicator = settings.EVENT_DEDUPLICATOR_INSTANCE
if not event_deduplicator:
     logging.critical("Event Deduplicator не инициализирован!")
     # TODO: Implement fallback strategy if needed

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class EventCheckView(APIView):
    """
    API View для проверки дубликации событий.
    Принимает GET запросы с JSON телом.
    """

    def get(self, request, *args, **kwargs):
        if not event_deduplicator:
             logger.error("Запрос получен, но дедупликатор не доступен.")
             return Response(
                 {"error": "Deduplication service unavailable", "is_duplicate": False},
                 status=status.HTTP_503_SERVICE_UNAVAILABLE
             )

        if not request.body:
            logger.warning("Получен GET запрос без тела.")
            return Response(
                {"error": "Request body is missing"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            event_data_raw = json.loads(request.body)

            # Ожидаем структуру как в примере: список с одним словарем внутри
            if isinstance(event_data_raw, list) and len(event_data_raw) == 1 and isinstance(event_data_raw[0], dict):
                event_data = event_data_raw[0]
            elif isinstance(event_data_raw, dict):
                 event_data = event_data_raw
            else:
                 logger.warning(f"Неожиданный формат JSON в теле: {type(event_data_raw)}")
                 return Response(
                    {"error": "Invalid JSON format in body. Expected a single event object or a list containing one event object."},
                    status=status.HTTP_400_BAD_REQUEST
                 )

        except json.JSONDecodeError:
            logger.warning(f"Невалидный JSON получен в теле GET: {request.body[:200]}...")
            return Response(
                {"error": "Invalid JSON in request body"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
             logger.exception(f"Непредвиденная ошибка при обработке тела запроса: {e}")
             return Response(
                 {"error": "Internal server error during request body processing"},
                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
             )



        try:
            is_duplicate, fingerprint = event_deduplicator.check_duplication(event_data)
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


