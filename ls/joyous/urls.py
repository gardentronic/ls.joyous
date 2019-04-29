from django.urls import path, include


app_name = 'ls.joyous'

urlpatterns = (
    path("api/", include('ls.joyous.api.urls', namespace='api')),
)

