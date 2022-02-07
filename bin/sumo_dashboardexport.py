#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Exaplanation: sumo_dashboardexport will take a list of dashboards and export results

Usage:
    $ python  sumo_dashboardexport [ options ]

Style:
    Google Python Style Guide:
    http://google.github.io/styleguide/pyguide.html

    @name           sumo_dashboardexport
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
import argparse
import time
import requests

try:
    import cookielib
except ImportError:
    import http.cookiejar as cookielib

sys.dont_write_bytecode = 1

MY_CFG = 'undefined'
PARSER = argparse.ArgumentParser(description="""
run_query is a Sumo Logic cli cmdlet managing queries
""")

PARSER.add_argument("-a", metavar='<secret>', dest='MY_APIKEY', \
                    required=True, help="set query authkey (format: <key>:<secret>) ")
PARSER.add_argument("-d", metavar='<dashboard>', dest='DASHBOARDLIST', \
                    action='append', required=True, help="set dashboard uid (list format)")
PARSER.add_argument("-f", metavar='<fmt>', default="Pdf", dest='OFORMAT', \
                    help="set query output")
PARSER.add_argument("-o", metavar='<outdir>', default="/var/tmp/dashboardexport", \
                    dest='OUTPUTDIR', help="set query output directory")
PARSER.add_argument("-s", metavar='<sleeptime>', default=2, dest='SLEEPTIME', \
                    help="set sleep time to check results")
PARSER.add_argument("-v", type=int, default=0, metavar='<verbose>', \
                    dest='VERBOSE', help="increase verbosity")

ARGS = PARSER.parse_args()

DASHBOARDLIST = ARGS.DASHBOARDLIST

OUTPUTDIR = ARGS.OUTPUTDIR

OUTFORMAT = ARGS.OFORMAT

MY_SLEEP = int(ARGS.SLEEPTIME)

VERBOSE = ARGS.VERBOSE

(SUMO_UID, SUMO_KEY) = ARGS.MY_APIKEY.split(':')

### beginning ###

def main():
    """
    Setup the Sumo API connection, using the required tuple of region, id, and key.
    Once done, then issue the command required
    """

    exporter=SumoApiClient(SUMO_UID, SUMO_KEY)

    for dashboard in DASHBOARDLIST:
        export = exporter.run_export_job(dashboard,timezone="Asia/Tokyo",exportFormat='Pdf')

        if export['status'] != 'Success':
            print('Job: {} Status: {}'.format({export['job']}, {export['status']}))
        else:
            os.makedirs(OUTPUTDIR, exist_ok=True)

        outputfile = "{dir}/{file}.{ext}".format(dir=OUTPUTDIR, \
                                                 file=dashboard,ext=OUTFORMAT.lower())
        print('Writing File: {}'.format(outputfile))

        with open(outputfile, "wb") as fileobject:
            fileobject.write(export['bytes'])


### class ###
class SumoApiClient():
    """
    This is defined SumoLogic API Client
    The class includes the HTTP methods, cmdlets, and init methods
    """
    def __init__(self, accessId=SUMO_UID, accessKey=SUMO_KEY, endpoint=None, caBundle=None, cookieFile='cookies.txt'):
        self.session = requests.Session()
        self.session.auth = (accessId, accessKey)
        self.default_version = 'v2'
        self.session.headers = {'content-type': 'application/json', 'accept': '*/*'}
        if caBundle is not None:
            self.session.verify = caBundle
        cookiejar = cookielib.FileCookieJar(cookieFile)
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
        return self.endpoint+'/%s' % version

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
        file_data = open(params['full_file_path'], 'rb').read()
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
        if VERBOSE > 5:
            print('Started Job: {}'.format(job_id))
        return job_id

    def check_export_dashboard_status(self,job_id):
        """
        Check on the status a defined export job
        """
        response = self.get('/dashboards/reportJobs/%s/status' % (job_id), version='v2')
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
        if VERBOSE > 5:
            print ('Returned File Type: {}'.format(response['format']))
        return response

    def define_export_job(self,report_id,timezone="America/Los_Angeles",exportFormat='Pdf'):
        """
        Define a dashboard export job
        """
        payload = {
            "action": {
                "actionType": "DirectDownloadReportAction"
                },
            "exportFormat": exportFormat,
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
            time.sleep(seconds)

        if VERBOSE > 5:
            print('{}/{} job: {} status: {}'.format(tried, tries, \
                                                    job_id, response['result']['status']))

        response['tried'] = tried
        response['seconds'] = tried * seconds
        response['tries'] = tries
        response['max_seconds'] = tries * seconds
        return response

    def run_export_job(self,report_id,timezone="America/Los_Angeles",exportFormat='Pdf',tries=30,seconds=MY_SLEEP):
        """
        Run the defined dashboard export job
        """
        payload = self.define_export_job(report_id,timezone=timezone,exportFormat=exportFormat)
        job = self.export_dashboard(payload)
        if VERBOSE > 7:
            print ('Running Job: {}'.format(job))
        poll_status = self.poll_export_dashboard_job(job,tries=tries,seconds=seconds)
        if poll_status['result']['status'] == 'Success':
            export = self.get_export_dashboard_result(job)
        else:
            print ('Job Unsuccessful after: {} attempts'.format(tries))
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
