from django.urls import path
from .views import check_event_api

urlpatterns = [
    path('check_event/', check_event_api, name='check_event'),
]