#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=R0914
# pylint: disable=R0913
# pylint: disable=R0201

"""
Exaplanation: sumo_dashboard_export will take a list of dashboards and export results

Usage:
    $ python  sumo_dashboard_export [ options ]

Style:
    Google Python Style Guide:
    http://google.github.io/styleguide/pyguide.html

    @name           sumo_dashboard_export
    @version        2.00
    @author-name    Rick Jury / Wayne Schmidt
    @author-email   rjury@sumologic.com / wschmidt@sumologic.com
    @license-name   Apache
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
import configparser
import tzlocal
import requests
import pdf2image

try:
    import cookielib
except ImportError:
    import http.cookiejar as cookielib

sys.dont_write_bytecode = 1

MY_CFG = 'undefined'
PARSER = argparse.ArgumentParser(description="""
sumologic_dashboard_export will extract out any and all dashboards you specify
""")

PARSER.add_argument("-a", metavar='<secret>', dest='MY_SECRET', \
                    help="set query authkey (format: <key>:<secret>) ")

PARSER.add_argument("-d", metavar='<dashboard>', dest='DASHBOARDLIST', \
                    action='append', help="set dashboard uid (list format)")

PARSER.add_argument("-f", metavar='<fmt>', default="Pdf", dest='OFORMAT', \
                    help="set query output")

PARSER.add_argument('-c', metavar='<cfgfile>', dest='CONFIG', help='specify a config file')

PARSER.add_argument("-o", metavar='<outdir>', default="/var/tmp/dashboardexport", \
                    dest='CACHED', help="set query output directory")

PARSER.add_argument("-s", metavar='<sleeptime>', default=2, dest='SLEEPTIME', \
                    help="set sleep time to check results")

PARSER.add_argument("-v", type=int, default=0, metavar='<verbose>', \
                    dest='verbose', help="increase verbosity")

ARGS = PARSER.parse_args()

CACHED = ARGS.CACHED

OUTFORMAT = ARGS.OFORMAT

MY_SLEEP = int(ARGS.SLEEPTIME)

RIGHTNOW = datetime.datetime.now()

DATESTAMP = RIGHTNOW.strftime('%Y%m%d')

TIMESTAMP = RIGHTNOW.strftime('%H%M%S')

def resolve_option_variables():
    """
    Validates and confirms all necessary variables for the script
    """

    if ARGS.MY_SECRET:
        (keyname, keysecret) = ARGS.MY_SECRET.split(':')
        os.environ['SUMO_UID'] = keyname
        os.environ['SUMO_KEY'] = keysecret

def resolve_config_variables():
    """
    Validates and confirms all necessary variables for the script
    """

    if ARGS.CONFIG:
        cfgfile = os.path.abspath(ARGS.CONFIG)
        configobj = configparser.ConfigParser()
        configobj.optionxform = str
        configobj.read(cfgfile)

        if ARGS.verbose > 8:
            print('Displaying Config Contents:')
            print(dict(configobj.items('Default')))

        if configobj.has_option("Default", "SUMO_UID"):
            os.environ['SUMO_UID'] = configobj.get("Default", "SUMO_UID")

        if configobj.has_option("Default", "SUMO_KEY"):
            os.environ['SUMO_KEY'] = configobj.get("Default", "SUMO_KEY")

def initialize_variables():
    """
    Validates and confirms all necessary variables for the script
    """

    resolve_option_variables()

    resolve_config_variables()

    try:
        my_uid = os.environ['SUMO_UID']
        my_key = os.environ['SUMO_KEY']

    except KeyError as myerror:
        print(f'Environment Variable Not Set :: {myerror.args[0]}')

    return my_uid, my_key

( sumo_uid, sumo_key ) = initialize_variables()

def resolve_dashboardlist():
    """
    Resolve dashboard list to export
    """
    if ARGS.DASHBOARDLIST:
        dashboardlist = ARGS.DASHBOARDLIST
    else:
        if ARGS.CONFIG:
            cfgfile = os.path.abspath(ARGS.CONFIG)
            configobj = configparser.ConfigParser()
            configobj.optionxform = str
            configobj.read(cfgfile)
            if configobj.has_section("Dashboards"):
                dashboarddict = dict(configobj.items('Dashboards'))
                dashboardlist = list(dashboarddict.keys())
    return dashboardlist

### beginning ###

def main():
    """
    Setup the Sumo API connection, using the required tuple of region, id, and key.
    Once done, then issue the command required
    """

    exporter=SumoApiClient(sumo_uid, sumo_key)

    tzname = str(tzlocal.get_localzone())

    os.makedirs(CACHED, exist_ok=True)

    dashboardlist = resolve_dashboardlist()

    for dashboard in dashboardlist:

        export = exporter.run_export_job(dashboard,timezone=tzname,export_format='Pdf')

        if export['status'] != 'Success':
            print(f'Job: {export["job"]} Status: {export["status"]}')
            sys.exit()

        outputfile = f'{CACHED}/{dashboard}.{OUTFORMAT.lower()}'
        print(f'Writing File: {outputfile}')

        with open(outputfile, "wb") as fileobject:
            fileobject.write(export['bytes'])

    for path in os.listdir(CACHED):
        file_name = os.path.join(CACHED, path)
        print(file_name)
        if os.path.isfile(file_name):
            extension = os.path.splitext(file_name)[1]
            if extension == '.pdf':
                images = pdf2image.convert_from_path(file_name)
                for number, _imageitem in enumerate(images):
                    image_name = file_name.replace('.pdf', '.' + str(number) + '.jpg')
                    images[number].save(image_name, 'JPEG')

### class ###
class SumoApiClient():
    """
    This is defined SumoLogic API Client
    The class includes the HTTP methods, cmdlets, and init methods
    """
    def __init__(self, access_id=sumo_uid, access_key=sumo_key, endpoint=None, \
                 ca_bundle=None, cookie_file='cookies.txt'):
        self.session = requests.Session()
        self.session.auth = (access_id, access_key)
        self.default_version = 'v2'
        self.session.headers = {'content-type': 'application/json', 'accept': '*/*'}
        if ca_bundle is not None:
            self.session.verify = ca_bundle
        cookiejar = cookielib.FileCookieJar(cookie_file)
        self.session.cookies = cookiejar
        if endpoint is None:
            self.endpoint = self._get_endpoint()
        elif len(endpoint) < 3:
            self.endpoint = 'https://api.' + endpoint + '.sumologic.com/api'
        else:
            self.endpoint = endpoint
        if self.endpoint[-1:] == "/":
            raise Exception("Endpoint should not end with a slash character")

    def _get_endpoint(self):
        """
        SumoLogic REST API endpoint changes based on the geo location of the client.
        This method makes a request to the default REST endpoint and resolves the 401 to learn
        the right endpoint
        """
        self.endpoint = 'https://api.sumologic.com/api'
        self.response = self.session.get('https://api.sumologic.com/api/v1/collectors')
        endpoint = self.response.url.replace('/v1/collectors', '')
        return endpoint

    def get_versioned_endpoint(self, version):
        """
        formats and returns the endpoint and version
        """
        return self.endpoint+f'/{version}'

    def delete(self, method, params=None, version=None):
        """
        HTTP delete
        """
        version = version or self.default_version
        endpoint = self.get_versioned_endpoint(version)
        response = self.session.delete(endpoint + method, params=params)
        if 400 <= response.status_code < 600:
            response.reason = response.text
        response.raise_for_status()
        return response

    def get(self, method, params=None, version=None):
        """
        HTTP get
        """
        version = version or self.default_version
        endpoint = self.get_versioned_endpoint(version)
        response = self.session.get(endpoint + method, params=params)
        if 400 <= response.status_code < 600:
            response.reason = response.text
        response.raise_for_status()
        return response

    def get_file(self, method, params=None, version=None, headers=None):
        """
        HTTP get file
        """
        version = version or self.default_version
        endpoint = self.get_versioned_endpoint(version)
        response = self.session.get(endpoint + method, params=params, headers=headers)
        if 400 <= response.status_code < 600:
            response.reason = response.text
        response.raise_for_status()
        return response

    def post(self, method, params, headers=None, version=None):
        """
        HTTP post
        """
        version = version or self.default_version
        endpoint = self.get_versioned_endpoint(version)
        response = self.session.post(endpoint + method, data=json.dumps(params), headers=headers)
        if 400 <= response.status_code < 600:
            response.reason = response.text
        response.raise_for_status()
        return response

    def post_file(self, method, params, headers=None, version=None):
        """
        Handle file uploads via a separate post request to avoid having to clear
        the content-type header in the session.
        Requests (or urllib3) does not set a boundary in the header if the content-type
        is already set to multipart/form-data.  Urllib will create a boundary but it
        won't be specified in the content-type header, producing invalid POST request.
        Multi-threaded applications using self.session may experience issues if we
        try to clear the content-type from the session.  Thus we don't re-use the
        session for the upload, rather we create a new one off session.
        """
        version = version or self.default_version
        endpoint = self.get_versioned_endpoint(version)
        post_params = {'merge': params['merge']}
        with open(params['full_file_path'], 'rb', encoding='utf8') as file_object:
            file_data = file_object.read()
        files = {'file': (params['file_name'], file_data)}
        response = requests.post(endpoint + method, files=files, params=post_params,
                auth=(self.session.auth[0], self.session.auth[1]), headers=headers)
        if 400 <= response.status_code < 600:
            response.reason = response.text
        response.raise_for_status()
        return response

    def put(self, method, params, headers=None, version=None):
        """
        HTTP put
        """
        version = version or self.default_version
        endpoint = self.get_versioned_endpoint(version)
        response = self.session.put(endpoint + method, data=json.dumps(params), headers=headers)
        if 400 <= response.status_code < 600:
            response.reason = response.text
        response.raise_for_status()
        return response

    def dashboards(self, monitors=False):
        """
        Return a list of dashboards
        """
        params = {'monitors': monitors}
        response = self.get('/dashboards', params)
        return json.loads(response.text)['dashboards']

    def dashboard(self, dashboard_id):
        """
        Return details on a specific dashboard
        """
        response = self.get('/dashboards/' + str(dashboard_id))
        return json.loads(response.text)['dashboard']

    def dashboard_data(self, dashboard_id):
        """
        Return data from a specific dashboard
        """
        response = self.get('/dashboards/' + str(dashboard_id) + '/data')
        return json.loads(response.text)['dashboardMonitorDatas']

    def export_dashboard(self,body):
        """
        Export data from a specific dashboard via a defined job
        """
        response = self.post('/dashboards/reportJobs', params=body, version='v2')
        job_id = json.loads(response.text)['id']
        if ARGS.verbose > 5:
            print(f'Started Job: {job_id}')
        return job_id

    def check_export_dashboard_status(self,job_id):
        """
        Check on the status a defined export job
        """
        response = self.get(f'/dashboards/reportJobs/{job_id}/status', version='v2')
        response = {
            "result": json.loads(response.text),
            "job": job_id
        }
        return response

    def get_export_dashboard_result(self,job_id):
        """
        Retrieve the results of a defined export job
        """
        response = self.get_file(f"/dashboards/reportJobs/{job_id}/result", version='v2', \
                                 headers={'content-type': 'application/json', 'accept': '*/*'})
        response = {
            "job": job_id,
            "format": response.headers["Content-Type"],
            "bytes": response.content
        }
        if ARGS.verbose > 5:
            print (f'Returned File Type: {response["format"]}')
        return response

    def define_export_job(self,report_id,timezone="America/Los_Angeles",export_format='Pdf'):
        """
        Define a dashboard export job
        """
        payload = {
            "action": {
                "actionType": "DirectDownloadReportAction"
                },
            "exportFormat": export_format,
            "timezone": timezone,
            "template": {
                "templateType": "DashboardTemplate",
                "id": report_id
                }
        }
        return payload

    def poll_export_dashboard_job(self,job_id,tries=60,seconds=MY_SLEEP):
        """
        Iterate and check on the dashboard export job
        """
        progress = ''
        tried=0

        while progress != 'Success' and tried < tries:
            tried += 1
            response = self.check_export_dashboard_status(job_id)
            progress = response['result']['status']
            if ARGS.verbose > 7:
                print(f'job: {job_id} status: {progress} tries: {tried} sleep: {seconds}')
            time.sleep(seconds)

        if ARGS.verbose > 5:
            print(f'{tried}/{tries} job: {job_id} status: {progress}')

        response['tried'] = tried
        response['seconds'] = tried * seconds
        response['tries'] = tries
        response['max_seconds'] = tries * seconds
        return response

    def run_export_job(self,report_id,timezone="America/Los_Angeles", \
                       export_format='Pdf',tries=30,seconds=MY_SLEEP):
        """
        Run the defined dashboard export job
        """
        payload = self.define_export_job(report_id,timezone=timezone,export_format=export_format)
        job = self.export_dashboard(payload)
        if ARGS.verbose > 7:
            print (f'Running Job: {job}')
        poll_status = self.poll_export_dashboard_job(job,tries=tries,seconds=seconds)
        if poll_status['result']['status'] == 'Success':
            export = self.get_export_dashboard_result(job)
        else:
            print (f'Job Unsuccessful after: {tries} attempts')
            export = {
                'job': job
            }
        export['id'] = report_id
        export['status'] = poll_status['result']['status']
        export['poll_status'] = poll_status
        return export

### class ###

if __name__ == '__main__':
    main()
