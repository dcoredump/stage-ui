#!/usr/bin/python3
"""
Zynthian stage gui
"""
from kivy.uix.boxlayout import BoxLayout
from kivy.app import App
from kivy.properties import ObjectProperty
from kivy.properties import NumericProperty
from kivy.uix.listview import ListItemButton
from kivy.adapters.models import SelectableDataItem
from kivy.logger import Logger
from kivy.clock import Clock
import os, stat, sys, re
import subprocess
import shlex
import pwd
import jack
import pexpect
import instruments
from time import sleep
from pprint import pprint
from pathlib import Path

import instruments

##############################################################################
# Globals
##############################################################################

PEDALBOARDS_PATH = os.environ['HOME'] + "/.pedalboards"
PEDALBOARD2MODHOST = "./pedalboard2modhost"
JACKWAIT="/usr/local/bin/jack_wait -t1 -w"
JACKALIAS="/usr/local/bin/jack_alias"
SYSTEMCTL="/bin/systemctl"
MODHOST="/usr/local/bin/mod-host"
MODHOST_TIMEOUT=30
LAST_PEDALBOARD_FILE=os.environ['HOME'] + "/.last_pedalboard"

##############################################################################
# Kivy class
##############################################################################

class StageApp(App):
    client=None
    xrun_counter=0
    actual_pedalboard="default"
    p_modhost=None

    def on_start(self):
        startup_jack()
    
        self.client=jack.Client("stage")
        self.client.set_xrun_callback(xrun)
        midi_alias()

        if(mod_host(True)==False):
            Logger.critical("Cannot start mod-host.")
            exit(101)
    
        systemctl("mod-ui",False)

        Logger.info("mod-host CPU: "+str(send_mod_host("cpu_load")))

        self.actual_pedalboard=read_last_pedalboard()
        load_pedalboard(self.actual_pedalboard,init=True)

    def on_stop(self):
        quit_prog()

class StageRoot(BoxLayout):
    pass

class ListPedalboardButton(ListItemButton):
    pass

class DataItem(SelectableDataItem):
    def __init__(self, text="", is_selected=False):
        self.text = text
        self.is_selected = is_selected

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
            midi_alias()
            mod_service("mod-ui",False)
            mod_service("mod-host",False)
            mod_host(True)
            load_pedalboard(App.get_running_app().actual_pedalboard,init=True)
            #self.Pedalboard.disabled=True
        else:
            mod_host(False)
            midi_alias(unalias=True)
            mod_service("mod-host",True)
            mod_service("mod-ui",True)
            #self.Pedalboard.disabled=False

    def restart_jack(self):
        mod_service("mod-ui",False)
        mod_service("mod-host",False)
        self.modui_button.state='normal'
        systemctl("jack2",False)
        startup_jack()
        App.get_running_app().actual_pedalboard=read_last_pedalboard()
        load_pedalboard(App.get_running_app().actual_pedalboard,init=True)

##############################################################################
# Functions
##############################################################################

def list_items_args_converter(row_index, obj):
    return({'text': obj.text, 'size_hint_y': None, 'height': 50})

def get_pedalboard_names():
    actual_pedalboard=read_last_pedalboard()
    pedalboards = []
    for p in os.listdir(PEDALBOARDS_PATH):
        m = re.search("^(.+)\.pedalboard", p)
        if (m):
            if(m.group(1)==actual_pedalboard):
                Logger.info("get_pedalboard_names: found actual pedalboard [%s]" % actual_pedalboard)
                pedalboards.append(DataItem(text=m.group(1),is_selected=True))
            else:
                pedalboards.append(DataItem(text=m.group(1)))
    return (pedalboards)

def load_pedalboard(pedalboard, init=False):
    Logger.info("load_pedalboard:%s (old: %s)" % (pedalboard,App.get_running_app().actual_pedalboard))

    if(App.get_running_app().actual_pedalboard==pedalboard and init==False):
        Logger.info("load_pedalboard:no need to load the same pedalboard")
        return
    if(systemctlstatus("mod-ui")):
        Logger.info("load_pedalboard:mod-ui is running! Loading nothing")
        return

    mod_service("mod-host",False)
   
    if(systemctlstatus('jack2')):
        if (pedalboard == "default"):
            pedalboard_ttl_name = "Default.ttl"
        else:
            pedalboard_ttl_name = pedalboard + ".ttl"
        if(App.get_running_app().p_modhost==None):
            Logger.critical("No modhost is running...")
            exit(503)
        if (send_mod_host("remove -1")):
            Logger.info("load_pedalboard:Cleanup pedalboard.")
        else:
            Logger.warning("Cleanup pedalboard failed.")

        p=subprocess.check_output(shlex.split(PEDALBOARD2MODHOST + " " + PEDALBOARDS_PATH + "/" + pedalboard + ".pedalboard/" + pedalboard_ttl_name))
        if(p!=""):
            re_connect=re.compile('^\s*(connect)\s+(.+)\s+(.+)_\d\s*$')
            for line in p.splitlines():
                line=line.decode('ascii')
                r=re_connect.match(line)
                if(r):
                    if(r.group(1)=="connect" and r.group(3)=="system:midi_capture"):
                        line="connect "+r.group(2)+" ttymidi:MIDI_in"
                resp=send_mod_host(line)
                if(resp[0]!=None):
                    Logger.info("load_pedalboard:"+line+":"+str(resp))
            resp=send_mod_host("connect mod-host:midi_in ttymidi:MIDI_in")
            write_last_pedalboard(pedalboard)
            actual_pedalboard=pedalboard
        else:
            Logger.warning("Pedalboard "+pedalboard+" load problem.")
    else:
        Logger.warning("Loading of pedalboards is disabled during a running mod-ui.")

def mod_service(mod,state):
    if(systemctlstatus(mod)!=state):
        if(state==True):
            systemctl(mod,True)
        else:
            systemctl(mod,False)
        Logger.info("mod_service:State change for %s to %s" % (mod,state))
    else:
        Logger.info("mod_service:No state change for %s" % mod)

def check_jack():
    Logger.info("check_jack:")
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
    Logger.info("systemctl: %s %s" % (service,run))
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

def quit_prog():
    mod_service("mod-ui",False)
    mod_service("mod-host",False)
    mod_host(False)
    midi_alias(unalias=True)
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
    Logger.warn("jackd: XRUN[%d] delay=%d" % (App.get_running_app().xrun_counter,delay))
    App.get_running_app().xrun_counter=xrun_counter+1
 
def jack_status(status, reason):
    Logger.warn("jackd: '%s'" % reason)
    App.get_running_app().jack_status_message=(status, reason)

def startup_jack():
    Logger.info("startup_jack:")

    mod_service("mod-ui",False)
    mod_service("mod-host",False)

    App.get_running_app().xrun_counter=0

    while True:
        if(check_jack()==False):
            if(systemctl("jack2",True)==False):
                Logger.critical("jackd is not running")
                exit(101)
                if(mod_host(True)==False):
                    Logger.critical("mod-host is not running")
                    exit(101)
                Logger.info("startup_jack:mod-host was not running, started.")
            else:
                break
        else:
            break

def midi_alias(unalias=False):
    if(App.get_running_app().client==None):
        Logger.warning("No internal jack-client available, creating new one...")
        App.get_running_app().client=jack.Client("stage")
    for i in range(1,3):
        if(i%2==0):
            io=True
            io_name="in"
        else:
            io=False
            io_name="out"
        ttymidi=App.get_running_app().client.get_ports("ttymidi", is_output=io, is_midi=True)
        if(len(ttymidi)==0):
            if(io==True):
                hw=App.get_running_app().client.get_ports("system",is_midi=True, is_audio=False, is_output=True, is_physical=True)
            else:
                hw=App.get_running_app().client.get_ports("system",is_midi=True, is_audio=False, is_input=True, is_physical=True)
            if(len(hw)>0):
                re_system_capture=re.compile('^(system:midi_capture_)\d+')
                for m in hw:
                    r=re_system_capture.match(m.name)
                    if(r):
                        if(unalias==True):
                            Logger.info("midi_alias:jack unalias %s => ttymidi:MIDI_%s" % (r.group(0),io_name))
                            subprocess.call(JACKALIAS+" -u "+str(r.group(0))+" ttymidi:MIDI_"+io_name,shell=True)
                        else:
                            Logger.info("midi_alias:jack alias %s => ttymidi:MIDI_%s" % (r.group(0),io_name))
                            subprocess.call(JACKALIAS+" "+str(r.group(0))+" ttymidi:MIDI_"+io_name,shell=True)

def read_last_pedalboard():
    last_pedalboard_file=Path(LAST_PEDALBOARD_FILE)
    if(last_pedalboard_file.is_file()):
        f=open(LAST_PEDALBOARD_FILE,"r")
        if(f):
            last_pedalboard=f.readline()[:-1]
            Logger.info("read_last_pedalboard:last pedalboard: [%s]" % last_pedalboard)
            if(last_pedalboard==""):
                last_pedalboard="default"
                write_last_pedalboard(last_pedalboard)
            f.close()
        else:
            Logger.warning("Cannot read '%s'" % LAST_PEDALBOARD_FILE)
            last_pedalboard="default"
    else:
        write_last_pedalboard("default")
        last_pedalboard="default"
    return(last_pedalboard)

def write_last_pedalboard(pedalboard):
    f=open(LAST_PEDALBOARD_FILE,"w")
    if(f):
        f.write(pedalboard+"\n")
        Logger.info("write_last_pedalboard: [%s]" % pedalboard)
        App.get_running_app().actual_pedalboard=pedalboard
        f.close()
    else:
        Logger.warning("Cannot create '%s'" % LAST_PEDALBOARD_FILE)

def mod_host(state=True):
    if(state==True):
        if(App.get_running_app().p_modhost!=None):
            return(True)
        App.get_running_app().p_modhost=pexpect.spawn(MODHOST+" -i")
        Logger.info("mod_host: Loading mod-host")
        if(not App.get_running_app().p_modhost):
            App.get_running_app().p_modhost=None
            return(False)
        else:
            try:
                App.get_running_app().p_modhost.expect('mod-host>',timeout=MODHOST_TIMEOUT)
            except Exception as e:
                Logger.critical("start_mod_host: Cannot start "+MODHOST+" :"+str(e))
                exit(502)
    else:
        App.get_running_app().p_modhost.terminate(force=True)
        App.get_running_app().p_modhost=None
    Logger.info("mod_host: mod-host state %s" % state)
    return(True)

def send_mod_host(cmd):
    r=[None,None]
    if(App.get_running_app().p_modhost==None):
        Logger.critical("No background mod-host is running...")
    else:
        App.get_running_app().p_modhost.sendline(cmd)
        Logger.info("send_mod_host:["+cmd+"]")
        try:
            App.get_running_app().p_modhost.expect('resp ([\-0-9]+)\s*(.*)\0',timeout=MODHOST_TIMEOUT)
            resp=App.get_running_app().p_modhost.match.groups()
            for i in range(0,len(resp)):
                r[i]=resp[i].decode('ascii')
        except Exception as e:
            Logger.warning("send_mod_host:"+cmd+":"+str(e))
    return(r)

##############################################################################
# Main
##############################################################################

def main():
    if(get_username()!='root'):
       Logger.critical("Program must run as root.")
       exit(100)

    Logger.info("main:Start StageApp.")
    StageApp().run()
    Logger.info("main:StageApp ends.")

if(__name__=="__main__"):
    main()
