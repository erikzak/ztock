#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Performs a trend analysis of daily candlestick patterns for configured
exchanges.
"""
import os
import ztock


def main():
    """
    Reads config, creates trader and runs trading function continuously at
    configured time intervals.
    """
    # Read config
    workspace = os.path.realpath(os.path.dirname(__file__))
    config_file = os.path.join(workspace, "config_analyzer.json")

    # Start trading based on config file
    ztock.analyze(config_file)
    return


if (__name__ == '__main__'):
    main()
