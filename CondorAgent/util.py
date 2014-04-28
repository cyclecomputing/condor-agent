###### COPYRIGHT NOTICE ########################################################
#
# Copyright (C) 2007-2014, Cycle Computing, LLC.
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

def runCommand(cmd, cwd=None):
    """Run the command and return (stdout, stderr) data"""
    logging.info('Executing cmd "%s" in "%s"'  % (cmd, cwd))
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
    #logging.debug("Created subprocess %i" % proc.pid)
    stdout_value, stderr_value = proc.communicate()
    return (stdout_value, stderr_value)


def runCommand2(cmd, cwd=None):
    """Similar to runCommand, but returns the returncode as well as stdout/err."""
    logging.info('Executing cmd "%s" in "%s"' % (cmd, cwd))
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
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


def readCondorHistory(file, date):
    '''Reads the file backwards until it hits the first job
    whose date is on or before the given date. This is critical because
    the history file is not rotated under Windows while there are any jobs
    running, so it can get very large.  Each item returned is an instance 
    of IncrementalAd.

    Note: due to a bug in the SOAP API, this is much more complicated than
    it needs to be:   https://htcondor-wiki.cs.wisc.edu/index.cgi/tktview?tn=1578

    If jobs are removed by the SOAP API, they can be left in an
    incomplete state.  In this case, the jobs have a CompletionDate of
    0, and an arbitrarily early EnteredCurrentStatus if the job is
    very old (and in fact it could be QDate if the job was idle when
    removed).  This means we cannot stop when we find an
    EnteredCurrentStatus that is too early, but we MUST find a way to
    stop before processing the entire file or we will always read the
    entire file. So this is the compromise:

    When we process each job from the end of the file backwards, we
    always output jobs if either its proper CompletionDate is later
    than the given date or it has CompletionDate=0, and we continue
    processing jobs until we find one whose CompletionDate is too
    early. That indicates we are in the part of the file which is
    earlier than we are looking for, so we are done. (No such
    conclusion can be made about jobs which don't have CompletionDate
    set properly.)  The worst case here is a file consisting solely of
    a large number of removed jobs. In that case, we end up
    re-scanning the whole file each time, until a job completes and
    writes a proper CompletionDate.

    We could work around this one bad case by doing something like
    checking the timestamp of the file, and skipping it if it is
    really old (say, 15 minutes old). At this point, the schedd has
    written out everything it was going to, so we can stop processing
    all those invalid jobs. For now we just do extra work.
    '''
    ad = IncrementalAd()
    part = ''
    offset_re = re.compile("\*\*\* .+ CompletionDate = (\d+)")

    for block in reversed_blocks(file):
        for c in reversed(block):
            if c == '\n' and part:
                line = part[::-1].strip()
                part = ''
                if line.startswith("*** "):
                    if ad.ad:
                        if ad.should_output(date):
                            yield ad
                        else:
                            return

                    ad = IncrementalAd()

                else:
                    ad.include(line)

            part = part + c

    if part:
        line = part[::-1].strip()
        ad.include(line)
        if ad.should_output(date):
            yield ad


def reversed_blocks(file, blocksize=4096):
    "Generate blocks of file's contents in reverse order."
    # Python 2.4 compatibility: use the numeric value for os.SEEK_*
    SEEK_SET = 0 # os.SEEK_SET
    SEEK_END = 2 # os.SEEK_END
    file.seek(0, SEEK_END)
    here = file.tell()
    while 0 < here:
        delta = min(blocksize, here)
        file.seek(here - delta, SEEK_SET)
        yield file.read(delta)
        here -= delta


class IncrementalAd:
    def __init__(self):
        self.ad = {}

    def include(self, line):
        # we put this in a dictionary in part because the condor history file
        # contains duplicates that are filtered out by processing it
        split = line.split(" = ", 1)
        # note: we always want the latest version (there are duplicates in each job in a history file),
        # but we are reading the file backwards so we only keep the "first" found.
        if not split[0] in self.ad:
            self.ad[split[0]] = split[1]

    def should_output(self, date):
        completion_time = int(self.ad.get("CompletionDate", 0))
        return completion_time == 0 or completion_time > date

    def get_text(self):
        result = []
        for k, v in self.ad.iteritems():
            result.append(k + " = " + v)
        return "\n".join(reversed(result)) + "\n"
