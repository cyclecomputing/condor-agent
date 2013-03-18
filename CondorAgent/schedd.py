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
import util
import time
import math
import logging
import os
import glob


################################################################################
# GLOBALS
################################################################################
__doc__ = "CondorAgent Utilities for Condor: Scheduler"

# the number of seconds to allow as overlap to make sure we don't miss any history,
# used when deciding what history files need to be processed
COMPLETED_SINCE_OVERLAP = 5


################################################################################
# CLASSES
################################################################################
class ScheddQuery:
    
    def __init__(self, schedd_name):
        self.scheddName=schedd_name
    
    def execute(self, completed_since, jobs, history):
        # Get timestamp for upcoming condor_history call (this will be the next
        # completedSince), add results from condor_history if appropriate.
        q_data = self.getCurrent(jobs)
        
        if history:
            history_data, new_completed_since = self.getHistory(completed_since, jobs)
            return_time  = "-- CompletedSince: " + str(new_completed_since) + "\n"
            data         = q_data + return_time + history_data
        else:
            data = q_data
        return data
    
    def getCurrent(self, jobs):
        # Get results from condor_q
        q_cmd = 'condor_q -name %s -long %s' % (self.scheddName, jobs)
        logging.info("condor_q command: %s" %q_cmd)
        q_data, err_data = util.runCommand(q_cmd)
        if err_data != '':
            # We really should be checking the return code but that's not available
            raise Exception("Executing condor_q command:\n%s" %err_data)
        return q_data
    
        
    def getHistory(self, completed_since, jobs):
        '''Returns a tuple of history, new_completed_since.  The new value for
        completed_since comes from the last job (with a non-zero
        CompletionDate) that was read. This ensures that the next time
        the client reads we resume from the last value we read in the
        file. (Previously we used the current timestamp.)'''
        new_completed_since = completed_since
        history_file = util.getCondorConfigVal("HISTORY", "schedd", self.scheddName)
        if history_file == None:
            raise Exception("History is not enabled on this scheduler")
        # Case 5458: Consider an empty string value for HISTORY to be the same as None
        # and raise an exception.
        if len(history_file.strip()) == 0 :
            raise Exception("The HISTORY setting is an empty string")
        history_file = os.path.normpath(history_file)
        logging.info("History file for daemon %s: %s"%(self.scheddName, history_file))
        files        = glob.glob(history_file + "*")
        history_data = ''
        for f in files:
            if os.path.isfile(f):
                mod = os.path.getmtime(f)
                # allow for some overlap when testing
                # note: we don't skip the current file based on its timestamp because we don't 
                # want to rely on that being updated properly
                if mod >= (completed_since - COMPLETED_SINCE_OVERLAP) or os.path.normpath(f) == history_file:
                    # each output from condor_history has a trailing newline so we can
                    # just concatenate them
                    if jobs != "":
                        history_data = history_data + self.getItemizedHistoryFromFile(completed_since, jobs, f)
                    else:
                        new_data, new_time = self.getHistoryFromFile(completed_since, f)
                        # keep the latest we've seen
                        new_completed_since = max(new_time, new_completed_since)
                        logging.debug("New CompletedSince: %s" % new_completed_since)
                        history_data = history_data + new_data
                else:
                    logging.info("History file %s was last modified before given completedSince, skipped" % os.path.basename(f))
        return (history_data, new_completed_since)
    
    def getHistoryFromFile(self, completed_since, history_file):
        '''Reads from the history file backwards to just get the changes.
        Returns the text and the latest non-zero CompletionDate found.'''
        f = open(history_file, "rb")
        try:
            ads = list(util.readCondorHistory(f, completed_since))
            jobs = []
            max_completion = 0
            for job in reversed(ads):
                jobs.append(job.get_text())
                # CompletionDate may not be specified, or may appear as 0, both of which are ignored
                max_completion = max(job.ad.get("CompletionDate", 0), max_completion)

            logging.debug("Read %s jobs from history file %s" % (len(jobs), history_file))
            return ("\n".join(jobs) + "\n", max_completion)
        finally:
            f.close()

    def getItemizedHistoryFromFile(self, completed_since, jobs, history_file):
        '''Note: we could modify the above method to take a constraint on jobs,
        and process the list of X.Y Z into a filter. Then we would not need to run condor_history at all.'''
        history_data = ''
        err_data     = ''
        history_cmd = 'condor_history -l -f %s %s' % (history_file, jobs)
        history_data, err_data = util.runCommand(history_cmd)
        if err_data != '':
            raise Exception("Executing condor_history command:\n%s" %err_data)
        return history_data
    

