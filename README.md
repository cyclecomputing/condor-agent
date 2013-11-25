# CondorAgent

A utility for accessing and extending Condor schedulers.

CondorAgent is a program that runs beside a [Condor][condor] scheduler. It provides enhanced access to scheduler-based data and scheduler actions via a HTTP-based REST interface. The interface supports gzip compression to reduce the bandwidth needed to transfer large amounts of ClassAd data by a factor of 10-20x making this interface suitable for querying large quantities of data over slow network connections.

CondorAgent is deployed as either a shell script wrapped Python program (which requires Python 2.4 or greater) or as a Windows binary (which does not require a local Python installation).

## Options

There are no command line options at present for this tool. All configuration and control of CondorAgent is done via Condor configuration settings. Please see the section *CONDOR CONFIGURATION* for more information on installing and configuring CondorAgent.

## Condor Configuration

To enable the CondorAgent on a scheduler, extract the appropriate CondorAgent package into Condor's sbin directory (or the bin directory for a Windows installation). Add the following to your local Condor configuration file to register CondorAgent as a daemon the condor_master process on this machine will monitor and control:

	CONDOR_AGENT = $(SBIN)/condor_agent/condor_agent
	CONDOR_AGENT_ENVIRONMENT = "CONDOR_BIN_PATH=$(BIN)"
	CONDOR_AGENT_SUBMIT_DIR = "$(LOCAL_DIR)/submit"
	DAEMON_LIST = $(DAEMON_LIST), CONDOR_AGENT
	CONDOR_AGENT_PORT = 8008
	SCHEDD_ATTRS = CONDOR_AGENT_PORT, CONDOR_AGENT_SUBMIT_DIR, $(SCHEDD_ATTRS)

If running on Windows the `CONDOR_AGENT` line should reference condor_agent.exe instead of condor_agent.

Note that the `CONDOR_AGENT_SUBMIT_DIR` directory can be any directory on disk into which the job files can  be written. The above is only a suggested default location. If you do not intend to do submissions over the REST interface with this CondorAgent installation you can omit this setting.

When making changes to CondorAgent configuration settings it is important to remember to reconfigure all the Condor daemons on the machine, otherwise the CondorAgent won't see config changes made in the files.

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

If you're running a [CycleServer][cycleserver] instance version 4.0.3 or earlier you will need to add some additional Condor configuration in order for CycleServer to detect the agent's presence on this scheduling node and being to fetch job and history information from this node using the CondorAgent after two polling intervals have completed.

Add the following configuration in the case where CycleServer is in use:

	CYCLE_AGENT_PORT = $(CONDOR_AGENT_PORT)
	SCHEDD_ATTRS = CYCLE_AGENT_PORT, $(SCHEDD_ATTRS)

To enable access to historical job information via CondorAgent we recommend the following Condor settings:

	HISTORY = $(SPOOL)/history
	ENABLE_HISTORY_ROTATION = True
	MAX_HISTORY_LOG = 4000000
	MAX_HISTORY_ROTATIONS = 5

This will ensure that the history log files stay reasonable small and provide about 20-24MB of history (5 backups plus the original). A job ClassAd is usually less than 4k, so this is over 5000 jobs.

## The Submission Proxy

The CondorAgent instance on a machine can act as a submission proxy for Condor jobs, allowing you to perform "remote" submissions to Condor over a REST-HTTP interface without having to rely on the Condor SOAP API or the `condor_submit -remote` command line submission approach. This approach provides some of the convenience of the programmatic SOAP API to the Condor scheduler with some of the speed of the batch processing that occurs when submitting locally using the `condor_q` command.

To enable proxy submissions on a scheduling machine add the following to the Condor configuration on the machine:

	CONDOR_AGENT_SUBMIT_PROXY = True
	CONDOR_AGENT_SUBMIT_DIR = $(LOCAL_DIR)/submit

The submission dir is local scratch space that is used for the submission ticket and some log stubs that Condor requires exist during the lifetime of the job. It should be on disk that's local to the system and not remote mounted. Issues with remote mounted submission scratch space have been reported with the beta release of this feature.

To turn the feature on:

	condor_restart -subsys CYCLE_AGENT
	condor_reconfig -full -schedd

If you're using CycleServer as your job submission interface it will now use the proxy submission API on the Agent to place jobs in to any scheduler running on this machine. For information on how to access the submission API please see THE REST API section for the */condor/submit* URL.

## The REST API

### /condor/submit

The submission API lets you perform local-type Condor submissions using a remotely-accessing HTTP interface. It is a much faster interface for queuing large quantities of jobs than the SOAP API that ships with Condor as it leverages the batching semantics inherent in `condor_submit` and does not need to retransmit data for every single job in a cluster as the SOAP API requires.

The interface handles POST messages. It expects the body of the post to be of type Application/Zip and the payload to be a zip file that contains a single *.sub file to be used for the submission. The submission is performed without any modifications to the *.sub file found in the body of the POST. It is a local submission, so you will need to ensure that your submission file is setup accordingly.

The API has one option: the queue to use on the machine for the submission. This option exists to support multi-schedd scenarios where more than one condor_schedd may be started on a machine at a time.

#### Example:

This example uses [curl][] to POST a new submission to a Linux-based scheduler using the REST API.

We have a file on disk, submit.sub, that contains the following:
	
	universe   = vanilla
	executable = /bin/sleep
	arguments  = "3m"
	# Use a network-mounted home directory as the starting and end
	# point for the job...
	iwd        = /net/home/condor/jobs/sleeper
	output     = out.txt
	error      = err.txt
	queue 1

We'll need to compress this file in to a zip file for transport:
	
	zip submit.zip submit.sub
	
Now we can post it to our Condor Agent running on port 8008 on machine 'myschedd':
	
	CLUSTERID = `curl -X POST -H "Content-Type: application/zip" --data-binary 	@submit.zip "http://myschedd:8008/condor/submit?queue=myschedd`
		
On success the API returns a 200 message with the new cluster ID of the submission as the body of the message. In the example above this cluster ID is now stored in the environment variable $CLUSTERID for future use. On failure you'll get a 500 return code from the web server and the body of the message will contain failure analysis information showing you what went wrong with the submission.
	
We can query the system for information about this job now with:
	
	condor_q -name myschedd $CLUSTERID	
	
## See Also

* [Condor][condor] - high throughput computing from the University of Wisconsin
* [curl][] - a command line tool for transferring data with URL syntax

## Copyright

Copyright (C) 2007-2013, Cycle Computing, LLC.

## License

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License.  You may obtain a copy of the License at

<http://www.apache.org/licenses/LICENSE-2.0.txt>

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

[cycleserver]:http://www.cyclecomputing.com/cycleserver/overview
[condor]:http://www.uwisc.cs.edu/condor
[curl]:http://curl.haxx.se/
