import logging

from typing import ClassVar

from health_check.views import MainView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


logger = logging.getLogger("querymaster")


class HealthAPIView(MainView, APIView):
    authentication_classes: ClassVar[list] = []
    permission_classes: ClassVar[list] = []

    def get(self, _request, *_args, **_kwargs):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR if self.errors else status.HTTP_200_OK
        response = self.render_to_response_json(self.plugins, status_code)
        if status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
            logger.info(f"Django health check response: {response.content}")

        return Response(status=response.status_code)
