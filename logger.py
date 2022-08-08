import logging
import sys

def get_logging_level(level):
    if level.lower() == "critical":
        return logging.CRITICAL
    elif level.lower() == "error":
        return logging.ERROR
    elif level.lower() == "warning":
        return logging.WARNING
    elif level.lower() == "info":
        return logging.INFO
    elif level.lower() == "debug":
        return logging.DEBUG
    else:
        print("Invalid logging level!")
        sys.exit(1)

def create_logger(name, stdout_level, file_level):
    logger = logging.getLogger(name)

    logger.setLevel(min(get_logging_level(stdout_level), get_logging_level(file_level)))

    # create a logging format
    formatter = logging.Formatter('%(asctime)s - %(name)-10s - %(levelname)s - %(message)s')

    # create an stdout logger
    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setLevel(get_logging_level(stdout_level))
    consoleHandler.setFormatter(formatter)
    logger.addHandler(consoleHandler)

    # create a file logger
    fileHandler = logging.FileHandler("simulation.log")
    fileHandler.setLevel(get_logging_level(file_level))
    fileHandler.setFormatter(formatter)
    logger.addHandler(fileHandler)

    return logger
