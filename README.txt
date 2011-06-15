NAME

	condor_agent[.exe] - A utility for accessing and extending Condor schedulers



SYNOPSIS

	condor_agent[.exe] [options]



DESCRIPTION

CondorAgent is a program that runs beside a Condor scheduler. It provides enhanced access to
scheduler-based data and scheduler actions via a HTTP-based REST interface. The interface
supports gzip compression to reduce the bandwidth needed to transfer large amounts of ClassAd
data by a factor of 10-20x making this interface suitable for querying large quantities of
data over slow network connections.

CondorAgent is deployed as either a shell script wrapped Python program (which requires Python
2.4 or greater) or as a Windows binary (which does not require a local Python installation).



OPTIONS

There are no command line options at present for this tool. All configuration and control of 
CondorAgent is done via Condor configuration settings. Please see the section CONDOR CONFIGURATION
for more information on installing and configuring CondorAgent.



CONDOR CONFIGURATION

To enable the CondorAgent on a scheduler, extract the appropriate CondorAgent package into Condor's
sbin directory (or the bin directory for a Windows installation). Add the following to your local
Condor configuration file to register CondorAgent as a daemon the condor_master process on this
machine will monitor and control:

	CONDOR_AGENT = $(SBIN)/condor_agent/condor_agent
	CONDOR_AGENT_ENVIRONMENT = "CONDOR_BIN_PATH=$(BIN)"
	CONDOR_AGENT_SUBMIT_DIR = "$(LOCAL_DIR)/submit"
	DAEMON_LIST = $(DAEMON_LIST), CONDOR_AGENT
	CONDOR_AGENT_PORT = 8008
	SCHEDD_ATTRS = CONDOR_AGENT_PORT, CONDOR_AGENT_SUBMIT_DIR, $(SCHEDD_ATTRS)

If running on Windows the CONDOR_AGENT line should reference condor_agent.exe instead of condor_agent.

Note that the CONDOR_AGENT_SUBMIT_DIR directory can be any directory on disk into which the job files
can  be written. The above is only a suggested default location. If you do not intend to do submissions
over the REST interface with this CondorAgent installation you can omit this setting.

When making changes to CondorAgent configuration settings it is important to remember to reconfigure
all the Condor daemons on the machine, otherwise the CondorAgent won't see config changes made in
the files.

Reconfigure this Condor installation:

	condor_reconfig -full

Verify that the CondorAgent settings are present:

	condor_status -schedd -l | grep CONDOR_AGENT_PORT

And now start CondorAgent:

	condor_on -subsys CONDOR_AGENT

You can verify the agent is running on this box using curl:

	SCHEDD=`condor_status -schedd -format "%s\n" Name | head -n 1`
	curl http://localhost:8008/condor/schedd/$SCHEDD/jobs

This should return output similar to a `condor_q -l` call.

If you're running a CycleServer instance, it will detect the agent's presence on this scheduling
node and being to fetch job and history information from this node using the CondorAgent after two
polling intervals have completed.

To enable access to historical job information via CondorAgent we recommend the following Condor
settings:

	HISTORY = $(SPOOL)/history
	ENABLE_HISTORY_ROTATION = True
	MAX_HISTORY_LOG = 4000000
	MAX_HISTORY_ROTATIONS = 5

This will ensure that the history log files stay reasonable small and provide about 20-24MB of history (5 backups
plus the original). A job ClassAd is usually less than 4k, so this is over 5000 jobs.



THE REST API

TODO fill in details about the REST API



SEE ALSO

cURL - a command line tool for transferring data with URL syntax
http://curl.haxx.se/



COPYRIGHT

Copyright (C) 2007-2011, Cycle Computing, LLC.



LICENSE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in
compliance with the License.  You may obtain a copy of the License at

	http://www.apache.org/licenses/LICENSE-2.0.txt

Unless required by applicable law or agreed to in writing, software distributed under the License is
distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
