#!/usr/bin/python3
"""
Zynthian stage gui
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.app import App
from kivy.properties import ObjectProperty
from kivy.logger import Logger
import os, stat, sys
import re
import subprocess
import shlex
import pwd
from time import sleep
from threading import Thread

##############################################################################
# Globals
##############################################################################

PEDALBOARDS_PATH = os.environ['HOME'] + "/.pedalboards"
PEDALBOARD2MODHOST = "./pedalboard2modhost"
MODHOST = "/usr/local/bin/mod-host"
MODHOST_PIPE="/tmp/mod-host"
TAIL ="/usr/bin/tail"
PARTRT="/usr/local/bin/partrt"
PARTRT_OPTIONS="-f99"
JACKWAIT="/usr/local/bin/jack_wait -t1 -w"
SYSTEMCTL="/bin/systemctl"

STATE['mod_ui']=False
STATE['mod_host']=False

##############################################################################
# Kivy class
##############################################################################

class StageApp(App):
    pass

class StageRoot(BoxLayout):
    pass

class StageScreens(BoxLayout):
    mod_ui_button=ObjectProperty()

    def check_jack(self):
        Logger.info("check_jack()")
        jackwait=subprocess.call(JACKWAIT+">/dev/null 2>&1",shell=True)
        if(jackwait!=0):
            return(False)
        else:
            return(True)

    def systemctl(self,service,run):
        Logger.info("systemctl() %s %s" % (service,run))
        if(run==True):
            if(subprocess.call(shlex.split(SYSTEMCTL + " start "+service))!=0):
                Logger.error("Cannot start %s" % service)
                return(False)
            else:
                return(True)
        else:
            if(subprocess.call(shlex.split(SYSTEMCTL + " stop "+service))!=0):
                Logger.error("Cannot stop %s" % service)
                return(False)
            else:
                return(True)

##############################################################################
# Functions
##############################################################################

def get_username():
    return pwd.getpwuid(os.getuid())[0]

##############################################################################
# Main
##############################################################################

def main():
    if(get_username()!='root'):
       Logger.critical("Program must run as root.")
       exit(100)
#
#    if(check_jack()==False):
#        Logger.critical("jackd is not running")
#        exit(101)
#    else:
#        start_mod_host()
#
    Logger.info("Start StageApp.")
    StageApp().run()
    Logger.info("StageApp ends.")

if(__name__=="__main__"):
    main()
    exit(0)
