Микросервис Дедупликации Событий (Прототип)

**Статус:** Рабочий прототип. Реализована основная функциональность с использованием асинхронной обработки через очередь задач. Требуется нагрузочное тестирование и возможная оптимизация для production.

Это микросервис на Django, предназначенный для дедупликации входящих продуктовых событий. Он использует архитектуру с очередью задач для асинхронной обработки:

1.  **API Приема:** Легковесный эндпоинт (`/api/v1/check_event/`) принимает события по HTTP POST.
2.  **Очередь Задач:** Принятое событие немедленно отправляется в очередь задач, реализованную с помощью Celery и Redis в качестве брокера. API быстро возвращает ответ `202 Accepted`.
3.  **Воркер:** Отдельный процесс (Celery Worker, запущенный с `eventlet` для совместимости с Windows при разработке) читает события из очереди.
4.  **Дедупликация:** Воркер использует класс `EventDeduplicator` для проверки события на уникальность. Отпечатки событий хранятся в Redis с TTL, настроенным на 7 дней. *(Текущая реализация логики дедупликации синхронная для совместимости с `eventlet`)*.
5.  **Хранение:** Если событие уникальное (не является дубликатом в пределах 7 дней), оно сохраняется в базу данных PostgreSQL для последующего анализа.
6.  **Очистка:** Реализована Django management command (`cleanup_old_events`) для удаления из PostgreSQL событий старше 7 дней.

Эта архитектура позволяет API быстро принимать большое количество событий, а фактическую обработку и дедупликацию выполнять асинхронно, что обеспечивает масштабируемость системы.

## Основные фичи

*   Прием событий через HTTP POST API.
*   Асинхронная обработка событий с использованием Celery и Redis.
*   Дедупликация событий на основе набора ключевых полей с 7-дневным окном (Redis TTL).
*   Сохранение уникальных событий в PostgreSQL.
*   Механизм очистки старых данных (старше 7 дней) из PostgreSQL.
*   Запуск всей системы (Приложение, Воркер, PostgreSQL, Redis) через Docker Compose.

## Технологический стек

*   Python 3.10
*   Django
*   Django REST Framework
*   Celery
*   Redis
*   PostgreSQL
*   Psycopg2
*   Eventlet
*   Docker
*   Docker Compose
*   python-dotenv
*   Uvicorn (для запуска Django приложения)

## Начало работы

### Предварительные требования

*   [Git](https://git-scm.com/)
*   [Docker](https://www.docker.com/products/docker-desktop/)
*   [Docker Compose](https://docs.docker.com/compose/install/) 

### Установка и Запуск (через Docker Compose)

1.  **Клонируйте репозиторий:**
    ```bash
    git clone <https://github.com/Julia-Kuznets/KN.git>
    cd <KN>
    ```

2.  **Создайте файл `.env`:**
    В корневой папке проекта создайте файл `.env` и заполните его необходимыми переменными:
    ```dotenv
    # .env

    # Django settings
    DEBUG=1 # 1 для разработки, 0 для прода
    SECRET_KEY='сгенерируйте_свой_надежный_ключ' # !!! ЗАМЕНИТЕ ЭТО !!!

    # PostgreSQL settings
    POSTGRES_DB=deduplicator_db
    POSTGRES_USER=deduplicator_user
    POSTGRES_PASSWORD=ваш_пароль_для_postgres # !!! ЗАМЕНИТЕ ЭТО !!!
    POSTGRES_HOST=postgres # Имя сервиса в docker-compose.yml

    # Redis settings (Используем имена сервисов из docker-compose.yml)
    REDIS_HOST=redis
    REDIS_PORT=6379
    REDIS_DB_DEDUP=1 # БД для хранения отпечатков дедупликатора

    # Deduplicator settings
    DEDUPLICATOR_TTL_SECONDS=604800 # 7 дней (7 * 24 * 60 * 60)
    
    # Django ALLOWED_HOSTS (обязательно для DEBUG=0)
    # Перечислите через запятую без пробелов IP или домены, с которых разрешен доступ
    DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,<IP_АДРЕС_СЕРВЕРА_ЕСЛИ_ЕСТЬ>


    # POSTGRES_PORT=5432 # Можно добавить, если отличается от стандартного
    ```
    **Важно:** Придумайте надежные `SECRET_KEY` и `POSTGRES_PASSWORD`.

3.  **Установите права на `.env` (рекомендуется на сервере):**
    ```bash
    chmod 600 .env
    ```

4.  **Соберите Docker-образы:**
    ```bash
    docker compose build
    ```

5.  **Примените миграции Django:**
    ```bash
    docker compose run --rm app python manage.py migrate
    ```

6.  **Запустите все сервисы:**
    ```bash
    docker compose up -d
    ```

7.  **Проверьте статус контейнеров:**
    ```bash
    docker ps
    ```
    (Должны быть запущены `deduplicator_postgres`, `deduplicator_redis`, `deduplicator_app`, `deduplicator_worker`).

8.  **Система готова!** API доступен по адресу `http://localhost:8000` (если запускаете локально) или `http://<IP_АДРЕС_СЕРВЕРА>:8000` (если запускаете на сервере).


**Просмотр логов (опционально):**
*   Все логи: `docker-compose logs -f` 
*   Логи приложения (API): `docker-compose logs app`
*   Логи воркера (обработка событий): `docker-compose logs worker`



### Остановка системы

1.  Чтобы остановить все запущенные контейнеры:
    ```bash
    docker-compose down
    ```
    (Данные в PostgreSQL и Redis сохранятся в volumes).

## API Эндпоинт

*   **URL:** `/api/v1/check_event/`
*   **Метод:** `POST`
*   **Headers:**
    *   `Content-Type: application/json`
*   **Тело запроса (Request Body):**
    Ожидается JSON, содержащий данные события (либо объект, либо список с одним объектом):
    ```json
    {
      "event_name": "some_event",
      "userId": "user123",
      "client_id": "client_abc",
      "product_id": null,
      // ... другие поля события ...
    }
    ```
*   **Успешный ответ (Response):**
    *   **`202 Accepted`:** Событие успешно принято и поставлено в очередь на обработку.
        ```json
        {
          "message": "Event accepted for processing"
        }
        ```
*   **Ошибки:**
    *   **`400 Bad Request`:** Невалидный JSON.
    *   **`500 Internal Server Error`:** Ошибка при постановке задачи в очередь (например, Redis недоступен).

## Обработка событий (Воркер)

*   Celery воркер автоматически забирает события из очереди Redis.
*   Проверяет событие на дубликат с помощью Redis (окно 7 дней).
*   **Уникальные события** сохраняются в таблицу `deduplicator_uniqueevent` в PostgreSQL.
*   **Дубликаты** просто игнорируются (логируются).
*   Логи работы воркера можно посмотреть командой `docker-compose logs worker`.

## Очистка старых данных

*   Реализована Django management command для удаления событий старше 7 дней из PostgreSQL.
*   **Запуск вручную (внутри контейнера `app`):**
    ```bash
    # Сначала проверка (без удаления)
    docker-compose exec app python manage.py cleanup_old_events --dry-run --days 7

    # Реальное удаление
    docker-compose exec app python manage.py cleanup_old_events --days 7
    ```
*   *Примечание:* В production-среде эту команду нужно настроить на автоматический запуск по расписанию (например, через cron).

##  Тестирование

Используйте инструменты типа Postman, Insomnia или curl для отправки POST-запросов.
Пример с curl:
```
curl -X POST http://<АДРЕС_СЕРВЕРА_ИЛИ_LOCALHOST>:8000/api/v1/check_event/ \
-H "Content-Type: application/json" \
-d '{"event_name": "test", "userId": "u1", "client_id": "c1", "product_id": "p1"}'
```
---