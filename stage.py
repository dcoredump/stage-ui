#!/usr/bin/python3
"""
Zynthian stage gui
"""
import pygame
import os, stat, sys
import re
import subprocess
import psutil
import pwd
from pygame.locals import *
from pgu import gui
from pgu import html

# from pgu.gui import layout

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

mod_ui=None
mod_host=None

##############################################################################
# Functions
##############################################################################

def main_gui():
    global tab_index_group, tab_box, pedalboards_button, mod_host
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

    # System container ######################################################
    system_header = """
<form id='form'>
    """
    system_footer = """
<input type='button' value='Okay' onclick='print(form.results())'> <input type='button' value='Cancel' onclick='print(form.results())'>
    """
    system_samplerate_table = """
<table style='border:1px; border-color: #000088; background: #ccccff; margin: 8px; padding: 8px;'>
<tr><td>Samplerate:<br>
<input type='radio' name='samplerate' value='44100' checked>44.100 Hz<br>
<input type='radio' name='samplerate' value='48000'>48.000 Hz
</table>
    """
    system_buffers_table = """
<table style='border:1px; border-color: #000088; background: #ccccff; margin: 8px; padding: 8px;'>
<tr><td>Buffers:<br>
<input type='radio' name='buffers' value='256' checked>256 bytes<br>
<input type='radio' name='buffers' value='128'>128 bytes
</table>
    """
    system_html = system_header + system_samplerate_table + system_buffers_table + system_footer
    system_container = html.HTML(system_html, align=-1, valign=-1, width=1280, height=1000)

    # Configure container ######################################################
    voice_container = gui.Container(width=1280, height=720)
    configure_container=gui.Container(width=1280,height=720)
    configure_mod_ui_button=gui.Button("Start MOD-UI")
    configure_mod_ui_button.connect(gui.CLICK, mod_ui_service,configure_mod_ui_button)
    configure_container.add(configure_mod_ui_button,10,10)
    if(not mod_host):
        configure_mod_host_button=gui.Button("Start MOD-HOST")
    else:
        configure_mod_host_button=gui.Button("Stop MOD-HOST")
    configure_mod_host_button.connect(gui.CLICK, mod_host_service,configure_mod_host_button)
    configure_container.add(configure_mod_host_button,200,10)
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
    tab_index_button = gui.Tool(tab_index_group, gui.Label("System"), system_container)
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
    if(not mod_ui and mod_host):
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
    global mod_ui, mod_host

    if(check_jack()==True):
        if(not mod_ui):
            if(mod_host):
                mod_host.kill()
                mod_host=None
                start_mod_host()
                # Start mod-ui
                systemctl_mod_ui(True)
                value.value = gui.Label('Stop MOD-UI')
                for pb in pedalboards_button:
                    pb.disabled=True
                    pb.blur()
                    pb.chsize()
                print("MOD-UI started.")
            else:
                print("Cannot start mod-ui because mod-host is not running.")
        else:
            systemctl_mod_ui(False)
            systemctl_mod_host(False)
            for pb in pedalboards_button:
                pb.disabled=False
                pb.chsize()
            start_mod_host(True)
            mod_ui=None
            value.value = gui.Label('Start MOD-UI')
            print("MOD-UI stopped.")
    else:
        print("Cannot start mod-ui, because jackd is not running")

def mod_host_service(value):
    global mod_host
    if(check_jack()==True):
        if(not mod_host):
            start_mod_host()
            for p in pedalboards_button:
                p.disabled=False
                p.chsize()
            value.value = gui.Label('Stop MOD-HOST')
        else:
            mod_host.kill()
            mod_host=None
            for proc in psutil.process_iter():
                if proc.name() == "tail":
                    print("Killing %d" %proc.pid)
                    proc.kill()
            for p in pedalboards_button:
                p.disabled=True
                p.blur()
                p.chsize()
            value.value = gui.Label('Start MOD-HOST')
    else:
        print("Cannot start mod-host, because jackd is not running")

def check_jack():
    jackwait=subprocess.call(JACKWAIT,shell=True)
    if(jackwait!=0):
        return(False)
    else:
        return(True)

def start_mod_host():
    global mod_host

    if(not mod_host):
        mod_host_env = os.environ.copy()
        if (mod_host_env.get("LD_LIBRARY_PATH")):
            mod_host_env["LD_LIBRARY_PATH"] = "/usr/local/lib:" + mod_host_env["LD_LIBRARY_PATH"]
        else:
            mod_host_env["LD_LIBRARY_PATH"] = "/usr/local/lib"
        mod_host_env["LV2_PATH"] = "/zynthian/zynthian-plugins/lv2:/zynthian/zynthian-my-plugins/lv2"
        if (os.path.isfile(PARTRT) and os.access(PARTRT, os.X_OK)):
            mod_host = subprocess.Popen(TAIL + " -f " + MODHOST_PIPE + "|" + PARTRT + " run " + PARTRT_OPTIONS + " rt " + MODHOST + " -i",shell=True, env=mod_host_env)
        else:
            mod_host = subprocess.Popen(TAIL + " -f " + MODHOST_PIPE + "|" + MODHOST + " -i", shell=True, env=mod_host_env)
    else:
        print("mod-host is already running.")

def systemctl_mod_ui(run):
    global mod_ui
    if(run==True):
        mod_ui = subprocess.Popen(SYSTEMCTL+" start mod-ui",shell=True)
        return (mod_ui.returncode)
    else:
        mod_ui = subprocess.Popen(SYSTEMCTL + " stop mod-ui", shell=True)
        mod_ui=None
        return(0);

def systemctl_mod_host(run):
    global mod_host
    if(run==True):
        mod_host = subprocess.Popen(SYSTEMCTL+" start mod-host",shell=True)
        return (mod_host.returncode)
    else:
        mod_host = subprocess.Popen(SYSTEMCTL + " stop mod-host", shell=True)
        mod_host=None
        return (0)

def get_username():
    return pwd.getpwuid( os.getuid() )[ 0 ]

##############################################################################
# Callback functions
##############################################################################

def tab():
    tab_box.widget = tab_index_group.value

##############################################################################
# Main
##############################################################################

def main():
    global stage

    if(get_username()!='root'):
        print("Program must run as root.")
        exit(101)

    if(check_jack()==False):
        print("jackd is not running")
    else:
        systemctl_mod_host(False)
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
    exit(999)