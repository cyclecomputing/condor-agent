@echo off

REM ###### COPYRIGHT NOTICE ########################################################
REM #
REM # Copyright (C) 2007-2011, Cycle Computing, LLC.
REM # 
REM # Licensed under the Apache License, Version 2.0 (the "License"); you
REM # may not use this file except in compliance with the License.  You may
REM # obtain a copy of the License at
REM # 
REM #   http://www.apache.org/licenses/LICENSE-2.0.txt
REM # 
REM # Unless required by applicable law or agreed to in writing, software
REM # distributed under the License is distributed on an "AS IS" BASIS,
REM # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
REM # See the License for the specific language governing permissions and
REM # limitations under the License.
REM #
REM ################################################################################

REM This creates the EXE, which must be done on Windows, so it is checked in.
REM Run build.sh on Unix after running this on Windows to create the packages.

del dist\cycle_agent.exe
setup.py py2exe

echo.
echo.
echo Windows version of CycleAgent built successfully.
echo Now run build.sh (on Unix) to create the archive packages.
