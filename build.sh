#!/bin/sh

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

VERSION=`sed -n -e 's/VERSION = "\(.*\)"/\1/p' condor_agent.py | tr -d '\r'`

echo "Building version $VERSION of Condor Agent..."

BUILD_DIR=build/condor_agent
DIST_DIR=dist/packages

if [ -e $DIST_DIR ]; then
    rm $DIST_DIR/*
else 
    mkdir -p $DIST_DIR
fi

# 0 for Linux, 1 for Mac
IS_MAC=0
if [ $(uname -s) == Darwin ]; then
    # Mac
    IS_MAC=1
fi
export IS_MAC

if [ $IS_MAC -eq 1 ]; then
    STAT="stat -f %m "
else
    STAT="stat -c %Y "
fi



prep_build() {
    rm -rf build
    mkdir -p  $BUILD_DIR
    cp README $BUILD_DIR
}

## Native python build
prep_build

cp condor_agent $BUILD_DIR
cp condor_agent.py $BUILD_DIR
mkdir $BUILD_DIR/CondorAgent
cp CondorAgent/*.py $BUILD_DIR/CondorAgent

FILE=condor_agent_$VERSION.python.tar.gz

cd build
tar czf $FILE condor_agent
cd ..

mv build/$FILE $DIST_DIR

#### Windows

prep_build


# get the latest modification time for any py file
LAST_MOD=`find . -name '*.py' -exec $STAT {} \; | sort -n -r | head -1`
# get the modification time for the EXE
EXE_MOD=`$STAT dist/condor_agent.exe`

if [ "$EXE_MOD" -lt "$LAST_MOD" ] ; then
    echo "ERROR: condor_agent.exe appears to be out of date. Please run build.bat on Windows to create a new EXE."
    exit 1
fi

cp dist/*.exe $BUILD_DIR

FILE=condor_agent_$VERSION.win32.zip


# Verify that we have the 7zip tool
export ZIP=`which 7za`
if [ -z "$ZIP" ]; then
    echo "ERROR: Unable to find the 7zip compression tool." >&2
    echo "Try \"port install p7zip\" or \"yum install p7zip\" depending on your OS." >&2
    exit 1
fi

cd build
$ZIP a -bd -tzip $FILE condor_agent
cd ..

mv build/$FILE $DIST_DIR
