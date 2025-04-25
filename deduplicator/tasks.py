
import logging
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from .models import UniqueEvent
try:
    import redis
except ImportError:
    pass

logger = logging.getLogger(__name__)

event_deduplicator = settings.EVENT_DEDUPLICATOR_INSTANCE

if not event_deduplicator:
    logger.critical("!!! Воркер Celery: Event Deduplicator не инициализирован при импорте tasks.py !!!")
else:
    logger.info("Воркер Celery: Event Deduplicator успешно получен из settings.")


@shared_task(bind=True, ignore_result=True)
def process_event(self, event_data):
    """
    Задача Celery для обработки и дедупликации события.
    Сохраняет уникальные события в БД PostgreSQL.
    Выполняется синхронно, но конкурентно с помощью eventlet.
    """
    task_id = self.request.id
    logger.info(f"[Task ID: {task_id}] Получено событие для обработки: {str(event_data)[:100]}...")

    # --- ДОБАВИЛИ ЛОГ ПРОВЕРКИ НАСТРОЕК БД СЮДА ---
    try:
        db_settings = settings.DATABASES.get('default', {})
        logger.info(
            f"[Task ID: {task_id}] Задача видит настройки БД: ENGINE={db_settings.get('ENGINE')}, HOST={db_settings.get('HOST')}, NAME={db_settings.get('NAME')}")
    except Exception as e:
        logger.error(f"[Task ID: {task_id}] Задача не может получить настройки БД: {e}")
    # ---------------------------------------------

    if not event_deduplicator:
        logger.error(f"[Task ID: {task_id}] Дедупликатор не доступен, обработка прервана.")
        return

    if not isinstance(event_data, dict):
        logger.warning(f"[Task ID: {task_id}] Получены некорректные данные (не словарь): {type(event_data)}. Задача пропущена.")
        return

    try:
        logger.debug(f"[Task ID: {task_id}] Вызов event_deduplicator.check_duplication...")
        is_duplicate, fingerprint = event_deduplicator.check_duplication(event_data)
        logger.debug(f"[Task ID: {task_id}] Вызов check_duplication завершен.")

        if is_duplicate:
            logger.info(f"[Task ID: {task_id}] Обнаружен дубль события. Fingerprint: {fingerprint}")
        else:
            logger.info(f"[Task ID: {task_id}] Уникальное событие обработано. Fingerprint: {fingerprint}")

            # --- БЛОК СОХРАНЕНИЯ В БД ---
            try:
                # Создаем и сохраняем объект в БД
                UniqueEvent.objects.create(
                    fingerprint=fingerprint,
                    event_data=event_data
                )
                logger.info(f"[Task ID: {task_id}] Уникальное событие СОХРАНЕНО в БД. Fingerprint: {fingerprint}")
            except Exception as db_err:
                # Ловим возможные ошибки БД
                logger.exception(f"[Task ID: {task_id}] Ошибка при сохранении события в БД (Fingerprint: {fingerprint}): {db_err}")

            # -----------------------------------------

    except redis.RedisError as redis_err:
         logger.error(f"[Task ID: {task_id}] Ошибка Redis при обработке события: {redis_err}.")
    except Exception as e:
        logger.exception(f"[Task ID: {task_id}] Непредвиденная ошибка при обработке события: {e}")