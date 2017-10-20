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

##############################################################################
# Kivy class
##############################################################################

class StageApp(App):
    pass

class StageRoot(BoxLayout):
    pass

class StageScreens(BoxLayout):
    modui_button=ObjectProperty()
    modhost_button=ObjectProperty()
    jack_button=ObjectProperty()

    def set_modui_button_state(self):
        if(systemctlstatus('mod-ui')==True):
            return("down")
        else:
            return("normal")

    def change_modui_button_state(self):
        if(systemctlstatus('jack2')==False):
            self.jack_button.state="down"
        if(systemctlstatus('mod-ui')==True):
            mod_service("mod-ui",False)
            if(systemctlstatus('mod-host')==True):
                mod_service("mod-host",False)
        else:
            self.modhost_button.state="normal"
            mod_service("mod-host",True)
            mod_service("mod-ui",True)

    def set_modhost_button_state(self):
        if(systemctlstatus('mod-host-pipe')==True):
            return("down")
        else:
            return("normal")

    def change_modhost_button_state(self):
        if(systemctlstatus('jack2')==False):
            self.jack_button.state="down"
        if(systemctlstatus('mod-host-pipe')==True):
            mod_service("mod-host-pipe",False)
        else:
            if(systemctlstatus('mod-ui')==True):
                self.modui_button.state="normal"
            mod_service("mod-host-pipe",True)

    def set_jack_button_state(self):
        if(check_jack()==True):
            return("down")
        else:
            return("normal")

    def change_jack_button_state(self):
        if(check_jack()==True):
            self.modui_button.state="normal"
            self.modhost_button.state="normal"
            systemctl("jack2",False)
        else:
            systemctl("jack2",True)

##############################################################################
# Functions
##############################################################################

def mod_service(mod,state):
    if(systemctlstatus(mod)!=state):
        if(state==True):
            systemctl(mod,True)
        else:
            systemctl(mod,False)
        Logger.info("State change for %s to %s" % (mod,state))
    else:
        Logger.info("No state change for %s" % mod)

def check_jack():
    Logger.info("check_jack()")
    jackwait=subprocess.call(JACKWAIT+">/dev/null 2>&1",shell=True)
    if(jackwait!=0):
        return(False)
    else:
        return(True)

def systemctlstatus(service):
    if(subprocess.call(shlex.split(SYSTEMCTL + " status "+service))!=0):
        return(False)
    else:
        return(True)

def systemctl(service,run):
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

def quit():
    systemctl("mod-ui",False)
    systemctl("mod-host",False)
    systemctl("mod-host-pipe",False)
    systemctl("jack2",False)
    exit(0)

def halt():
    subprocess.call("/sbin/halt",shell=True)
    exit(0)

def restart():
    subprocess.call("/sbin/reboot",shell=True)
    exit(0)

def get_username():
    return pwd.getpwuid(os.getuid())[0]

##############################################################################
# Main
##############################################################################

def main():
    if(get_username()!='root'):
       Logger.critical("Program must run as root.")
       exit(100)

    if(check_jack()==False):
        if(systemctl("jack2",True)==False):
            Logger.critical("jackd is not running")
            exit(101)
        Logger.info("jackd was not running, started.")
    mod_service("mod-host-pipe",True)

    Logger.info("Start StageApp.")
    StageApp().run()
    Logger.info("StageApp ends.")

if(__name__=="__main__"):
    main()
    exit(0)
