#!/usr/bin/python3
"""
Zynthian stage gui
"""
import pygame
import os, stat, sys
import re
import subprocess
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
MODHOST_PIPE = "/tmp/mod-host"

mod_ui=None

##############################################################################
# Functions
##############################################################################

def main_gui():
    global tab_index_group, tab_box, pedalboards_button
    pedalboards_button = []

    # Pedalboards container ######################################################
    pedalboards_container=gui.Container(width=1280,height=720)
    y=10
    for p in get_pedalboard_names():
        pedalboards_button.append(gui.Button(p))
        if(mod_ui):
            pedalboards_button[-1].blur()
            pedalboards_button[-1].chsize()
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
    configure_container=gui.Container(width=1280,height=720)
    configure_button=gui.Button("Start MOD-UI")
    configure_button.connect(gui.CLICK, mod_ui_server,configure_button)
    configure_container.add(configure_button,10,10)

    # Tabs container ######################################################
    # Tab index group
    tab_index_group = gui.Group()
    tab_index_group.connect(gui.CHANGE, tab)
    # Tab index labels
    tab_index_table = gui.Table()
    tab_index_table.tr()
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
    if(not mod_ui):
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

def mod_ui_server(value):
    global mod_ui
    if(not mod_ui):
        # Start mod-ui
        mod_ui_env = os.environ.copy()
        mod_ui_env["LD_LIBRARY_PATH"]="/usr/local/lib:"+mod_ui_env["LD_LIBRARY_PATH"]
        mod_ui_env["LV2_PATH"]="/zynthian/zynthian-plugins/lv2:/zynthian/zynthian-my-plugins/lv2"
        mod_ui_env["MOD_SCREENSHOT_JS"]="/zynthian/zynthian-sw/mod-ui/screenshot.js"
        mod_ui_env["MOD_PHANTOM_BINARY"]="/usr/bin/phantomjs"
        mod_ui_env["MOD_DEVICE_WEBSERVER_PORT"]="8888"
        mod_ui_env["MOD_DEV_ENVIRONMENT"]="0"
        mod_ui_env["MOD_SYSTEM_OUTPUT"]="1"
        mod_ui_env["MOD_HOST"]="1"
        mod_ui=subprocess.Popen("python3 /zynthian/zynthian-sw/mod-ui/server.py",shell=True, env=mod_ui_env)
        value.value = gui.Label('Stop MOD-UI')
        for pb in pedalboards_button:
            pb.disabled=True
            pb.blur()
            pb.chsize()
        print("MOD-UI started.")
    elif(mod_ui.pid):
        for pb in pedalboards_button:
            pb.disabled=False
            pb.chsize()
        mod_ui.terminate()
        mod_ui=None
        value.value = gui.Label('Start MOD-UI')
        print("MOD-UI stopped.")

##############################################################################
# Callback functions
##############################################################################

def tab():
    tab_box.widget = tab_index_group.value

##############################################################################
# Main
##############################################################################

def main():
    global stage, mod_ui_started

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