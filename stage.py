#!/usr/bin/python3
"""
Zynthian stage gui
"""

import pygame
import os, stat, sys
import re
import subprocess
import shlex
import pwd
import jack
import logging
from time import sleep
from threading import Thread
from pgu import gui

##############################################################################
# Globals
##############################################################################

FRAMEBUFFER_DEV = "/dev/fb0"
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

#Input Black List
hw_black_list = [
    #"Midi Through"
]

logger=logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

##############################################################################
# Functions
##############################################################################

def main_gui():
    global tab_index_group, tab_box, pedalboards_button, mod_host, configure_mod_ui_button, configure_mod_host_button, configure_jack_button
    pedalboards_button = []

    # Pedalboards container ######################################################
    pedalboards_container=gui.Container(width=1280,height=720)
    y=10
    for p in get_pedalboard_names():
        pedalboards_button.append(gui.Button(p))
        if(not mod_host):
            pedalboards_button[-1].disabled=True
            pedalboards_button[-1].blur()
            pedalboards_button[-1].chsize()
        else:
            pedalboards_button[-1].connect(gui.CLICK, load_pedalboard,p)
        pedalboards_container.add(pedalboards_button[-1],10,y)
        y += 40

    # Configure container ######################################################
    voice_container = gui.Container(width=1280, height=720)
    configure_container=gui.Container(width=1280,height=720)
    configure_mod_ui_button=gui.Button("Start MOD-UI")
    configure_mod_ui_button.connect(gui.CLICK,mod_ui_service,configure_mod_ui_button)
    configure_container.add(configure_mod_ui_button,10,10)
    if(mod_host==False):
        configure_mod_host_button=gui.Button("Start MOD-HOST")
    else:
        configure_mod_host_button=gui.Button("Stop MOD-HOST")
    configure_mod_host_button.connect(gui.CLICK,mod_host_service,configure_mod_host_button)
    configure_container.add(configure_mod_host_button, 200, 10)
    if(check_jack()==False):
        configure_jack_button=gui.Button("Start Audio System")
    else:
        configure_jack_button=gui.Button("Stop Audio System")
    configure_jack_button.connect(gui.CLICK,jack_service,configure_jack_button)
    configure_container.add(configure_jack_button,400,10)
    # Tabs container ######################################################
    # Tab index group
    tab_index_group = gui.Group()
    tab_index_group.connect(gui.CHANGE, tab)
    # Tab index labels
    tab_index_table = gui.Table()
    tab_index_table.tr()
    tab_index_button = gui.Tool(tab_index_group, gui.Label("Voice"), voice_container)
    tab_index_table.td(tab_index_button)
    tab_index_button = gui.Tool(tab_index_group, gui.Label("Pedalboards"), pedalboards_container)
    tab_index_table.td(tab_index_button)
    tab_index_button = gui.Tool(tab_index_group, gui.Label("Configure"), configure_container)
    tab_index_table.td(tab_index_button)
    tab_index_table.tr()
    # Tab box
    spacer = gui.Spacer(1280, 720)
    tab_box = gui.ScrollArea(spacer, height=720)
    tab_index_table.td(tab_box, style={'border': 1}, colspan=40)

    return (tab_index_table)

def get_pedalboard_names():
    pedalboards = []
    for p in os.listdir(PEDALBOARDS_PATH):
        m = re.search("^(.+)\.pedalboard", p)
        if (m):
            pedalboards.append(m.group(1))
    return (pedalboards)


def load_pedalboard(pedalboard):
    if(mod_ui==False and mod_host==True):
        if (pedalboard == "default"):
            pedalboard_ttl_name = "Default.ttl"
        else:
            pedalboard_ttl_name = pedalboard + ".ttl"

        if (stat.S_ISFIFO(os.stat(MODHOST_PIPE).st_mode)):
            if (subprocess.call("echo \"remove -1\" >" + MODHOST_PIPE, shell=True)==0):
                print("Cleanup pedalboard.")
            else:
                print("Cleanup pedalboard failed.")

            if (subprocess.call(PEDALBOARD2MODHOST + " " + PEDALBOARDS_PATH + "/" + pedalboard + ".pedalboard/" + pedalboard_ttl_name + " > " + MODHOST_PIPE, shell=True)==0):
                print("Success.")
            else:
                print("Problem.")
        else:
            print(MODHOST_PIPE + " is not a named pipe.")
    else:
        print("Loading of pedalboards is disabled during a running mod-ui.")

def mod_ui_service(value):
    global mod_ui,mod_host
    if(check_jack()==True):
        if(mod_ui==False):
            start_mod_ui()
            value.value = gui.Label('Stop MOD-UI')
            for pb in pedalboards_button:
                pb.disabled=True
                pb.blur()
                pb.chsize()
            configure_mod_host_button.disabled=True
            configure_mod_host_button.blur()
            configure_mod_host_button.chsize()
            print("MOD-UI started.")
        else:
            start_mod_host()
            for pb in pedalboards_button:
                pb.disabled=False
                pb.chsize()
            configure_mod_host_button.disabled=False
            configure_mod_host_button.chsize()
            value.value = gui.Label('Start MOD-UI')
            print("MOD-UI stopped.")
    else:
        print("Cannot start mod-ui, because jackd is not running")

def mod_host_service(value):
    global mod_host
    if(check_jack()==True):
        if(mod_host==False):
            mod_host=systemctl("mod-host-pipe",True)
            for p in pedalboards_button:
                p.disabled=False
                p.chsize()
            value.value = gui.Label('Stop MOD-HOST')
        else:
            systemctl("mod-host-pipe",False)
            mod_host=False
            for p in pedalboards_button:
                p.disabled=True
                p.blur()
                p.chsize()
            value.value = gui.Label('Start MOD-HOST')
    else:
        print("Cannot start mod-host, because jackd is not running")

def jack_service(value):
   if(check_jack()==False):
       systemctl("jack2",False)
       systemctl("jack2",True)
       start_mod_host()

def start_mod_host():
    global mod_host, mod_ui
    systemctl("mod-ui",False)
    systemctl("mod-host",False)
    mod_ui=False
    mod_host=systemctl("mod-host-pipe",True)
    configure_mod_host_button.disabled=False
    configure_mod_host_button.chsize()
    configure_mod_host_button.value = gui.Label('Stop MOD-HOST')
    configure_mod_ui_button.disabled=False
    configure_mod_ui_button.chsize()
    configure_mod_ui_button.value = gui.Label('Start MOD-HOST')
    if(checK_jack()==False):
        configure_jack_button.value = gui.Label('Start Audio System')
    else:
        configure_jack_button.value = gui.Label('Stop Audio System')
    configure_jack_button.disabled=False
    configure_jack_button.chsize()

def check_jack():
    jackwait=subprocess.call(JACKWAIT,shell=True)
    if(jackwait!=0):
        return(False)
    else:
        return(True)

def systemctl(service,run):
    if(run==True):
        if(subprocess.call(shlex.split(SYSTEMCTL + " start "+service))!=0):
            print("Cannot start %s" % service)
            return(False)
        else:
            return(True)
    else:
        if(subprocess.call(shlex.split(SYSTEMCTL + " stop "+service))!=0):
            print("Cannot stop %s" % service)
            return(False)
        else:
            return(True)

def get_username():
    return pwd.getpwuid( os.getuid() )[ 0 ]

##############################################################################
# Jack autoconnect functions
##############################################################################

def midi_autoconnect():
    logger.info("Autoconnecting Midi ...")

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
            #logger.debug("Element %s => %s " % (i,v) )
            if v in str(hw):
                hw_out.pop(i)

    #logger.debug("Physical Devices: " + str(hw_out))

	# Get Synth Engines
    engines=jclient.get_ports(is_input=True,is_midi=True,is_physical=False)

    #logger.debug("Engine Devices: " + str(engines))

	# Connect Physical devices to Synth Engines
    for hw in hw_out:
        for engine in engines:
            #logger.debug("Connecting HW "+str(hw)+" => "+str(engine))
            try:
                jclient.connect(hw,engine)
            except:
                logger.warning("Failed input device midi connection: %s => %s" % (str(hw),str(engine)))

def autoconnect_thread():
    while not exit_flag:
        try:
            midi_autoconnect()
        except Exception as err:
            logger.error("ERROR Autoconnecting: "+str(err))
        sleep(refresh_time)

def start_autoconnect(rt=2):
    global refresh_time, exit_flag, jclient, thread
    refresh_time=rt
    exit_flag=False
    try:
        jclient=jack.Client("Zynthian_autoconnect")
    except Exception as e:
        logger.error("Failed to connect with Jack Server: %s" % (str(e)))
    thread=Thread(target=autoconnect_thread, args=())
    thread.daemon = True # thread dies with the program
    thread.start()

def autoconnect_stop(self):
    global exit_flag
    exit_flag=True

##############################################################################
# Callback functions
##############################################################################

def tab():
    tab_box.widget = tab_index_group.value

##############################################################################
# Main
##############################################################################

def main():
    global stage,mod_host

    if(get_username()!='root'):
       print("Program must run as root.")
       exit(101)

    if(check_jack()==False):
        print("jackd is not running")
        exit(102)
    else:
        start_mod_host()
        start_autoconnect()

    # Check for X11 or framebuffer
    found = False
    disp_no = os.getenv('DISPLAY')
    if not disp_no:
        os.putenv('SDL_FBDEV', FRAMEBUFFER_DEV)
        drivers = ['directfb', 'fbcon', 'svgalib']
        for driver in drivers:
            if not os.getenv('SDL_VIDEODRIVER'):
                os.putenv('SDL_VIDEODRIVER', driver)
            try:
                pygame.display.init()
            except pygame.error:
                print("Driver: %s failed." % driver)
                continue
            found = True
            break
        if not found:
            raise Exception('No suitable video driver found!')
    else:
        if found:
            size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
            pygame.display.set_mode(size, pygame.FULLSCREEN)

    # Start gui
    theme = gui.Theme("themes/default")
    stage = gui.Desktop(theme=theme)
    stage.connect(gui.QUIT, stage.quit, None)
    stage.run(main_gui())
    print("End.")

if(__name__=="__main__"):
    main()
    exit(0)
