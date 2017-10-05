#!/usr/bin/python3
"""
Zynthian stage gui
"""
import pygame
import os
import re
from pygame.locals import *
from pgu import gui
from pgu import html
#from pgu.gui import layout

##############################################################################
# Globals
##############################################################################

FRAMEBUFFER_DEV="/dev/fb0"
PEDALBOARDS_PATH=os.environ['HOME']+"/.pedalboards"

##############################################################################
# Functions
##############################################################################

def main_gui():
    global tab_index_group,tab_box

# Pedalboards container ######################################################
    pedalboard_header="""
<h1>Pedalboards</h1>
<form id='form'>
    """
    pedalboard_footer="""
    """
    pedalboard_pedalboards="""
<table style='border:1px; border-color: #000088; background: #ccccff; margin: 8px; padding: 8px;'>
    """
    for p in get_pedalboard_names():
        pedalboard_pedalboards+="<tr><td><input type='button' value='"+p+"' onclick='load_pedalboard(p)'>"
    pedalboard_pedalboards+="</table>"

    pedalboard_html=pedalboard_header+pedalboard_pedalboards+pedalboard_footer
    pedalboards_container = html.HTML(pedalboard_html,align=-1,valign=-1,width=1280,height=1000)

# System container ######################################################
    system_header="""
<h1>System</h1>
<form id='form'>
    """
    system_footer="""
<input type='button' value='Okay' onclick='print(form.results())'> <input type='button' value='Cancel' onclick='print(form.results())'>
    """
    system_samplerate_table="""
<table style='border:1px; border-color: #000088; background: #ccccff; margin: 8px; padding: 8px;'>
<tr><td>Samplerate:<br>
<input type='radio' name='samplerate' value='44100' checked>44.100 Hz<br>
<input type='radio' name='samplerate' value='48000'>48.000 Hz
</table>
    """
    system_buffers_table="""
<table style='border:1px; border-color: #000088; background: #ccccff; margin: 8px; padding: 8px;'>
<tr><td>Buffers:<br>
<input type='radio' name='buffers' value='256' checked>256 bytes<br>
<input type='radio' name='buffers' value='128'>128 bytes
</table>
    """
    system_html=system_header+system_samplerate_table+system_buffers_table+system_footer
    system_container = html.HTML(system_html,align=-1,valign=-1,width=1280,height=1000)

# Tabs container ######################################################

    # Tab index group
    tab_index_group = gui.Group()
    tab_index_group.connect(gui.CHANGE,tab)

    # Tab index labels
    tab_index_table=gui.Table()
    tab_index_table.tr()
    tab_index_button=gui.Tool(tab_index_group,gui.Label("Pedalboards"),pedalboards_container)
    tab_index_table.td(tab_index_button)
    tab_index_button=gui.Tool(tab_index_group,gui.Label("System"),system_container)
    tab_index_table.td(tab_index_button)
    tab_index_table.tr()

    # Tab box
    spacer = gui.Spacer(1280,720)
    tab_box = gui.ScrollArea(spacer,height=720)
    tab_index_table.td(tab_box,style={'border':1},colspan=40)

    return(tab_index_table)

def get_pedalboard_names():
    pedalboards=[]
    for p in os.listdir(PEDALBOARDS_PATH):
        m=re.search("^(.+)\.pedalboard",p)
        if(m):
            pedalboards.append(m.group(1))
    return(pedalboards)

def load_pedalboard(pedalboard):
    print(pedalboard)

##############################################################################
# Callback functions
##############################################################################

def tab():
    tab_box.widget = tab_index_group.value
    
##############################################################################
# Main
##############################################################################

# Check for X11 or framebuffer
found = False
disp_no = os.getenv('DISPLAY')
if not disp_no:
    os.putenv('SDL_FBDEV',FRAMEBUFFER_DEV)
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
theme=gui.Theme("themes/default")
stage = gui.Desktop(theme=theme)
stage.connect(gui.QUIT,stage.quit,None)
stage.run(main_gui())
