import logging


def loggerFunc(logfile=None):
    logging.basicConfig(filename=logfile, filemode="w", level=logging.INFO,
                        format='%(levelname)s - %(module)s ---- %(message)s')

    logger = logging.getLogger("backtest")

    return logger

