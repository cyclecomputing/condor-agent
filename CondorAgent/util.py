###### COPYRIGHT NOTICE ########################################################
#
# Copyright (C) 2007-2011, Cycle Computing, LLC.
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
import subprocess
import time
import re
import StringIO
import gzip
import urllib
import logging
import os
import string


################################################################################
# GLOBALS
################################################################################
__doc__ = "CondorAgent Utilities for Condor:Utilities"

URL_ATTR_VALUE = re.compile('(?P<attr>.*?)=(?P<value>.*)$')


################################################################################
# CLASSES
################################################################################


################################################################################
# METHODS
################################################################################

def getCondorConfigVal(attr, daemon='', name='', default=None):
    '''Query Condor for a configuration value. Returns the value as a string or
    None if the value cannot be found. If the name of the attribute stars with
    CONDOR_ and cannot be found the command will also try to find the CYCLE_
    equivalent of the configuration value (for backwards compatibility).'''
    
    cycle_attr = string.replace(attr.upper(), 'CONDOR_', 'CYCLE_', 1)
    
    if daemon!='':
        if name!='':
            config_val_cmd = "condor_config_val -%s -name %s %s" %(daemon, name, attr)
        else:
            config_val_cmd = "condor_config_val -%s %s" %(daemon, attr)
    else:
        config_val_cmd = "condor_config_val %s" %(attr)
    try:
        (rc, o, e) = runCommand2(config_val_cmd)
    except Exception, e:
        logging.error('Unable to get value for configuration setting %s:' % (attr, str(e)))
        return None
    
    if o.find('Not defined') > -1 or e.find('Not defined') > -1:
        value = None
    elif len(o) == 0:
        value = None
    else:
        value = o.splitlines()[0]
        
    # If we didn't file the value, and the CONDOR_ -> CYCLE_ substitution happened,
    # try looking for the setting using the CYCLE_ prefix since this may be 
    # running on a scheduler with an old style configuration.
    if (not value or value == '') and cycle_attr != attr:
        value = getCondorConfigVal(cycle_attr, daemon=daemon, name=name, default=None)
        
    # If the user supplied a default value return that instead of None 
    if default and not value:
        value = default
    
    return value

def runCommand(cmd):
    """Run the command and return (stdout, stderr) data"""
    logging.info("Executing cmd: %s" % cmd)
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #logging.debug("Created subprocess %i" % proc.pid)
    stdout_value, stderr_value = proc.communicate()
    return (stdout_value, stderr_value)


def runCommand2(cmd):
    """Similar to runCommand, but returns the returncode as well as stdout/err."""
    logging.info("Executing cmd: %s" % cmd)
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #logging.debug("Created subprocess %i" % proc.pid)
    stdout_value, stderr_value = proc.communicate()
    return_code = proc.returncode
    # Poll until the process finishes.
    while (return_code is None):
        time.sleep(1)
        return_code = proc.returncode
        
    return (return_code, stdout_value, stderr_value)


def getHTTPHeaderTime(epoch_time):
    return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(epoch_time))


def gzipBuffer(buf):
    '''Returns a gzipped version of the input stream. Adds the necessary gzip
    headers to the base zlib compression.'''
    zbuf = StringIO.StringIO()
    zfile = gzip.GzipFile(None, 'wb', 9, zbuf)
    zfile.write(buf)
    zfile.close()
    return zbuf.getvalue()

def processRequestArgs(raw_args):
    '''Return a dictionary of arguments. Where arguments match the
    k=v type style of arguments.'''
    return_args=dict()
    
    if raw_args != '' and raw_args != '/' and (raw_args[0] == '/' or raw_args[0] == '?'):
        if raw_args[0] == '/':
            raw_args = raw_args[1:]
        if raw_args[0] == '?':
            raw_args = raw_args[1:]
        attr_value_pairs = raw_args.split('&')
        for attr_value in attr_value_pairs:
            m = URL_ATTR_VALUE.match(attr_value)
            if m:
                return_args[urllib.unquote(m.group('attr'))] = urllib.unquote(m.group('value'))
    return return_args

def getCondorUID():
    '''Returns the UID that the user expects all Condor daemons
    to be running as. This only works from non-Windows so only
    call it if you are certain you are not on Windows. It will
    return None if it cannot figure out an appropriate UID for
    this daemon to run as. I based this search for a UID to use
    on the information found here:
    http://www.cs.wisc.edu/condor/manual/v7.4/3_3Configuration.html#14439
    '''
    repat = re.compile(r"^\s*(\d+)\.(\d+)", re.IGNORECASE)
    uid = None
    condor_ids = getCondorConfigVal("CONDOR_IDS")
    # Check Condor config files -- maybe they're set there?
    if not condor_ids:
        # Nope. Check the environment -- maybe they're set there?
        if not os.environ.has_key('CONDOR_IDS'):
            # Nope. Is there a 'condor' user on the system?
            import pwd
            uid_entry = pwd.getpwnam('condor')
            if uid_entry:
                uid = uid_entry[2]
        else:
            m = re.search(repat, os.environ.has_key('CONDOR_IDS'))
            if m:
                uid = m.group(1)
    else:
        m = re.search(repat, condor_ids)
        if m:
            uid = m.group(1)
    return int(uid)

def getCondorGID():
    '''Returns the GID that the user expects all Condor daemons
    to be running as. This only works from non-Windows so only
    call it if you are certain you are not on Windows. It will
    return None if it cannot figure out an appropriate GID for
    this daemon to run as. I based this search for a GID to use
    on the information found here:
    http://www.cs.wisc.edu/condor/manual/v7.4/3_3Configuration.html#14439
    '''
    repat = re.compile(r"^\s*(\d+)\.(\d+)", re.IGNORECASE)
    gid = None
    condor_ids = getCondorConfigVal("CONDOR_IDS")
    # Check Condor config files -- maybe they're set there?
    if not condor_ids:
        # Nope. Check the environment -- maybe they're set there?
        if not os.environ.has_key('CONDOR_IDS'):
            # Nope. Is there a 'condor' user on the system?
            import pwd
            uid_entry = pwd.getpwnam('condor')
            if uid_entry:
                gid = uid_entry[3]
        else:
            m = re.search(repat, os.environ.has_key('CONDOR_IDS'))
            if m:
                gid = m.group(2)
    else:
        m = re.search(repat, condor_ids)
        if m:
            gid = m.group(2)
    return int(gid)



def getCondorUsername():
    '''Returns the username that the user expects all Condor daemons
    to be running as. This only works from non-Windows so only
    call it if you are certain you are not on Windows. It will
    return None if it cannot figure out an appropriate UID for
    this daemon to run as.
    '''
    uid = getCondorUID()
    username = None
    if uid:
        import pwd
        uid_entry = pwd.getpwuid(uid)
        if uid_entry:
            username = uid_entry[0]
    return username



    
