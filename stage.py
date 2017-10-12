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

SCREEN_X=1280
SCREEN_Y=800

mod_ui=False
mod_host=False

refresh_time=2
jclient=None
thread=None
exit_flag=False
actual_pedalboard=None

#Input Black List
hw_black_list = [
    #"Midi Through"
]

pedalboards_button = []

logger=logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

##############################################################################
# Functions
##############################################################################

def main_gui():
    global tab_index_group, tab_box, mod_host, configure_mod_ui_button, configure_mod_host_button, configure_jack_button, voice_container

    # Voice container ###########################################################
    voice_container = gui.Container(width=SCREEN_X, height=SCREEN_Y)

    # Pedalboards container #####################################################
    pedalboards_container=gui.Container(width=SCREEN_X,height=SCREEN_Y)
    y=10
    for p in get_pedalboard_names():
        pedalboards_button.append(gui.Button(p))
        pedalboards_button[-1].connect(gui.CLICK, load_pedalboard,p)
        pedalboards_container.add(pedalboards_button[-1],10,y)
        y += 40

    if(mod_host==False or mod_ui==True):
        blur_pedalboard_buttons(True)

    # Configure container ######################################################
    configure_container = gui.Container(width=SCREEN_X, height=SCREEN_Y)
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
        configure_jack_button=gui.Button("Restart Audio System")
    configure_jack_button.connect(gui.CLICK,jack_service,configure_jack_button)
    configure_container.add(configure_jack_button,500,10)
    configure_halt_button=gui.Button("System halt")
    configure_halt_button.connect(gui.CLICK,halt_service)
    configure_container.add(configure_halt_button,800,10)
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
    spacer = gui.Spacer(SCREEN_X, SCREEN_Y)
    tab_box = gui.ScrollArea(spacer, height=SCREEN_Y)
    tab_index_table.td(tab_box, style={'border': 1}, colspan=40)

    return (tab_index_table)

def blur_pedalboard_buttons(blur):
    for p in pedalboards_button:
        if(blur==True):
            p.disabled=True
            p.blur()
            p.chsize()
        else:
            p.disabled=False
            p.chsize()

def get_pedalboard_names():
    pedalboards = []
    for p in os.listdir(PEDALBOARDS_PATH):
        m = re.search("^(.+)\.pedalboard", p)
        if (m):
            pedalboards.append(m.group(1))
    return (pedalboards)


def load_pedalboard(pedalboard):
    global actual_pedalboard,voice_container
    if(mod_ui==False and mod_host==True):
        if (pedalboard == "default"):
            pedalboard_ttl_name = "Default.ttl"
        else:
            pedalboard_ttl_name = pedalboard + ".ttl"

        if(actual_pedalboard):
            voice_container.remove(actual_pedalboard)

        if (stat.S_ISFIFO(os.stat(MODHOST_PIPE).st_mode)):
            if (subprocess.call("echo \"remove -1\" >" + MODHOST_PIPE, shell=True)==0):
                logging.info("Cleanup pedalboard.")
            else:
                logging.warning("Cleanup pedalboard failed.")

            if (subprocess.call(PEDALBOARD2MODHOST + " " + PEDALBOARDS_PATH + "/" + pedalboard + ".pedalboard/" + pedalboard_ttl_name + " > " + MODHOST_PIPE, shell=True)==0):
                logging.info("Pedalboard "+pedalboard+" load success.")
                actual_pedalboard=voice_container.add(gui.Label(pedalboard),10,10)
            else:
                logging.warning("Pedalboard "+pedalboard+" load problem.")
        else:
            logging.warning(MODHOST_PIPE + " is not a named pipe.")
    else:
        logging.warning("Loading of pedalboards is disabled during a running mod-ui.")

def mod_ui_service(value):
    global mod_ui,mod_host
    if(check_jack()==True):
        if(mod_ui==False):
            start_mod_ui()
            value.value = gui.Label('Stop MOD-UI')
            blur_pedalboard_buttons(True)
            configure_mod_host_button.disabled=True
            configure_mod_host_button.blur()
            configure_mod_host_button.chsize()
            logging.info("MOD-UI started.")
        else:
            start_mod_host()
            for pb in pedalboards_button:
                pb.disabled=False
                pb.chsize()
            configure_mod_host_button.disabled=False
            configure_mod_host_button.chsize()
            value.value = gui.Label('Start MOD-UI')
            logging.info("MOD-UI stopped.")
    else:
        logging.ciritical("Cannot start mod-ui, because jackd is not running")

def mod_host_service(value):
    global mod_host
    if(check_jack()==True):
        if(mod_host==False):
            mod_host=systemctl("mod-host-pipe",True)
            blur_pedalboard_buttons(False)
            value.value = gui.Label('Stop MOD-HOST')
        else:
            systemctl("mod-host-pipe",False)
            mod_host=False
            blur_pedalboard_buttons(True)
            value.value = gui.Label('Start MOD-HOST')
    else:
        logging.ciritcal("Cannot start mod-host, because jackd is not running")

def jack_service(value):
    if(check_jack()==True):
        systemctl("mod-ui",False)
        mod_ui=False
        systemctl("mod-host",False)
        systemctl("mod-host-pipe",False)
        mod_host=False
        systemctl("jack2",False)
        sleep(2)
        systemctl("jack2",True)
        mod_host=systemctl("mod-host-pipe",True)
        configure_mod_host_button.disabled=False
        configure_mod_host_button.value = gui.Label('Stop MOD-HOST')
        configure_mod_host_button.chsize()
        configure_mod_ui_button.disabled=False
        configure_mod_ui_button.value = gui.Label('Start MOD-UI')
        configure_mod_ui_button.chsize()

def halt_service():
    subprocess.call(shlex.split("/sbin/halt"))

def start_mod_host():
    global mod_host, mod_ui
    systemctl("mod-ui",False)
    systemctl("mod-host",False)
    mod_ui=False
    mod_host=systemctl("mod-host-pipe",True)
    if(mod_host==True):
        blur_pedalboard_buttons(False)
    start_autoconnect()

def start_mod_ui():
    global mod_host, mod_ui
    stop_autoconnect()
    systemctl("mod-host-pipe",False)
    mod_host=False
    systemctl("mod-host",True)
    mod_ui=systemctl("mod-ui",True)
    if(mod_ui==True):
        blur_pedalboard_buttons(True)

def check_jack():
    jackwait=subprocess.call(JACKWAIT+">/dev/null 2>&1",shell=True)
    if(jackwait!=0):
        return(False)
    else:
        return(True)

def systemctl(service,run):
    if(run==True):
        if(subprocess.call(shlex.split(SYSTEMCTL + " start "+service))!=0):
            logging.error("Cannot start %s" % service)
            return(False)
        else:
            return(True)
    else:
        if(subprocess.call(shlex.split(SYSTEMCTL + " stop "+service))!=0):
            logging.error("Cannot stop %s" % service)
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

def stop_autoconnect():
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

    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

    if(get_username()!='root'):
       logging.critical("Program must run as root.")
       exit(101)

    if(check_jack()==False):
        logging.critical("jackd is not running")
        exit(102)
    else:
        start_mod_host()

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
                logging.warning("Driver: %s failed." % driver)
                continue
            logging.info("Driver: %s" % driver)
            found = True
            break
        if not found:
            raise Exception('No suitable video driver found!')
        if found:
            size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
            pygame.display.set_mode(size, pygame.FULLSCREEN)
            logging.info("Screen %s" % str(size))

    # Start gui
    theme = gui.Theme("/zynthian/zynthian-stage-ui/themes/default")
    stage = gui.Desktop(theme=theme)
    stage.connect(gui.QUIT, stage.quit, None)
    stage.run(main_gui())
    logging.info("End.")

if(__name__=="__main__"):
    main()
    exit(0)
