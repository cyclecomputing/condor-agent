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
import win32api
import win32con
import win32gui
import threading

################################################################################
# GLOBALS
################################################################################



################################################################################
# CLASSES
################################################################################

class MainWindow:
    '''Creates a simple window so we can watch for WM_CLOSE and
    WM_DESTROY signals.'''
    
    def __init__(self, callback):
        self.hinst    = win32api.GetModuleHandle(None)
        self.callback = callback
    
     
    def CreateWindow(self):
        className   = "CondorAgent"
        message_map = {
            win32con.WM_DESTROY: self.OnDestroy,
            win32con.WM_CLOSE : self.OnDestroy,
            }
        wc               = win32gui.WNDCLASS()
        wc.lpfnWndProc   = message_map
        wc.lpszClassName = className
        classAtom        = win32gui.RegisterClass(wc)
        self.BuildWindow(className)
    
    
    def BuildWindow(self, className):
        style = win32con.WS_OVERLAPPEDWINDOW
        self.hwnd = win32gui.CreateWindow(className,
                                          "ThisIsJustATest",
                                          style, win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT,
                                          100, 100, 0, 0,
                                          self.hinst, None)
    
                                          
    def OnDestroy(self, hwnd, message, wparam, lparam):
        win32gui.PostQuitMessage(0)
        return True
    
    
    def run(self):
        self.CreateWindow()
        win32gui.PumpMessages()
        self.callback()
    


################################################################################
# METHODS
################################################################################

def setupShutdownHook(callback):
    '''Create a window on a background thread that executes a callback on
    close/destroy.'''
    w = MainWindow(callback)
    t = threading.Thread(target = w.run, args = ())
    t.setDaemon (1)
    t.start()
