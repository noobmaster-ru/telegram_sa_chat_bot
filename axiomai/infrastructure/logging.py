import json
import logging
from typing import override


class JsonFormatter(logging.Formatter):
    @override
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "filename": record.filename,
            "lineno": record.lineno,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(*, json_logs: bool = False) -> None:
    if json_logs:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logging.basicConfig(
            level=logging.INFO,
            handlers=[handler],
        )
    else:
        logging.basicConfig(
            level=logging.DEBUG,
            format="[%(asctime)s] #%(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s",
        )
