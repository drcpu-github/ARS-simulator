import logging
import sys

def create_logger(name, stdout_level=logging.INFO, file_level=logging.DEBUG):
    logger = logging.getLogger(name)

    logger.setLevel(logging.DEBUG)

    # create a logging format
    formatter = logging.Formatter('%(asctime)s - %(name)-10s - %(levelname)s - %(message)s')

    # create an stdout logger
    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setLevel(stdout_level)
    consoleHandler.setFormatter(formatter)
    logger.addHandler(consoleHandler)

    # create a file logger
    fileHandler = logging.FileHandler("simulation.log")
    fileHandler.setLevel(file_level)
    fileHandler.setFormatter(formatter)
    logger.addHandler(fileHandler)

    return logger
