import config
from system.shared import mkdir_p

import logging
from logging.handlers import RotatingFileHandler
import os
import sys


def init_logger(mainLoggerName = __name__):
    logger = logging.getLogger(mainLoggerName)

    logsDirPath = os.path.dirname(config.LOG_FILE_PATH)
    if not os.path.exists(logsDirPath):
        if not mkdir_p(logsDirPath):
            print("ERROR INITIALIZING! Can't create directory for logs: '{}'".format(logsDirPath))
            exit(-1)

    # create file handler
    handler = RotatingFileHandler(
        config.LOG_FILE_PATH,
        encoding="utf-8",
        maxBytes=config.MAIN_LOG_FILE_MAX_SIZE,
        backupCount=config.LOG_BACKUPS_COUNT
    )
    handler.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter(config.LOG_FORMAT)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if config.LOG_TO_CONSOLE:
        consoleHandler = logging.StreamHandler(sys.stdout)
        consoleHandler.setLevel(config.APP_LOG_LEVEL)
        consoleHandler.setFormatter(formatter)
        logger.addHandler(consoleHandler)

    logger.setLevel(config.APP_LOG_LEVEL)
    return logger
