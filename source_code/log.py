#!/usr/bin/env python
# -*- coding: utf-8 -*-

#######################################################################
#
#   This module support logging
#
#######################################################################


import logging
import logging.config
from cloghandler import ConcurrentRotatingFileHandler

LOGGING_INI = 'logging.ini'
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

def init_logger(force=False):

    global logging_configured

    if not force and logging_configured:
        return

    logging.config.fileConfig(LOGGING_INI)
    logging_configured = True
    logger = get_logger()
    logger.info("\n\n-------------------------------------------------------------------------------------------------")
    logger.info("Logging configured\n")


def get_logger():
    """
    Get logger
    :return: logger
    """
    if not logging_configured:
        init_logger()

    return logging.getLogger()


def dictionary_to_log(d, keywords_for_logging=KEYWORDS_FOR_LOGGING):
    """
    Prepare dictionary vital parameters for logging
    :param d:
    :param keywords_for_logging: list of dictionary keywords to log
    :return: string
    """
    result = ''
    if d is not None:
        for key in keywords_for_logging:
            if key in d:
                try:
                    if key == 'direction' or key == 'type':
                        result = result + d[key] + ' '
                    elif key == 'city':
                        result = result + d['city'].split(',')[0] + ' '
                    else:
                        result = result + ("%s=%s " % (key, str(d[key])))
                except UnicodeEncodeError:
                    continue

    return result
