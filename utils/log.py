import logging.config
import sys
from os.path import dirname

__all__ = ["logger"]

config = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {
        "bili_spider": {
            "level": "DEBUG",
            "handlers": ["console", "file"]
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "generic",
            "level": "INFO",
            "stream": sys.stderr,
        },
        "file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "formatter": "generic",
            "filename": dirname(__file__) + "/../logs/app.log",
            "when": "M",
            "interval": 1,
            "backupCount": 10,
            "encoding": "utf-8"
        }
    },
    "formatters": {
        "generic": {
            "format": "[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(process)d] [%(filename)s:%(lineno)d] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "class": "logging.Formatter",
        }
    }
}

logging.config.dictConfig(config)
logger = logging.getLogger("bili_spider")