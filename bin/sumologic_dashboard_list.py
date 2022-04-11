#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Exaplanation: sumo_dashboard_list. Show your dashboard ID

Usage:
   $ python  sumo_dashboard_list [ options ]

Style:
   Google Python Style Guide:
   http://google.github.io/styleguide/pyguide.html

    @name           sumo_dashboard_list
    @version        2.00
    @author-name    Wayne Schmidt
    @author-email   wschmidt@sumologic.com
    @license-name   Apache 2.0
    @license-url    https://www.apache.org/licenses/LICENSE-2.0
"""

__version__ = 2.00
__author__ = "Wayne Schmidt (wschmidt@sumologic.com)"

### beginning ###
import json
import os
import sys
import time
import datetime
import argparse
import http
import configparser
import requests

sys.dont_write_bytecode = 1

MY_CFG = 'undefined'
PARSER = argparse.ArgumentParser(description="""
This shows you all of the dashboards you have
""")

PARSER.add_argument("-a", metavar='<secret>', dest='MY_SECRET', \
                    help="set api (format: <key>:<secret>) ")

PARSER.add_argument("-k", metavar='<client>', dest='MY_CLIENT', \
                    help="set key (format: <site>_<orgid>) ")

PARSER.add_argument("-e", metavar='<endpoint>', dest='MY_ENDPOINT', \
                    help="set endpoint (format: <endpoint>) ")

PARSER.add_argument('-c', metavar='<cfgfile>', dest='CONFIG', help='specify a config file')

PARSER.add_argument("-i", "--initialize", action='store_true', default=False, \
                    dest='INITIALIZE', help="initialize config file")

PARSER.add_argument("-t", metavar='<type>', default="personal", dest='foldertype', \
                    help="Specify folder type to look for (default = personal )")

PARSER.add_argument("-v", type=int, default=0, metavar='<verbose>', \
                    dest='verbose', help="specify level of verbose output")

ARGS = PARSER.parse_args()

VARTMPDIR = '/var/tmp'

CFGTAG = 'dashboardexport'

DELAY_TIME = .2

CACHEDIR  = '/var/tmp'

RIGHTNOW = datetime.datetime.now()

DATESTAMP = RIGHTNOW.strftime('%Y%m%d')

TIMESTAMP = RIGHTNOW.strftime('%H%M%S')

FOLDERTYPE = ARGS.foldertype.capitalize()

def initialize_config_file():
    """
    Initialize configuration file, write output, and then exit
    """

    starter_config = os.path.join( VARTMPDIR, ".".join((CFGTAG, "initial.cfg")))
    config = configparser.RawConfigParser()
    config.optionxform = str

    config.add_section('Default')

    cached_input = input ("Please enter your Cache Directory: \n")
    config.set('Default', 'CACHED', cached_input )

    apikey_input = input ("Please enter your Sumo Logic API Key Name: \n")
    config.set('Default', 'SUMOUID', apikey_input )

    apikey_input = input ("Please enter your Sumo Logic API Secret: \n")
    config.set('Default', 'SUMOKEY', apikey_input )

    source_input = input ("Please enter the your Sumo Logic deployment value: \n")
    config.set('Default', 'SUMOEND', source_input )

    with open(starter_config, 'w') as configfile:
        config.write(configfile)
    print('Complete! Written: {}'.format(starter_config))
    sys.exit()

if ARGS.INITIALIZE:
    initialize_config_file()

if ARGS.CONFIG:
    CFGFILE = os.path.abspath(ARGS.CONFIG)
    CONFIG = configparser.ConfigParser()
    CONFIG.optionxform = str
    CONFIG.read(CFGFILE)
    if ARGS.verbose > 8:
        print(dict(CONFIG.items('Default')))

    if CONFIG.has_option("Default", "CACHED"):
        CACHED = os.path.abspath(CONFIG.get("Default", "CACHED"))

    if CONFIG.has_option("Default", "SUMOUID"):
        SUMOUID = CONFIG.get("Default", "SUMOUID")
        os.environ['SUMO_UID'] = SUMOUID

    if CONFIG.has_option("Default", "SUMOKEY"):
        SUMOKEY = CONFIG.get("Default", "SUMOKEY")
        os.environ['SUMO_KEY'] = SUMOKEY

    if CONFIG.has_option("Default", "SUMOEND"):
        SUMOEND = CONFIG.get("Default", "SUMOEND")
        os.environ['SUMO_END'] = SUMOEND

if ARGS.MY_SECRET:
    (MY_APINAME, MY_APISECRET) = ARGS.MY_SECRET.split(':')
    os.environ['SUMO_UID'] = MY_APINAME
    os.environ['SUMO_KEY'] = MY_APISECRET

if ARGS.MY_ENDPOINT:
    os.environ['SUMO_END'] = ARGS.MY_ENDPOINT

try:
    SUMO_UID = os.environ['SUMO_UID']
    SUMO_KEY = os.environ['SUMO_KEY']
    SUMO_END = os.environ['SUMO_END']
except KeyError as myerror:
    print('Environment Variable Not Set :: {} '.format(myerror.args[0]))

### beginning ###

def main():
    """
    Setup the Sumo API connection, using the required tuple of region, id, and key.
    Once done, then issue the command required
    """
    source = SumoApiClient(SUMO_UID, SUMO_KEY, SUMO_END)

    dashboard_output = source.list_dashboards()

    for dashboard_item in dashboard_output['dashboards']:
        dashid = dashboard_item['id']
        dashoid = dashboard_item['contentId']
        dashname = dashboard_item['title']
        print('{},{},{}'.format(dashoid,dashid,dashname))

### class ###
class SumoApiClient():
    """
    This is defined SumoLogic API Client
    The class includes the HTTP methods, cmdlets, and init methods
    """

    def __init__(self, access_id, access_key, region, cookieFile='cookies.txt'):
        """
        Initializes the Sumo Logic object
        """
        self.session = requests.Session()
        self.session.auth = (access_id, access_key)
        self.session.headers = {'content-type': 'application/json', \
            'accept': 'application/json'}
        self.apipoint = 'https://api.' + region + '.sumologic.com/api'
        cookiejar = http.cookiejar.FileCookieJar(cookieFile)
        self.session.cookies = cookiejar

    def delete(self, method, params=None, headers=None, data=None):
        """
        Defines a Sumo Logic Delete operation
        """
        response = self.session.delete(self.apipoint + method, \
            params=params, headers=headers, data=data)
        if response.status_code != 200:
            response.reason = response.text
        response.raise_for_status()
        return response

    def get(self, method, params=None, headers=None):
        """
        Defines a Sumo Logic Get operation
        """
        response = self.session.get(self.apipoint + method, \
            params=params, headers=headers)
        if response.status_code != 200:
            response.reason = response.text
        response.raise_for_status()
        return response

    def post(self, method, data=None, headers=None, params=None):
        """
        Defines a Sumo Logic Post operation
        """
        response = self.session.post(self.apipoint + method, \
            data=json.dumps(data), headers=headers, params=params)
        if response.status_code != 200:
            response.reason = response.text
        response.raise_for_status()
        return response

    def put(self, method, data, headers=None, params=None):
        """
        Defines a Sumo Logic Put operation
        """
        response = self.session.put(self.apipoint + method, \
            data=json.dumps(data), headers=headers, params=params)
        if response.status_code != 200:
            response.reason = response.text
        response.raise_for_status()
        return response

### class ###
### methods ###

    def export_content_results(self, myself, myjobid):
        """
        This should get the results
        """
        url = "/v2/content/" + str(myself) + "/export/" + str(myjobid) + "/result"
        body = self.get(url).text
        results = json.loads(body)
        time.sleep(DELAY_TIME)
        return results

    def export_content_status(self, myself, myjobid):
        """
        This should get the status
        """
        url = "/v2/content/" + str(myself) + "/export/" + str(myjobid) + "/status"
        body = self.get(url).text
        results = json.loads(body)
        time.sleep(DELAY_TIME)
        return results

    def list_dashboards(self):
        """
        Show all of the dashboards
        """
        url = "/v2/dashboards"
        body = self.get(url).text
        results = json.loads(body)
        time.sleep(DELAY_TIME)
        return results

    def list_dashboard(self, myself):
        """
        Show all of the dashboards
        """
        url = "/v2/dashboards/" + str(myself)
        body = self.get(url).text
        results = json.loads(body)
        time.sleep(DELAY_TIME)
        return results

    def export_content(self, myself):
        """
        Launch an export job. This should return a JOBID.
        """
        url = "/v2/content/" + str(myself) + "/export"
        body = self.post(url).text
        results = json.loads(body)
        time.sleep(DELAY_TIME)
        return results

    def get_myfolders(self):
        """
        Using an HTTP client, this uses a GET to retrieve all connection information.
        """
        url = "/v2/content/folders/personal/"
        body = self.get(url).text
        results = json.loads(body)
        return results

    def get_myfolder(self, myself):
        """
        Using an HTTP client, this uses a GET to retrieve single connection information.
        """
        url = "/v2/content/folders/" + str(myself)
        body = self.get(url).text
        results = json.loads(body)
        time.sleep(DELAY_TIME)
        return results

    def get_globalfolders(self):
        """
        Using an HTTP client, this uses a GET to retrieve all connection information.
        """
        url = "/v2/content/folders/global"
        body = self.get(url).text
        results = json.loads(body)
        return results

    def get_globalfolder(self, myself):
        """
        Using an HTTP client, this uses a GET to retrieve single connection information.
        """
        url = "/v2/content/folders/global/" + str(myself)
        body = self.get(url).text
        results = json.loads(body)
        return results

### methods ###

if __name__ == '__main__':
    main()
