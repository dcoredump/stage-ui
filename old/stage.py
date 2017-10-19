#!/usr/bin/python3
"""
Zynthian stage gui
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.app import App
from kivy.properties import ObjectProperty, StringProperty
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

mod_ui=False
mod_host=False

refresh_time=2
jclient=None
thread=None
exit_flag=False
actual_pedalboard=None

# Input Black List
hw_black_list = [
    "Midi Through"
]

##############################################################################
# Kivy class
##############################################################################

class StageScreens(BoxLayout):
    mod_ui_button=ObjectProperty()

    def get_pedalboard_names():
        pedalboards = []
        for p in os.listdir(PEDALBOARDS_PATH):
            m = re.search("^(.+)\.pedalboard", p)
            if (m):
                pedalboards.append(m.group(1))
        return (pedalboards)


    def load_pedalboard(pedalboard):
        Logger.info("load_pedalboard() %s" % load_pedalboard)
        if(mod_ui==False and mod_host==True):
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
                    actual_pedalboard=voice_container.add(gui.Label(pedalboard),10,10)
                else:
                    Logger.warning("Pedalboard "+pedalboard+" load problem.")
            else:
                Logger.warning(MODHOST_PIPE + " is not a named pipe.")
        else:
            Logger.warning("Loading of pedalboards is disabled during a running mod-ui.")

    def mod_ui_service(value):
        Logger.info("mod_ui_service() %s" % value)
        global mod_ui,mod_host
        if(check_jack()==True):
            if(mod_ui==False):
                start_mod_ui()
                Logger.info("MOD-UI started.")
            else:
                start_mod_host()
                Logger.info("MOD-UI stopped.")
        else:
            Logger.ciritical("Cannot start mod-ui, because jackd is not running")

    def mod_host_service(value):
        global mod_host
        Logger.info("mod_host_service() %s" % value)
        if(check_jack()==True):
            if(mod_host==False):
                mod_host=systemctl("mod-host-pipe",True)
            else:
                systemctl("mod-host-pipe",False)
                mod_host=False
        else:
            Logger.ciritcal("Cannot start mod-host, because jackd is not running")

    def jack_service(value):
        global mod_ui,mod_host
        Logger.info("jack_service() %s" % value)
        if(check_jack()==True):
            if(mod_ui):
                systemctl("mod-ui",False)
                mod_ui=False
            systemctl("mod-host",False)
            if(mod_host):
                systemctl("mod-host-pipe",False)
                mod_host=False
            systemctl("jack2",False)
            sleep(2)
            systemctl("jack2",True)
            mod_host=systemctl("mod-host-pipe",True)

    def halt_service():
        Logger.info("halt_service()")
        subprocess.call(shlex.split("/sbin/halt"))

    def start_mod_host():
        global mod_host, mod_ui
        Logger.info("start_mod_host()")
        systemctl("mod-ui",False)
        systemctl("mod-host",False)
        mod_ui=False
        mod_host=systemctl("mod-host-pipe",True)
        start_autoconnect()
        return(mod_host)

    def start_mod_ui():
        global mod_host, mod_ui
        Logger.info("start_mod_ui()")
        stop_autoconnect()
        systemctl("mod-host-pipe",False)
        mod_host=False
        systemctl("mod-host",True)
        mod_ui=systemctl("mod-ui",True)
        return(mod_ui)

    def check_jack(self):
        Logger.info("check_jack()")
        jackwait=subprocess.call(JACKWAIT+">/dev/null 2>&1",shell=True)
        if(jackwait!=0):
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

    def get_username():
        return pwd.getpwuid(os.getuid())[0]

class StageRoot(BoxLayout):
    pass

class StageApp(App):
    pass

##############################################################################
# Jack autoconnect functions
##############################################################################

def midi_autoconnect():
    # Get Physical MIDI-devices ...
    hw_out=jclient.get_ports(is_output=True,is_physical=True,is_midi=True)
    if len(hw_out)==0:
        hw_out=[]
    # Add ttymidi device ...
    tty_out=jclient.get_ports("ttymidi",is_output=True,is_physical=False,is_midi=True)
    try:
        hw_out.append(tty_out[0])
    except:
        pass

    # Remove HW Black-listed
    for i,hw in enumerate(hw_out):
        for v in hw_black_list:
            #Logger.debug("Element %s => %s " % (i,v) )
            if v in str(hw):
                hw_out.pop(i)

    Logger.debug("Physical Devices: " + str(hw_out))

    # Get Synth Engines
    engines=jclient.get_ports(is_input=True,is_midi=True,is_physical=False)

    Logger.debug("Engine Devices: " + str(engines))

    # Connect Physical devices to Synth Engines
    for hw in hw_out:
        for engine in engines:
            #Logger.debug("Connecting HW "+str(hw)+" => "+str(engine))
            try:
                jclient.connect(hw,engine)
            except:
                Logger.warning("Failed input device midi connection: %s => %s" % (str(hw),str(engine)))

def autoconnect_thread():
    while not exit_flag:
        try:
            midi_autoconnect()
        except Exception as err:
            Logger.error("ERROR Autoconnecting: "+str(err))
        sleep(refresh_time)
    Logger.info("midi_autoconnect() stopped.")

def start_autoconnect(rt=2):
    global refresh_time, exit_flag, jclient, thread
    refresh_time=rt
    exit_flag=False
    try:
        jclient=jack.Client("Zynthian_autoconnect")
    except Exception as e:
        Logger.error("Failed to connect with Jack Server: %s" % (str(e)))
    thread=Thread(target=autoconnect_thread, args=())
    thread.daemon = True # thread dies with the program
    thread.start()
    Logger.info("midi_autoconnect() started.")

def stop_autoconnect():
    global exit_flag
    exit_flag=True
    Logger.info("autoconnect stop flagged.")

##############################################################################
# Callback functions
##############################################################################

##############################################################################
# Main
##############################################################################

def main():
    global mod_host

    #if(get_username()!='root'):
    #   Logger.critical("Program must run as root.")
    #   exit(100)
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
