
import hashlib
import json
from typing import Dict, Any, Optional, List, Tuple
import redis
import logging


logger = logging.getLogger(__name__)

class EventDeduplicator:
    # Принимаем синхронный redis.Redis
    def __init__(self, redis_client: redis.Redis, ttl_seconds: int, key_fields: List[str]):

        # --- ПРОСТАЯ ПРОВЕРКА НА ТИП ---
        if not isinstance(redis_client, redis.Redis):
             logger.warning("redis_client не является экземпляром redis.Redis")


        if not isinstance(ttl_seconds, int) or ttl_seconds <= 0:
            raise ValueError("ttl_seconds должен быть положительным целым числом")
        if not isinstance(key_fields, list) or not all(isinstance(f, str) for f in key_fields):
             raise ValueError("key_fields должен быть списком строк")
        if not key_fields:
             raise ValueError("key_fields не должен быть пустым")

        self.redis = redis_client
        self.ttl = ttl_seconds
        self.key_fields = sorted(key_fields)


    def _generate_fingerprint(self, event_data: Dict[str, Any]) -> Optional[str]:
        try:
            key_data = {field: event_data.get(field) for field in self.key_fields}
            canonical_string = json.dumps(key_data, sort_keys=True, separators=(',', ':'))
            fingerprint = hashlib.sha256(canonical_string.encode('utf-8')).hexdigest()
            return fingerprint
        except Exception as e:
            logger.error(f"Ошибка генерации отпечатка для события {event_data}: {e}")
            return None

    # --- синхронный метод ---
    def check_duplication(self, event_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if not isinstance(event_data, dict):
            logger.warning("Получены невалидные данные события (не словарь)")
            return False, None

        fingerprint = self._generate_fingerprint(event_data)

        if fingerprint is None:
            logger.warning(f"Не удалось сгенерировать отпечаток для: {event_data}")
            return False, None

        redis_key = f"event_dedup:{fingerprint}"

        try:
            # --- СИНХРОННЫЙ ВЫЗОВ redis.set ---
            is_new = self.redis.set(redis_key, "1", ex=self.ttl, nx=True)

            if is_new:
                logger.debug(f"Новое событие зарегистрировано: {fingerprint}")
                return False, fingerprint
            else:
                logger.debug(f"Обнаружен дубль события: {fingerprint}")
                return True, fingerprint
        # Ловим ошибку синхронного клиента
        except redis.RedisError as e:
            logger.error(f"Ошибка Redis при проверке дубликации ({fingerprint}): {e}")
            return False, fingerprint
        except Exception as e:
            logger.exception(f"Неожиданная ошибка в check_duplication ({fingerprint}): {e}")
            return False, fingerprint