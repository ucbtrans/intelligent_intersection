import logging
import logging.config
import os


logging_configured = False
KEYWORDS_FOR_LOGGING = ['id',
                        'name',
                        'direction',
                        'lane_type',
                        'type',
                        'compass',
                        'bearing',
                        'lane_id',
                        'city',
                        'streets',
                        'center_x',
                        'center_y',
                        'size',
                        'crop_radius',
                        'east',
                        'west',
                        'north',
                        'south'
                        ]


def init_logger():
    if os.environ.get("AWS_EXECUTION_ENV"):
        lgr = logging.getLogger()
        lgr.setLevel(logging.DEBUG)
        hndlr = lgr.handlers[0]
        hndlr.setFormatter(logging.Formatter(
            "%(asctime)s %(filename)-15s %(lineno)-4d %(funcName)-25s %(levelname)-7s %(message)s",
            "%Y-%m-%d %H:%M:%S"))
    else:
        logging.config.fileConfig("../logging.ini")
        logger = logging.getLogger()
        logger.info(
            "\n\n---------------------------------------------------------------------------------")
        logger.info("Logging configured\n")

    logging_configured = True


def get_logger():
    if not logging_configured:
        init_logger()

    return logging.getLogger()

