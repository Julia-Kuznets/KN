# Generated by Django 5.2 on 2025-04-24 19:15

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='UniqueEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fingerprint', models.CharField(db_index=True, help_text="SHA256 fingerprint of the unique event's key fields.", max_length=64, unique=True)),
                ('event_data', models.JSONField(help_text='The full JSON payload of the unique event.')),
                ('received_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now, help_text='Timestamp when the event was processed and saved.')),
            ],
            options={
                'verbose_name': 'Unique Event',
                'verbose_name_plural': 'Unique Events',
                'ordering': ['-received_at'],
            },
        ),
    ]
