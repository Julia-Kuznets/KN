
import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from deduplicator.models import UniqueEvent


logger = logging.getLogger(__name__)


DAYS_TO_KEEP = 7

class Command(BaseCommand):
    help = f'Deletes unique events older than {DAYS_TO_KEEP} days from the database.'

    def add_arguments(self, parser):
        # Добавляем опциональный аргумент, чтобы можно было запустить "вхолостую"
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate the deletion process without actually deleting records.',
        )
        # Добавляет аргумент для изменения количества дней
        parser.add_argument(
            '--days',
            type=int,
            default=DAYS_TO_KEEP,
            help=f'Specify the number of days to keep data (default: {DAYS_TO_KEEP}).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        days_to_keep = options['days']

        if days_to_keep < 1:
            raise CommandError("Number of days to keep must be a positive integer.")

        # Рассчитываем пороговую дату
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        formatted_cutoff_date = cutoff_date.strftime('%Y-%m-%d %H:%M:%S %Z')

        self.stdout.write(f"Looking for events received before {formatted_cutoff_date} (older than {days_to_keep} days)...")

        # Формируем запрос на удаление
        events_to_delete = UniqueEvent.objects.filter(received_at__lt=cutoff_date)

        # Считаем количество записей перед удалением
        count = events_to_delete.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No old events found to delete."))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN: Found {count} events older than {days_to_keep} days that would be deleted."))
            logger.warning(f"[Dry Run] Would delete {count} events older than {formatted_cutoff_date}")
        else:
            try:
                self.stdout.write(f"Found {count} events. Proceeding with deletion...")
                # Выполняем удаление
                deleted_count, deleted_details = events_to_delete.delete()


                self.stdout.write(self.style.SUCCESS(f'Successfully deleted {deleted_count} old events.'))
                logger.info(f"Successfully deleted {deleted_count} events older than {formatted_cutoff_date}")
            except Exception as e:
                logger.exception(f"An error occurred during event deletion: {e}")
                raise CommandError(f"Failed to delete old events: {e}")