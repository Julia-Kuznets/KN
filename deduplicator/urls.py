from django.urls import path
from .views import EventCheckView

urlpatterns = [
    path('check_event/', EventCheckView.as_view(), name='check_event'),
]