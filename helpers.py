import logging
from datetime import datetime


def get_logger(name, file=False):
    """
    Logger init function

    :param name:    string             name of current file/module
    :param file:    bool               defines whether to write log in file
    :return:        Logger object      configured logger object
    """
    timestamp = datetime.now().strftime('%m-%d_%H:%M:%S')
    logger = logging.Logger(name)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    if file:
        fh = logging.FileHandler(f'logs/{name}_{timestamp}.log')
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger
