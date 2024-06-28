#!/usr/bin/python
# -*- coding: utf-8 -*-

__metaclass__ = type

import logging
import os
import sys
import configparser
import ast
import inspect

try:
    from enum import Enum
except ImportError as error:
    pass

from logging.config import fileConfig
from time import gmtime, strftime

try:
    from .hv_messages import MessageID
    from .ansible_common import get_ansible_home_dir
    from .ansible_common_constants import (
        ANSIBLE_LOG_PATH,
        LOGFILE_NAME,
        LOGGER_LEVEL,
        ROOT_LEVEL,
    )

    HAS_MESSAGE_ID = True
except ImportError as error:
    from .ansible_common import get_ansible_home_dir

    HAS_MESSAGE_ID = False

import logging
import logging.config
import logging.handlers
import os


def setup_logging(logger):
    # Define the log directory and ensure it exists
    os.makedirs(ANSIBLE_LOG_PATH, exist_ok=True)

    # Define the log file path
    log_file = os.path.join(ANSIBLE_LOG_PATH, LOGFILE_NAME)

    # Logging configuration dictionary
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "logfileformatter": {"format": "%(asctime)s - %(levelname)s - %(message)s"},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "logfileformatter",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "": {"level": ROOT_LEVEL, "handlers": ["console"]},  # root logger
            "hv_logger": {
                "level": LOGGER_LEVEL,
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }

    # Apply the logging configuration
    logging.config.dictConfig(logging_config)

    # Manually add RotatingFileHandler to the loggers
    log_handler = logging.handlers.RotatingFileHandler(
        log_file, mode="a", maxBytes=1000000, backupCount=20
    )

    # Use the existing formatter from the configuration
    formatter = logging_config["formatters"]["logfileformatter"]["format"]
    log_handler.setFormatter(logging.Formatter(formatter))

    # Add the handler to the root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(log_handler)

    # Add the handler to the hv_logger
    logger.addHandler(log_handler)


class Log:

    logger = None

    @staticmethod
    def getHomePath():

        # example: "/opt/hitachivantara/ansible"

        path = os.getenv("HV_STORAGE_MGMT_PATH")

        if path is None:
            path = get_ansible_home_dir()
            # raise Exception("Improper environment home configuration, please execute the 'bash' command and try again.")

        if Log.logger:
            msg = "getHomePath={0}".format(path)
            # Log.logger.debug(msg)

        return path

    @staticmethod
    def getLogPath():
        path = os.getenv("HV_STORAGE_MGMT_VAR_LOG_PATH")  # example: "/var/log"

        # if HAS_MESSAGE_ID and path is None:
        #     path = '/var/log/hitachivantara/ansible/storage'
        #     #raise Exception("Improper environment configuration, please execute the 'bash' command and try again.")

        if Log.logger:
            msg = "getHomePath={0}".format(path)
            Log.logger.debug(msg)

        return path

    def __init__(self):

        if not Log.logger:
            Log.logger = logging.getLogger("hv_logger")
            setup_logging(Log.logger)

            self.logger = Log.logger
        self.loadMessageIDs()

    def get_previous_frame_info(self):
        frame = inspect.currentframe()
        outer_frames = inspect.getouterframes(frame)
        if len(outer_frames) > 2:
            # Get the previous frame (two levels up)
            previous_frame = outer_frames[2]
            frame_info = {
                "filename": os.path.basename(previous_frame.filename),
                "funcName": previous_frame.function,
                "lineno": previous_frame.lineno,
            }
            return frame_info
        return None

    def ensure_log_dirs(self, config_file):
        config = configparser.ConfigParser()
        config.read(config_file)

        # Iterate through handlers to find FileHandlers
        for section in config.sections():
            if (
                section.startswith("handler_")
                and config[section]["class"] == "handlers.RotatingFileHandler"
            ):
                # Extract the file path from the args parameter
                args = config.get(section, "args")
                # args is expected to be a string representation of a tuple, e.g., "('logs/app.log', 'a')"
                try:
                    log_file_path = ast.literal_eval(args)[
                        0
                    ]  # Use ast.literal_eval to safely parse the args tuple
                    log_dir = os.path.dirname(log_file_path)
                    os.makedirs(log_dir, exist_ok=True)
                except (ValueError, SyntaxError) as e:
                    raise ValueError(f"Error parsing log file path from args: {args}")

    def writeException(self, exception, messageID=None, *args):
        if isinstance(exception, Exception) is True and messageID is None:
            message = str(
                exception
            )  # if not isinstance(exception, AttributeError) else exception.message
            message = "ErrorType={0}. Message={1}".format(type(exception), message)
        else:
            messageID = self.getMessageIDString(messageID, "E", "ERROR")
            if args:
                messageID = messageID.format(*args)
            message = strftime("%Y-%m-%d %H:%M:%S {} {}", gmtime()).format(
                messageID, exception
            )
        self.logger.error(message)

    def writeAMException(self, messageID, *args):

 
        messageID = self.getMessageIDString(messageID, "E", "ERROR")
        if args:
            messageID = messageID.format(*args)
        msg = "MODULE {0}".format(messageID)
        self.logger.error(msg)

    def writeHiException(self, exception):
        from .hv_exceptions import HiException

        # ....................self.logger.debug("writeHiException")

        if isinstance(exception, HiException):

            # ........................self.writeParam("exception={}",str(exception))

            messageId = exception.messageId
            errorMessage = exception.errorMessage

            # ........................self.writeParam("messageId={}",messageId)
            # ........................self.writeParam("errorMessage={}",str(type(errorMessage)))
            # ........................self.writeParam("errorMessage={}",str(errorMessage))
            # message = exception.errorMessage
            # ........................self.writeParam("errorMessage={}",errorMessage)
            msg = "SDK [{0}] {1}".format(messageId, errorMessage)
            self.logger.error(msg)

    def addHandler(self):
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(levelname)-10s - %(funcName)s - %(message)s"
            )
        )
        handler.setLevel(10)
        self.logger.addHandler(handler)

    def loadMessageIDs(self):
        if Log.getHomePath() is not None:
            resources = os.path.join(Log.getHomePath(), "/messages.properties")
        else:
            resources = "/opt/hitachivantara/ansible/messages.properties"
        self.messageIDs = {}
        if os.path.exists(resources):
            with open(resources) as file:
                for line in file.readlines():
                    (key, value) = line.split("=")
                    self.messageIDs[key.strip()] = value.strip()

    def getMessageIDString(self, messageID, charType, strType):
        if HAS_MESSAGE_ID and isinstance(messageID, MessageID):
            return "[{0}56{1:06X}] {2}".format(
                charType,
                messageID.value,
                self.messageIDs.get(messageID.name, messageID.name),
            )
        else:
            return messageID

    def writeParam(self, messageID, *args):
        if args:
            messageID = messageID.format(*args)
        msg = "PARAM: " + messageID
        self.logger.info(msg)

    def writeInfo(self, messageID, *args):
        frame_info = self.get_previous_frame_info()
        if args:
            messageID = messageID.format(*args)
        msg = (
            f"{frame_info['filename']} - {frame_info['funcName']} - {frame_info['lineno']} - {messageID}"
            if frame_info
            else messageID
        )
        self.logger.info(msg)

    def writeDebug(self, messageID, *args):
        frame_info = self.get_previous_frame_info()
        if args:
            messageID = messageID.format(*args)
        msg = (
            f"{frame_info['filename']} - {frame_info['funcName']} - {frame_info['lineno']} - {messageID}"
            if frame_info
            else messageID
        )
        self.logger.debug(msg)

    def writeError(self, messageID, *args):
        frame_info = self.get_previous_frame_info()
        messageID = self.getMessageIDString(messageID, "E", "ERROR")
        if args:
            messageID = messageID.format(*args)
        msg = (
            f"{frame_info['filename']} - {frame_info['funcName']} - {frame_info['lineno']} - {messageID}"
            if frame_info
            else messageID
        )
        self.logger.error(msg)

    def writeWarning(self, messageID, *args):
        frame_info = self.get_previous_frame_info()
        messageID = self.getMessageIDString(messageID, "W", "WARN")
        if args:
            messageID = messageID.format(*args)
        msg = (
            f"{frame_info['filename']} - {frame_info['funcName']} - {frame_info['lineno']} - {messageID}"
            if frame_info
            else messageID
        )
        self.logger.warning(msg)

    def writeEnter(self, messageID, *args):
        if args:
            messageID = messageID.format(*args)
        msg = "ENTER: " + messageID
        self.logger.info(msg)

    def writeEnterModule(self, messageID, *args):
        if args:
            messageID = messageID.format(*args)
        msg = "ENTER MODULE: " + messageID
        self.logger.info(msg)

    def writeEnterSDK(self, messageID, *args):
        if args:
            messageID = messageID.format(*args)
        msg = "ENTER SDK: " + messageID
        self.logger.info(msg)

    def writeExit(self, messageID, *args):
        if args:
            messageID = messageID.format(*args)
        msg = "EXIT: " + messageID
        self.logger.info(msg)

    def writeExitSDK(self, messageID, *args):
        if args:
            messageID = messageID.format(*args)
        msg = "EXIT SDK: " + messageID
        self.logger.info(msg)

    def writeExitModule(self, messageID, *args):
        if args:
            messageID = messageID.format(*args)
        msg = "EXIT MODULE: " + messageID
        self.logger.info(msg)

    def writeErrorModule(self, messageID, *args):
        messageID = self.getMessageIDString(messageID, "E", "ERROR")

        if args:
            messageID = messageID.format(*args)

        message = messageID
        msg = "MODULE " + messageID
        self.logger.error(msg)

    def writeErrorSDK(self, messageID, *args):
        messageID = self.getMessageIDString(messageID, "E", "ERROR")

        if args:
            messageID = messageID.format(*args)

        message = messageID
        msg = "SDK " + messageID
        self.logger.error(msg)

    def writeException1(self, exception, messageID, *args):
        messageID = self.getMessageIDString(messageID, "E", "ERROR")

        if args:
            messageID = messageID.format(*args)

        message = strftime("%Y-%m-%d %H:%M:%S {} {}", gmtime()).format(
            messageID, exception
        )
        self.logger.error(messageID)
