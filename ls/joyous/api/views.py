from django.conf import settings

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView

from ls.joyous.models import EventBase
from .serializers import EventSerializer


class EventAPIView(APIView):
    http_method_names = ['get']
    permission_classes = (AllowAny,)

    def get(self, request, *args, date=None, **kwargs):
        """  """

        context = {'status': 'success'}
        context['date'] = date

        return Response(context)


