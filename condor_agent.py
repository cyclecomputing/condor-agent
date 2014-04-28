#!/usr/bin/env python

###### COPYRIGHT NOTICE ########################################################
#
# Copyright (C) 2007-2013, Cycle Computing, LLC.
# 
# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License.  You may
# obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0.txt
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
################################################################################

################################################################################
# USAGE
################################################################################


################################################################################
# IMPORTS
################################################################################

import os
import sys
import exceptions
import re
import logging
import logging.handlers
import signal
import time
import SocketServer
import zlib
import urllib
import CondorAgent.util
import CondorAgent.schedd
import CondorAgent.post_submit
import CondorAgent.post_submit_cleanup

 # Import modules for CGI handling 
import cgi, cgitb 
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

################################################################################
# GLOBALS
################################################################################
__version__ = "1.25"

# URL Patterns for REST Calls
#
# We're using regular expressions for URL pattern matching, not because we want
# to, but because we have to in order to be cross-Python version compatible.
# Most modern, RHEL-based, Linux distros ship with antiquated Python 2.4 and we
# like to be compatible with that version, as well as 2.6 and up. If there's a
# better way to do this that isn't RE-based, we should move to that ASAP. Or
# Linux could stop depending on 2.4...which ever comes first.

# condor_submit URLs

#/condor/submit/             POST => Receives the attached zip file, uncompresses it to a
#                                    specified directory, and then submits the jobs to Condor. 
#                                    Return the cluster ID if the submission was created successfully.  
#'^/condor/submit$'
URL_schedd_SUBMIT = re.compile('^/condor/submit/?(?P<args>/?\?.*|/?)$')

# condor_status URLs

#/condor/schedd/             GET => Return schedd ads from condor_status -schedd -l
#/condor/schedd/#Name/       Get => Return schedd ad from condor_status -schedd -name #Name -l
#'^/condor/schedd/(?P<schedd_name>[^/]*)(?P<args>/?\?.*?|/?)$$'
URL_schedd_STATUS = re.compile('^/condor/schedd/(?P<schedd_name>[^/]*)(?P<args>/?\?.*?|/?)$$')

# job handler condor_q/condor_history urls
#/condor/schedd/#name/jobs/?attr=val&attr2=val2  GET => return ads from condor_q and condor history
#/condor/schedd/#name/jobs/#cluster/ GET => return cluster ads from condor_q or condor_history 
#/condor/schedd/#name/jobs/#cluster/#proc/ GET => return cluster/proc ads from condor_q or history regardless
#'^/condor/schedd/(?P<schedd_name>[^/]*)/jobs/?(?P<cluster_id>[0-9]*)/?(?P<proc_id>[0-9]*)(?P<args>/?\?.*?|/?)$'
URL_schedd_JOBS = re.compile('^/condor/schedd/(?P<schedd_name>[^/]*)/jobs(?P<args>/?\?.*|/?)$')

# Anything you want, that's the way you want it, anything you want...
URL_ANY = re.compile('^.*$')


################################################################################
# CLASSES
################################################################################

class ThreadedHTTPServer(SocketServer.ThreadingMixIn, HTTPServer):
    '''Empty class, semantics.'''
    pass

                                
class CondorAgentHandler(BaseHTTPRequestHandler):
    '''Used to handle RESTful calls to this agent made over HTTP.'''
    
    def __init__(self, request, client_address, server):
        self.submitDir = None
        # List of URL handlers
        # URL handlers take the match_object as input
        self.listURLHandlers=[(URL_schedd_STATUS, self.getScheddStatus),
                              (URL_schedd_JOBS, self.getScheddJobs),
                              (URL_schedd_SUBMIT, self.submit),
                              (URL_ANY, self.getUnrecognizedURL)]
        BaseHTTPRequestHandler.__init__(self, request, client_address, server)
    
    def initializeForSubmissions(self):
        self.submitDir = CondorAgent.util.getCondorConfigVal("CONDOR_AGENT_SUBMIT_DIR")
        if not self.submitDir or self.submitDir == '':
            self.submitDir = os.path.join(os.getcwd(), "submit")
            logging.warning('Unable to find a defined submit directory in the Condor configuration. Using directory: %s' % self.submitDir)
        else:
            self.submitDir = self.submitDir.replace('"', '')
            logging.info("Retrieved submit directory '%s'" % self.submitDir)
        if not os.path.isdir(self.submitDir):
            logging.warning('Unabled to find submit directory %s -- attempting to create it now...' % self.submitDir)
            os.makedirs(self.submitDir)   
    
    def requestAcceptsGZip(self):
        '''Returns True if the requestor can handle a compressed stream.
        Otherwise False.'''
        accepts_gzip = False
        if self.headers.has_key('Accept-Encoding'):
            accepts_gzip = self.headers['Accept-Encoding'].find('gzip') != -1
        return accepts_gzip
    
    def getScheddStatus(self, match_obj):
        # needs to return schedd classad
        raise exceptions.NotImplementedError
    
    def getScheddJobs(self, match_obj):
        matches      = match_obj.groupdict()
        accepts_gzip = self.requestAcceptsGZip()
        daemon       = 'schedd'
        logging.info("Requested Daemon: " + daemon)
        
        schedd_name = urllib.unquote(matches['schedd_name'])
        logging.info("Requested ScheddName: " + schedd_name)   
        
        args = CondorAgent.util.processRequestArgs(matches['args'])
        logging.info("Requested Args: " + str(args))
        
        #Look at arguments to determine when to get jobs from
        completedSince = 0
        if args.has_key('completedSince'):
            logging.info("CompletedSince: %s" % args['completedSince'])
            completedSince = int(args['completedSince'])
        
        history = True
        if args.has_key('history') and args['history'].lower() == 'false':
            logging.info("History will not be returned by request")
            history = False
        else:
            logging.debug("Historical job information will be returned.")
        
        jobs = ""
        # Argument: processes="1.2 2.3 4"
        if args.has_key('jobs'):
            logging.info("jobs in Request: %s\n" % args['jobs'])
            jobs = args['jobs'].strip().strip("\"'").strip()
        else:
            logging.debug("No specific jobs or clusters specified in Request. All jobs' data will be returned.")
        
        query = CondorAgent.schedd.ScheddQuery(schedd_name)
        data  = query.execute(completedSince, jobs, history)
        logging.debug("Retrieved jobs data.")
        
        if accepts_gzip:
            logging.debug("Agent returning gzipped data.")
            data = CondorAgent.util.gzipBuffer(data)
        else:
            logging.debug("Agent returning uncompressed response data.")
        
        logging.debug("Sending response to client.")
        self.send_response(200)
        logging.debug("Sending headers.")
        if accepts_gzip:
            self.send_header('Content-Encoding', 'gzip')
            self.send_header('Content-Length', len(data))
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        logging.debug("Sending response body.")
        self.wfile.write(data)    
        logging.debug("Response complete.")
    
    def submit(self, match_obj):
        if not self.submitDir:
            self.initializeForSubmissions()
        data = CondorAgent.post_submit.do_submit(self, self.submitDir)
        if not data:
            raise Exception('Encountered an unknown error submitting job, no cluster ID was returned')
        logging.debug("Sending response to client.")
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        logging.debug("Sending response body: %s" % str(data))
        self.wfile.write("%s" % str(data))
    
    def getUnrecognizedURL(self, match_obj):
        self.send_response(404)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write("Path '%s' not found" % self.path)
    
    def handle_response(self):
        try:
            try:
                logging.info("Received URL request: " + self.path)
                # Strip off any URL-encoded parameters from the path
                logging.info("Headers: \n%s" %str(self.headers).strip())
                for i in range(len(self.listURLHandlers)):
                    match_obj = self.listURLHandlers[i][0].match(self.path)
                    if match_obj:
                        logging.info( "Matched URL index #%d" %i)
                        self.listURLHandlers[i][1](match_obj)
                        break
                    
            except Exception, e:
                # we construct the response because send_error puts the whole message in the headers
                logging.error('Caught unhandled exception: %s' % str(e))
                try:
                    logging.error('Current working directory: %s' % os.getcwd())
                except Exception, e:
                    logging.error('Unable to determine current working directory!')
                self.send_response(500)
                self.send_header('Content-Type', 'text/plain')
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                self.wfile.write('Error fulfilling request:\n%s\n' % (str(e)))
        except:
            # the HTTPServer base class can hang on uncaught exceptions
            # (case 5090, BaseException does not exist until Python 2.5)
            logging.error("Uncaught exception")
    
    def do_GET(self):
        self.handle_response()
    
    def do_POST(self):
        self.handle_response()
    
    def log_message(self, format, *args):
        # the default is to write to stderr so we override it
        logging.info("%s - - [%s] %s\n" % 
                     (self.address_string(),
                      self.log_date_time_string(),
                      format%args))
    


class Shutdown:
    '''Used to send a shutdown request to its own web service when a signal
    is caught. Python 2.5 does not support a way to shut down the server
    directly.'''
    
    def __init__(self, url):
        self.stop = False
        self.url = url
    
    def shutdown(self):
        self.stop = True
        urllib.urlopen(self.url)
    


################################################################################
# METHODS
################################################################################

def main():
    '''The main method that drives the daemon. Starts an infinite loop that handles
    requests and responses to HTTP-based REST calls.'''

    def cleanShutdown(signal, frame):
        '''A method to handle shutdowns. This is necessary to prevent the agent from
        hanging on a HTCondor shutdown, since the shutdown script sends SIGQUIT
        instead of SIGTERM.'''
 
        logging.info('Received signal %i, shutting down server' % signal)
        print 'Received signal %i, shutting down server' % signal
        server.socket.close()
        sys.exit(0)

    # We need access to the Condor binaries on this machine in order to complete
    # requests and return data. Set up the PATH so we have access to the things
    # we need.
    if not os.environ.has_key("CONDOR_BIN_PATH"):
        os.environ["CONDOR_BIN_PATH"] = "/opt/condor/bin"
    if not os.environ.has_key("CONDOR_CONFIG") and os.name != 'nt':
        # set this as a default, but not under Windows. (Under Windows Condor uses the registry.)
        os.environ["CONDOR_CONFIG"] = "/etc/condor/condor_config"
    if os.environ.has_key("CONDOR_BIN_PATH"):
        os.environ["PATH"] = os.environ["PATH"] + os.pathsep + os.environ["CONDOR_BIN_PATH"]
    
    # Get Log directory from Condor configuration
    log_dir = CondorAgent.util.getCondorConfigVal("LOG")
    
    if not log_dir:
        log_dir = os.getcwd()
    
    # Set up Basic configuration (Python 2.3 compatible)
    logger    = logging.getLogger()
    hdlr      = logging.handlers.RotatingFileHandler(os.path.join(log_dir.strip(), "CondorAgentLog"), maxBytes=20*1024*1024, backupCount=3)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.DEBUG)
    
    try:
        logging.info("\n\nStarting CondorAgent v%s..." % __version__)
        logging.info("Arguments: %s" % str(sys.argv))
        logging.info('Working directory: %s' % os.getcwd())
        
        print "Starting CondorAgent v%s...started." % __version__
        
        try:
            port = CondorAgent.util.getCondorConfigVal("CONDOR_AGENT_PORT")
            logging.info("Retrieved port '%s'" % port)
            port = int(port)
        except:
            port = 8008
            logging.warning('Unable to find valid port in condor configuration, using default %d' % port)
        
        url = "http://localhost:" + str(port) + "/_shutdown"
        shutdown = Shutdown(url)
        
        # Standard ways of killing this in Unix (SIGTERM) work automatically, 
        # but the standard way in Windows (WM_CLOSE) requires careful handling.
        if os.name == 'nt':
            from CondorAgent import win32
            win32.setupShutdownHook(shutdown.shutdown)
        
        print "Waiting for incoming requests on post %d (press ^C to stop)..." % port
        
        # Start web service interface
        server = ThreadedHTTPServer(('', port), CondorAgentHandler)
        logging.info("Created web server at port %d" % port)
        
        # Capture SIGINT and SIGQUIT
        signal.signal(signal.SIGINT,cleanShutdown)
        if os.name != 'nt':
            signal.signal(signal.SIGQUIT,cleanShutdown)
            
        # 1.12: Switch user context to the CONDOR_IDS user before we start polling
        # for things on the port we just opened up. Don't do this on Windows!
        if os.name != 'nt':
            try:
                condor_uid = CondorAgent.util.getCondorUID()
            except KeyError:
                # Couldn't find a UID for Condor on this machine
                logging.warning('Unable to figure out the UID to run as on this host')
                condor_uid = None
            try:
                condor_gid = CondorAgent.util.getCondorGID()
            except KeyError:
                logging.warning('Unable to figure out the GID to run as on this host')
                # Couldn't find a GID for Condor on this machine
                condor_gid = None
            if condor_gid:
                # This may fail if we're not running as root (maybe someone started
                # us in the foreground?). Don't treat failure as a cause to interrupt
                # this daemon. We already created the socket for the server so we
                # should just continue to run as the user we already are...
                try:
                    os.setgid(condor_gid)
                except Exception, e:
                    logging.warning('Unable to change context to GID %d: %s' % (condor_gid, str(e)))
                else:
                    if condor_uid:
                        try:
                            os.setuid(condor_uid)
                        except Exception, e:
                            logging.warning('Unable to change context to UID %d: %s' % (condor_uid, str(e)))
        
        # 1.13: Start a thread to handle cleaning up local Condor submissions if this technology
        # is set to be used in this instance of the Agent. We start the thread after the UID
        # context switch so it runs as the same user that the submissions are being done as. Safer.
        local_submission_enabled = CondorAgent.util.getCondorConfigVal('CONDOR_AGENT_SUBMIT_PROXY')
        #logging.debug('CONDOR_AGENT_SUBMIT_PROXY = %s' % local_submission_enabled)
        if local_submission_enabled and (local_submission_enabled.lower() == 'true'):
            logging.info('Spawning sub-thread to handle local submission cleanup')
            cleanup_thread = CondorAgent.post_submit_cleanup.LocalSubmitCleaner(sleeptime=300)
            if cleanup_thread:
                cleanup_thread.start()
            else:
                logging.error('Unable to create local submission cleanup thread: LocalSubmitCleaner() returned None')
                raise Exception('Unable to create local submission cleanup thread')
        
        while True:
            server.handle_request()
            if shutdown.stop:
                break
        
        # wait for the shutdown request to finish cleanly
        time.sleep(0.5)
    
    except Exception, e:
        logging.error(e)

    logging.info("Server shutdown")


if __name__ == '__main__':
    '''Run the main method if we are being called as a script.'''
    main()

