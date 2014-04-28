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
# python test_post_submit.py
#
# Run unit tests against the local submission features of the Agent.


################################################################################
# IMPORTS
################################################################################
import unittest
import post_submit
import zipfile
import shutil
import tempfile
import os
import util


################################################################################
# GLOBALS
################################################################################


################################################################################
# CLASSES
################################################################################

class MockRequestHandler:
    def __init__(self):
        self.headers = {}
        self.responseCode = None
        # Set to file pointers...
        self.rfile = None
        self.wfile = None
        #self.wfile.write(str(clusterId))
    
    def send_response(self, responseCode):
        self.responseCode = responseCode
    
    def send_header(self, name, contentType):
        self.headers[name] = contentType
    
    def end_headers(self):
        pass
    


class Test(unittest.TestCase):
    #def __init__(self):
        #self.scratchDir = tempfile.mkdtemp(dir=os.getcwd())
        #self.requestHandler = MockRequestHandler()
    def setUp(self):
        os.environ["CONDOR_BIN_PATH"] = "/opt/condor/bin"
        os.environ["CONDOR_CONFIG"] = "/opt/condor/etc/condor_config"
        if os.environ.has_key("CONDOR_BIN_PATH"):
            os.environ["PATH"] = os.environ["PATH"] + os.pathsep + os.environ["CONDOR_BIN_PATH"]
        # Create a temporary directory with files and what not
        # Then zip it up
        #tempfile()       
        pass
    
    def tearDown(self):
        # Delete the temporary directory and files we created.
        pass
    
    def testDoRunCommand2(self):
        (retval, out, err) = util.runCommand2("ls -al")
        self.assertEqual(0, retval)
        self.assertTrue(out != '')
        self.assertEqual('', err)
    
    def testDoCondorSubmit(self):
        # TBD This path is wrong, needs to change
        #post_submit.doCondorSubmit("/cycle/svn_source/trunk/cycle_server/cycle_agent/cycle_agent/src/test_sub/test_condor.sub")
        pass
    
    def testTmpFileAndDirCreation(self):
        pass
    
    def testLocate(self):
        pass
    
    def testNoSubmitFiles(self):
        pass
    
    def testManySubmitFiles(self):
        pass
    
    def testValidSubmitFile(self):
        pass
    



if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
