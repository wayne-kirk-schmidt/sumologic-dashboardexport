#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Explanation:

This will walk the client through a set of questions to create a config file.

Usage:
    $ python  genconfig [ options ]

Style:
    Google Python Style Guide:
    http://google.github.io/styleguide/pyguide.html

    @name           genconfig
    @version        1.9.0
    @author-name    Wayne Schmidt
    @author-email   wschmidt@sumologic.com
    @license-name   GNU GPL
    @license-url    http://www.gnu.org/licenses/gpl.html
"""

__version__ = '1.9.0'
__author__ = "Wayne Schmidt (wschmidt@sumologic.com)"

import argparse
import configparser
import datetime
import os
import sys

sys.dont_write_bytecode = 1

PARSER = argparse.ArgumentParser(description="""
Generates a Sumo Logic/Recorded Future Integration Config File
""")

PARSER.add_argument('-c', metavar='<cfgfile>', dest='CONFIG', \
                    default='recorded_future.initial.cfg', help='specify a config file')

PARSER.add_argument("-i", "--initialize", action='store_true', default=False, \
                    dest='INITIALIZE', help="initialize config file")

ARGS = PARSER.parse_args(args=None if sys.argv[1:] else ['--help'])

DASHBOARDS = dict()
DASHBOARDLIST = list()

SRCTAG = 'dashboardexport'

CURRENT = datetime.datetime.now()
DSTAMP = CURRENT.strftime("%Y%m%d")
TSTAMP = CURRENT.strftime("%H%M%S")

LSTAMP = DSTAMP + '.' + TSTAMP

if os.name == 'nt':
    VARTMPDIR = os.path.join ( "C:\\", "Windows", "Temp" )
else:
    VARTMPDIR = os.path.join ( "/", "var", "tmp" )

def collect_config_info(config):
    """
    Collect information to populate the config file with
    """

    config.add_section('Default')

    sumo_uid_input = input ("Please enter your Sumo Logic API Key Name: \n")
    config.set('Default', 'SUMO_UID', sumo_uid_input )

    sumo_key_input = input ("Please enter your Sumo Logic API Key String: \n")
    config.set('Default', 'SUMO_KEY', sumo_key_input )

    print('Please enter the dashboardid:dashboardname you want to export')
    print('When you enter "DONE" at any time, then the collection is done.')

    config.add_section('Dashboards')

    dashboard_input = ''
    while dashboard_input != 'DONE':
        dashboard_input = input ("Dashboard_Name_and_Id: \n")
        DASHBOARDLIST.append(dashboard_input)

    for dashboardstring in DASHBOARDLIST:
        if dashboardstring != 'DONE':
            dash_key, dash_value = dashboardstring.split(":")
            config.set('Dashboards', dash_key, dash_value )

def persist_config_file(config):
    """
    This is a wrapper to persist the configutation files
    """

    starter_config = os.path.join( VARTMPDIR, SRCTAG + ".initial.cfg")

    with open(starter_config, 'w') as configfile:
        config.write(configfile)

    print('Written script config: {}'.format(starter_config))

def display_config_file():
    """
    This is a wrapper to display the configuration file
    """
    cfg_file = os.path.abspath(ARGS.CONFIG)
    if os.path.exists(cfg_file):
        my_config = configparser.ConfigParser()
        my_config.optionxform = str
        my_config.read(cfg_file)
        print('### Contents: {} ###\n'.format(cfg_file))
        for cfgitem in dict(my_config.items('Default')):
            cfgvalue = my_config.get('Default', cfgitem)
            print('{} = {}'.format(cfgitem, cfgvalue))
    else:
        print('Unable to find: {}'.format(cfg_file))

def main():
    """
    This is a wrapper for the configuration file generation routine
    """

    if ARGS.INITIALIZE is False:

        display_config_file()

    else:

        config = configparser.RawConfigParser()
        config.optionxform = str

        collect_config_info(config)

        persist_config_file(config)

if __name__ == '__main__':
    main()
