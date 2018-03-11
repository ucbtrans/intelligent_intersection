#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides city level functions
#
#######################################################################


def get_city_name_from_address(address):
    """
    Extract city name from a string like  "San Pablo and University, Berkeley, California",
    :param address: string
    :return: string
    """

    if ',' not in address:
        return None

    return ','.join(address.split(',')[1:]).strip()
