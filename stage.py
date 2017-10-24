#!/usr/bin/python3
"""
Zynthian stage gui
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.app import App
from kivy.properties import ObjectProperty
from kivy.properties import StringProperty
from kivy.uix.listview import ListItemButton
from kivy.logger import Logger
from kivy.clock import Clock
#from pluginsmanager.model.connection import Connection
#from pluginsmanager.model.midi_connection import MidiConnection
#from pluginsmanager.observer.autosaver.autosaver import Autosaver
from pluginsmanager.observer.mod_host.mod_host import ModHost
from pluginsmanager.model.pedalboard import Pedalboard
from pluginsmanager.model.lv2.lv2_effect_builder import Lv2EffectBuilder
from pluginsmanager.model.system.system_effect import SystemEffect
from pluginsmanager.model.system.system_effect_builder import SystemEffectBuilder
from pluginsmanager.jack.jack_client import JackClient
#from pluginsmanager.banks_manager import BanksManager
#from pluginsmanager.model.bank import Bank
import os, stat, sys, re
import subprocess
import shlex
import pwd
from time import sleep

##############################################################################
# Globals
##############################################################################

PEDALBOARDS_PATH = os.environ['HOME'] + "/.pedalboards"
PEDALBOARD2MODHOST = "./pedalboard2modhost"
JACKWAIT="/usr/local/bin/jack_wait -t1 -w"
SYSTEMCTL="/bin/systemctl"
MODHOST_PIPE="/tmp/mod-host"

# globals for PedalPi (placeholder)
client = None
sys_effect = None
autosaver = None
manager = None
modhost = None
xrun_counter=0
jack_status_message=(0,"")

##############################################################################
# Kivy class
##############################################################################

class StageApp(App):
    pass

class StageRoot(BoxLayout):
    pass

class SelectPedalboardButton(ListItemButton):
    pass

class StageScreens(BoxLayout):
    modui_button=ObjectProperty()
    jack_button=ObjectProperty()
    preset_list=ObjectProperty()
    mod_host_status=ObjectProperty()

    def set_modui_button_state(self):
        if(systemctlstatus('mod-ui')==True and systemctlstatus('jack2')==True):
            return("down")
        else:
            return("normal")

    def change_modui_button_state(self):
        if(systemctlstatus('mod-ui')==True):
            mod_service("mod-ui",False)
        else:
            mod_service("mod-ui",True)

    def restart_jack(self):
        systemctl("jack2",False)
        startup_jack()

##############################################################################
# Functions
##############################################################################

def get_pedalboard_names():
    pedalboards = []
    for p in os.listdir(PEDALBOARDS_PATH):
        m = re.search("^(.+)\.pedalboard", p)
        if (m):
            pedalboards.append(m.group(1))
    return (pedalboards)

def load_pedalboard(pedalboard):
    Logger.info("load_pedalboard() %s" % load_pedalboard)

    mod_service("mod-host-pipe",False)
    mod_service("mod-host-pipe",True)
   
    if(systemctlstatus('mod-host-pipe') and systemctlstatus('jack2')):
        if (pedalboard == "default"):
            pedalboard_ttl_name = "Default.ttl"
        else:
            pedalboard_ttl_name = pedalboard + ".ttl"
        if (stat.S_ISFIFO(os.stat(MODHOST_PIPE).st_mode)):
            if (subprocess.call("echo \"remove -1\" >" + MODHOST_PIPE, shell=True)==0):
                Logger.info("Cleanup pedalboard.")
            else:
                Logger.warning("Cleanup pedalboard failed.")

            if (subprocess.call(PEDALBOARD2MODHOST + " " + PEDALBOARDS_PATH + "/" + pedalboard + ".pedalboard/" + pedalboard_ttl_name + " > " + MODHOST_PIPE, shell=True)==0):
                Logger.info("Pedalboard "+pedalboard+" load success.")
                sleep(3)
            else:
                Logger.warning("Pedalboard "+pedalboard+" load problem.")
        else:
            Logger.warning(MODHOST_PIPE + " is not a named pipe.")
    else:
        Logger.warning("Loading of pedalboards is disabled during a running mod-ui.")

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
    mod_service("mod-ui",False)
    exit(0)

def halt():
    subprocess.call("/sbin/halt",shell=True)
    exit(0)

def restart():
    subprocess.call("/sbin/reboot",shell=True)
    exit(0)

def get_username():
    return pwd.getpwuid(os.getuid())[0]

def xrun(delay):
    global xrun_counter
    Logger.warn("jackd: XRUN[%d] delay=%d" % (xrun_counter,delay))
    xrun_counter=xrun_counter+1
 
def jack_status(status, reason):
    global jack_status_message
    Logger.warn("jackd: '%s'" % reason)
    jack_status_message=(status, reason)

def startup_jack():
    global client
    global xrun_counter

    Logger.info("startup_jack()")

    xrun_counter=0

    if(client):
        client.close()

    while True:
        if(check_jack()==False):
            if(systemctl("jack2",True)==False):
                Logger.critical("jackd is not running")
                exit(101)
                if(systemctl("mod-host",True)==False):
                    Logger.critical("mod-host is not running")
                    exit(101)
                Logger.info("mod-host was not running, started.")
            else:
                break
        else:
            break

    client = JackClient()
    client.xrun_callback=lambda delay: xrun(delay)
    client.shutdown_callback = lambda status, reason: jack_status(status, reason)


##############################################################################
# Main
##############################################################################

def main():
    global client
    if(get_username()!='root'):
       Logger.critical("Program must run as root.")
       exit(100)

    startup_jack()

    Logger.info("Start StageApp.")
    StageApp().run()
    Logger.info("StageApp ends.")

if(__name__=="__main__"):
    main()
    exit(0)
