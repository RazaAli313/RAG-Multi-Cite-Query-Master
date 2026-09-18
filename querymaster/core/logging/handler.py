import json

from logging.handlers import RotatingFileHandler


class LoggingHandler(RotatingFileHandler):
    def emit(self, record):
        msg = self.format(record)

        data = {
            "logger": {
                "name": record.name,
            },
            "error": {},
            "http": {},
            "user": {},
            "message": msg,
            "code": {
                "file_path": record.pathname,
                "function_name": record.funcName,
                "line_no": record.lineno,
            },
            "process": {
                "id": record.process,
                "name": record.processName,
            },
            "thread": {
                "id": record.thread,
                "name": record.threadName,
            },
        }

        if record.exc_info:
            data["error"]["type"] = record.exc_info[0].__name__
            data["error"]["value"] = str(record.exc_info[1])
            data["error"]["traceback"] = record.exc_text

        try:
            data["http"]["uri"] = record.request_uri
            data["http"]["method"] = record.request_method
            data["http"]["referer"] = record.http_referer
            data["http"]["useragent"] = record.http_user_agent
            data["user"]["ip"] = record.ip_address
            data["http"]["status_code"] = record.status_code
        except AttributeError:
            pass

        record.msg = json.dumps(data)
        record.args = ()

        try:
            if self.shouldRollover(record):
                self.doRollover()

            super().emit(record)
        except Exception:
            self.handleError(record)
