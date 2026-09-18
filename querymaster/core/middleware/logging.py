import json
import logging

from copy import deepcopy
from uuid import uuid4

from constance import config
from ipware import get_client_ip


logger = logging.getLogger("querymaster")


class LoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        logging_attributes = {
            "request_uri": request.build_absolute_uri(),
            "request_method": request.method,
            "http_referer": request.META.get("HTTP_REFERER", ""),
            "http_user_agent": request.META.get("HTTP_USER_AGENT", ""),
            "ip_address": get_client_ip(request)[0],
            "status_code": None,
        }

        uuid = uuid4()
        logger.info(f"REQ {uuid} {request.path}", extra=logging_attributes)

        response = self.get_response(request)

        response_body = "-"
        if "application/json" in response.get("content-type", "") and hasattr(response, "data"):
            response_body = self._truncate_large_response_body(deepcopy(response.data))

        status_code = response.status_code

        logging_attributes["status_code"] = status_code

        logger.info(f"RESP {uuid} {response_body}", extra=logging_attributes)

        return response

    def _truncate_large_response_body(self, value):
        """
        We are truncating the response body after a certain number of characters to
        keep the logs cleanable, understandable and easy to navigate.
        """

        response_body = json.dumps(value, default=str)
        response_body = f"{response_body[:config.MAX_LOG_BODY_CHARS_LIMIT]}..."
        return response_body
