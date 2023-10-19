# logger module
from enum import Enum
import logging
import logging.handlers as handlers
import os
import sys
import traceback


DEFAULT_LOG_ADDRESS = "/logs"  # /logs
DEFAULT_LOG_PERIOD = "1000"  # positive integer
DEFAULT_LOG_LEVEL = "DEBUG"  # DEBUG/INFO/WARNING/ERROR/CRITICAL


class WHEN(str, Enum):
  SECONDS = "S"
  MINUTES = "M"
  HOURS = "H"
  DAYS = "D"
  MONDAY = "W0"
  TUESDAY = "W1"
  WEDNESDAY = "W2"
  THURSDAY = "W3"
  FRIDAY = "W4"
  SATURDAY = "W5"
  SUNDAY = "W6"
  MIDNIGHT = "midnight"


def build_logger(
  name,
  min_level=logging.DEBUG,
  file_only=False,
  directory=DEFAULT_LOG_ADDRESS,
  rotate_when=WHEN.SUNDAY,
  rotate_interval=1,
):
  try:
    if not name:  # exit on no name
      raise ValueError("Logger must have a name")
    dir = os.path.normpath(directory)
    if os.path.isfile(dir):  # exit if the path is a file
      raise ValueError("Logger directory must be a directory")
    if not os.path.exists(dir):  # create log dir
      os.makedirs(dir)

    log_filename = "{}.log".format(name)
    full_filename = os.path.join(dir, log_filename)
    logger = logging.getLogger(name)
    # Define rotation handler
    file_handler = handlers.TimedRotatingFileHandler(
      full_filename, when=rotate_when, interval=rotate_interval, backupCount=8
    )
    # Define handler for console output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    ## Define formatter
    # Will have to google for info on formatting
    formatter = logging.Formatter(
      "%(asctime)s | %(levelname)-7s| %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    # Add formatter to handlers
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # add handlers to logger
    if logger.hasHandlers():
      logger.handlers.clear()
    logger.addHandler(file_handler)
    if not file_only:
      logger.addHandler(console_handler)  # add this to write to console
    # set min level
    logger.setLevel(min_level)
    return logger
  except Exception:
    print(f'An error occured while creating logger "{name}": {traceback.format_exc()}')
    return None
