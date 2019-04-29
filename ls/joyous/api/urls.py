from django.urls import path, register_converter

from . import converters, views

register_converter(converters.EventDayConverter, 'eventdate')

app_name = 'ls.joyous'

urlpatterns = (
    path("events/<eventdate:date>/", views.EventAPIView.as_view(), name="events"),
)
