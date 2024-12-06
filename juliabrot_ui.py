#!/usr/bin/env python
# coding: utf-8

""" BSD 3-Clause License

Copyright (c) 2020, Fred Kellerman
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import numpy as np
import os
from ipycanvas import Canvas, MultiCanvas, hold_canvas
from ipywidgets import interact, Button, ColorPicker, FloatLogSlider, IntSlider, FloatSlider, link, AppLayout, HBox, VBox, Dropdown
from juliabrot import JuliabrotGrid, JuliabrotTile, Juliabrot, JuliabrotGridSettings
from cv2 import imwrite
import juliabrot_coloring as jcolor
import copy
#from fxpmath import Fxp

#########################################################
#  State variables section
#########################################################

juliabrot = None
background_layer = 0
drawing_layer = 1
interaction_layer = 2
jgrid_history = []
status_offset = 25
catalog_path = './catalog/'
remote_host = None
remote_user = None
remote_password = None
remote_keyfile = None

# Define precision of calculations (for fxpmath's Fxp)
_FXP_N_WORD = 80
_FXP_N_FRAC = 77

# Setup the remote control parameters
def remote_setup(host, user, password, keyfile=None) :
    global remote_user, remote_password, remote_keyfile
    remote_user = user
    remote_password = password
    remote_keyfile = keyfile

#########################################################
#  Canvas actions section
#########################################################
def display_info(in_canvases, in_grid) :
    global color_it
    in_canvases[drawing_layer].clear()
    y_spacing = 30
    y_pos = y_spacing
    in_canvases[drawing_layer].fill_text('ul X: ' + str(in_grid.settings.ulX), in_canvases[drawing_layer].width/2.2+10, y_pos)
    y_pos += y_spacing 
    in_canvases[drawing_layer].fill_text('ul Y: ' + str(in_grid.settings.ulY), in_canvases[drawing_layer].width/2.2+10, y_pos)
    y_pos += y_spacing 
    in_canvases[drawing_layer].fill_text('lr X: ' + str(in_grid.settings.lrX), in_canvases[drawing_layer].width/2.2+10, y_pos)
    y_pos += y_spacing 
    in_canvases[drawing_layer].fill_text('lr Y: ' + str(in_grid.settings.lrY), in_canvases[drawing_layer].width/2.2+10, y_pos)
    y_pos += y_spacing 
    in_canvases[drawing_layer].fill_text('cX: ' + str(in_grid.settings.cX), in_canvases[drawing_layer].width/2.2+10, y_pos)
    y_pos += y_spacing 
    in_canvases[drawing_layer].fill_text('cY: ' + str(in_grid.settings.cY), in_canvases[drawing_layer].width/2.2+10, y_pos)
    y_pos += y_spacing
    in_canvases[drawing_layer].fill_text('sizeX: ' + str(int(in_grid.settings.sizeX)), in_canvases[drawing_layer].width/2.2+10, y_pos)
    y_pos += y_spacing
    in_canvases[drawing_layer].fill_text('sizeY: ' + str(int(in_grid.settings.sizeY)), in_canvases[drawing_layer].width/2.2+10, y_pos)
    y_pos += y_spacing 
    if in_grid.settings.mandelbrot_mode == True :
        m_str = 'Mode: Mandelbrot'
    else :
        m_str = 'Mode: Julia'
    m_str = m_str + (' Color' if color_it == True else ' BW')
    in_canvases[drawing_layer].fill_text(m_str, in_canvases[drawing_layer].width/2.2+10, y_pos)
    y_pos += y_spacing
    '''
    if in_grid.settings.ulX == in_grid.settings.lrX :
        in_canvases[drawing_layer].fill_text('Warn: hstep = 0', in_canvases[drawing_layer].size[0]/2+30, y_pos)
    else :
        delta = (in_grid.settings.lrX - in_grid.settings.ulX) * (np.longdouble(1.0) / in_grid.settings.sizeX)
        detal = _to_fixed(delta)
        in_canvases[drawing_layer].fill_text('hstep: ' + str(delta), in_canvases[drawing_layer].size[0]/2+30, y_pos)
    '''

def show_canvas(in_canvases, in_tiles, in_offset=(0,0)) :
    global color_it
    save_style = canvases[interaction_layer].fill_style
    canvases[interaction_layer].fill_style = '#aaaa00'
    in_canvases[interaction_layer].clear()
    if color_it == True:
        in_canvases[interaction_layer].fill_text('Status: Coloring', in_canvases[drawing_layer].width/2+30, in_canvases[drawing_layer].height-status_offset)
    else :
        in_canvases[interaction_layer].fill_text('Status: Coloring BW', in_canvases[drawing_layer].width/2+30, in_canvases[drawing_layer].height-status_offset)
    in_canvases[interaction_layer].clear()
    canvases[interaction_layer].fill_style = save_style
    for in_tile in in_tiles :
        rgb = color_data(in_tile, color_it)
    in_canvases[background_layer].put_image_data(rgb, in_offset[0] + in_tile.limits[0], in_offset[1] + in_tile.limits[1])

def draw_fractal(in_canvases, in_tiles, in_progress_report = False) :
    save_style = canvases[interaction_layer].fill_style
    canvases[interaction_layer].fill_style = '#aa4400'
    in_canvases[interaction_layer].clear()
    in_canvases[interaction_layer].fill_text('Status: Computing', in_canvases[drawing_layer].width/2+10, in_canvases[drawing_layer].height-status_offset)
    for in_tile in in_tiles :
        juliabrot.compute(in_tile, in_progress_report)
    in_canvases[interaction_layer].clear()
    canvases[interaction_layer].fill_style = save_style
    show_canvas(in_canvases, in_tiles)

    jgrid_history.append(copy.deepcopy(jgrid)) # Have to deep copy to retain the member settings
    # But we can free up the history data, since it will get recalculated again anyways
    for tile in jgrid_history[-1].tile_list :
        tile.data = None

def draw_line(in_canvas, in_start, in_end) :
    in_canvas.begin_path()
    in_canvas.move_to(in_start[0], in_start[1])
    in_canvas.line_to(in_end[0], in_end[1])
    in_canvas.stroke()
    in_canvas.close_path()

def _to_fixed(x) :
    return x #Fxp(x, True, _FXP_N_WORD, _FXP_N_FRAC)

#########################################################
#  Mouse events section
#########################################################

def on_mouse_down(x, y) :
    global drawing, ulx_select, uly_select, lrx_select, lry_select, jgrid
    if x <= jgrid.settings.sizeX :
        if not drawing :
            ulx_select = int(x)
            uly_select = int(y)
        else :
            with hold_canvas(canvases) :
                canvases[interaction_layer].clear()

            if abs(ulx_select - x) <= 2 :
                # Double click in same spot sets Julia values
                h_step = (jgrid.settings.lrX - jgrid.settings.ulX) / jgrid.settings.sizeX
                jgrid.settings.cX = _to_fixed(jgrid.settings.ulX + h_step * x)
                jgrid.settings.cY = _to_fixed(jgrid.settings.ulY - h_step * y)
                display_info(canvases, jgrid)
                if jgrid.settings.mandelbrot_mode == False :
                    draw_fractal(canvases, jgrid.tile_list)
            else :
                lrx_select = int(x)
                lry_select = int(uly_select + (x - ulx_select) * np.longdouble(jgrid.settings.sizeY) / jgrid.settings.sizeX)
                h_step = (jgrid.settings.lrX - jgrid.settings.ulX) * (np.longdouble(1.0) / jgrid.settings.sizeX)
                jgrid.settings.ulX = _to_fixed(jgrid.settings.ulX + h_step * ulx_select)
                jgrid.settings.ulY = _to_fixed(jgrid.settings.ulY - h_step * uly_select)
                jgrid.settings.lrX = _to_fixed(jgrid.settings.ulX + h_step * (lrx_select - ulx_select))
                jgrid.settings.lrY = _to_fixed(jgrid.settings.ulY + h_step * (uly_select - lry_select))
                display_info(canvases, jgrid)
                draw_fractal(canvases, jgrid.tile_list)
                # Reset selection box
                ulx_select = 0
                uly_select = 0
                lrx_select = jgrid.settings.sizeX-1
                lry_select = jgrid.settings.sizeY-1

        drawing = not drawing

def on_mouse_move(x, y) :
    if x <= jgrid.settings.sizeX :
        if not drawing :
            return
        y = int(uly_select + (x - ulx_select) * jgrid.settings.sizeY / jgrid.settings.sizeX)
        with hold_canvas(canvases) :
            canvases[interaction_layer].clear()
            d = canvases[interaction_layer]
            d.begin_path()
            d.move_to(ulx_select, uly_select)
            d.line_to(x, uly_select)
            d.line_to(x,y)
            d.line_to(ulx_select,y)
            d.line_to(ulx_select, uly_select)
            d.stroke()
            d.close_path()

#########################################################
#  Buttons and sliders events section
#########################################################

def bdown_button_handler(x) :
    global jgrid
    bump_pixels = bump_ud_slider.value
    if bump_pixels > 0 :
        vstep = bump_pixels * (jgrid.settings.lrX - jgrid.settings.ulX) / jgrid.settings.sizeX
    else :
        vstep = jgrid.settings.sizeY * (jgrid.settings.lrX - jgrid.settings.ulX) / jgrid.settings.sizeX
    jgrid.settings.lrY = _to_fixed(jgrid.settings.lrY + vstep)
    jgrid.settings.ulY = _to_fixed(jgrid.settings.ulY + vstep)
    display_info(canvases, jgrid)
    draw_fractal(canvases, jgrid.tile_list)

def bup_button_handler(x) :
    global jgrid
    bump_pixels = bump_ud_slider.value
    if bump_pixels > 0 :
        vstep = bump_pixels * (jgrid.settings.lrX - jgrid.settings.ulX) / jgrid.settings.sizeX
    else :
        vstep = jgrid.settings.sizeY * (jgrid.settings.lrX - jgrid.settings.ulX) / jgrid.settings.sizeX
    jgrid.settings.lrY = _to_fixed(jgrid.settings.lrY - vstep)
    jgrid.settings.ulY = _to_fixed(jgrid.settings.ulY - vstep)
    display_info(canvases, jgrid)
    draw_fractal(canvases, jgrid.tile_list)

def save_button_handler(x) :
    canvases[interaction_layer].fill_style = '#00aa00'
    canvases[interaction_layer].clear()
    canvases[interaction_layer].fill_text('Saving settings', canvases[drawing_layer].width/2+30, canvases[drawing_layer].height-status_offset)
    filename_prefix = jgrid.settings.save_json(catalog_path, color_list.value, color_list.label, hue_slider.value, sat_slider.value, val_slider.value, modulo_slider.value, picker1.value)
    save_png(catalog_path + filename_prefix + ".png")
    canvases[interaction_layer].clear()
    canvases[interaction_layer].fill_text('Settings saved', canvases[drawing_layer].width/2+30, canvases[drawing_layer].height-status_offset)

def color_data(in_tile, color_mode) :
    choice = color_list.value
    sat_val = sat_slider.value if color_mode == True else 0
    if choice == 1 :
        rgb = jcolor.color_rainbow(in_tile, hue_slider.value, sat_val, val_slider.value, modulo_slider.value, [picker1.value])
    elif choice == 2 :
        rgb = jcolor.color_classic(in_tile, hue_slider.value, sat_val, val_slider.value, modulo_slider.value, [picker1.value])
    elif choice == 3 :
        rgb = jcolor.color_log(in_tile, hue_slider.value, sat_val, val_slider.value, modulo_slider.value, [picker1.value])
    elif choice == 4 :
        rgb = jcolor.rgb_iter_max(in_tile, hue_slider.value, sat_val, val_slider.value, modulo_slider.value, [picker1.value])
    elif choice == 5 :
        rgb = jcolor.color_rainbow2(in_tile, hue_slider.value, sat_val, val_slider.value, modulo_slider.value, [picker1.value])
        #elif choice == 6 :
        #    rgb = jcolor.color_range(in_tile, hue_slider.value, sat_val, val_slider.value, [picker1.value, picker2.value, picker2.value])
    else :
        rgb = jcolor.color_rainbow(in_tile, hue_slider.value, sat_val, val_slider.value, modulo_slider.value, [picker1.value])
    return rgb

def save_png(filename, x_width=120) :
    global color_it
    grid = copy.deepcopy(jgrid)
    grid.tile_list[0].data = None
    scale = x_width / grid.tile_list[0].sizeX
    x = int(x_width)
    y = int(grid.tile_list[0].sizeY * scale)
    grid.set_size(x, y)
    tile = juliabrot.compute(grid.tile_list[0])
    tmp = color_data(tile, color_it)
    rgb = np.empty(shape=(y,x,3), dtype=np.uint8)
    rgb[:,:,0] = tmp[:,:,2]
    rgb[:,:,1] = tmp[:,:,1]
    rgb[:,:,2] = tmp[:,:,0]
    imwrite(filename, rgb)
    
def bright_button_handler(x) :
    global jgrid
    bump_pixels = bump_lr_slider.value
    if bump_pixels > 0 :
        hstep = bump_pixels * (jgrid.settings.lrX - jgrid.settings.ulX) / jgrid.settings.sizeX
    else :
        hstep = jgrid.settings.sizeX * (jgrid.settings.lrX - jgrid.settings.ulX) / jgrid.settings.sizeX
    jgrid.settings.lrX = _to_fixed(jgrid.settings.lrX - hstep)
    jgrid.settings.ulX = _to_fixed(jgrid.settings.ulX - hstep)
    display_info(canvases, jgrid)
    draw_fractal(canvases, jgrid.tile_list)

def bleft_button_handler(x) :
    global jgrid
    bump_pixels = bump_lr_slider.value
    if bump_pixels > 0 :
        hstep = bump_pixels * (jgrid.settings.lrX - jgrid.settings.ulX) / jgrid.settings.sizeX
    else :
        hstep = jgrid.settings.sizeX * (jgrid.settings.lrX - jgrid.settings.ulX) / jgrid.settings.sizeX
    jgrid.settings.lrX = _to_fixed(jgrid.settings.lrX + hstep)
    jgrid.settings.ulX = _to_fixed(jgrid.settings.ulX + hstep)
    display_info(canvases, jgrid)
    draw_fractal(canvases, jgrid.tile_list)
    
def undo_button_handler(x) :
    global jgrid, preview_data, iter_slider
    if len(jgrid_history) > 1 :
        jgrid_history.pop()  # Throw away where we're currently at
        jgrid = jgrid_history.pop()
        s1_val = jgrid.settings.max_iterations
        if iter_slider.value != s1_val :
            # The change will force a draw_fractal
            iter_slider.value = s1_val
        else :
            display_info(canvases, jgrid)
            draw_fractal(canvases, jgrid.tile_list)

def juliabrot_button_handler(x) :
    global jgrid
    jgrid.settings.mandelbrot_mode = not jgrid.settings.mandelbrot_mode
    display_info(canvases, jgrid)
    draw_fractal(canvases, jgrid.tile_list)

def color_button_handler(x) :
    global color_it
    color_it = not color_it
    show_canvas(canvases, jgrid.tile_list)
    display_info(canvases, jgrid)

def zoom_button_handler(x) :
    global jgrid
    if zoom_slider.value != 1.0 :
        if zoom_slider.value == 0.0 :
            jgrid.settings.ulX = start_ulX
            jgrid.settings.ulY = start_ulY
            jgrid.settings.lrX = start_lrX
            jgrid.settings.lrY = start_lrY
        else :
            zoom_value = np.longdouble(1.0) / zoom_slider.value
            center_X = (jgrid.settings.ulX + jgrid.settings.lrX) * .5
            center_Y = (jgrid.settings.ulY + jgrid.settings.lrY) * .5
            x_span = zoom_value * (jgrid.settings.lrX - jgrid.settings.ulX) * .5
            y_span = zoom_value * (jgrid.settings.lrY - jgrid.settings.ulY) * .5
            ulx = center_X - x_span
            uly = center_Y - y_span
            lrx = center_X + x_span
            lry = center_Y + y_span
            # The computations will wrap if the numbers exceed +/-2.0 (which is where the set lives anyways)
            if ulx <= 2.5 and ulx >= -2.5 :
                jgrid.settings.ulX = _to_fixed(ulx)
            if uly <= 2.5 and uly >= -2.5 :
                jgrid.settings.ulY = _to_fixed(uly)
            if lrx <= 2.5 and lrx >= -2.5 :
                jgrid.settings.lrX = _to_fixed(lrx)
            if lry <= 2.5 and lry >= -2.5 :
                jgrid.settings.lrY = _to_fixed(lry)
        display_info(canvases, jgrid)
        draw_fractal(canvases, jgrid.tile_list)

def iter_slider_handler(x) :
    global jgrid
    jgrid.settings.max_iterations = int(iter_slider.value)
    display_info(canvases, jgrid)
    draw_fractal(canvases, jgrid.tile_list)

def color_select_handler(x) :
    show_canvas(canvases, jgrid.tile_list)
    
    
def color_picker1_handler(x) :
    show_canvas(canvases, jgrid.tile_list)

def color_picker2_handler(x) :
    show_canvas(canvases, jgrid.tile_list)

def color_picker3_handler(x) :
    show_canvas(canvases, jgrid.tile_list)

def hue_slider_handler(x) :
    show_canvas(canvases, jgrid.tile_list)

def sat_slider_handler(x) :
    show_canvas(canvases, jgrid.tile_list)

def val_slider_handler(x) :
    show_canvas(canvases, jgrid.tile_list)

def modulo_slider_handler(x) :
    show_canvas(canvases, jgrid.tile_list)

#########################################################
#  Setup of GUI
#########################################################

def init_ui(in_grid) :
    global start_ulX, start_ulY, start_lrX, start_lrY, jgrid, juliabrot
    if type(in_grid) == str :
        js = JuliabrotGridSettings()
        jg = JuliabrotGrid(js, in_grid)
        jgrid = copy.deepcopy(jg)
    else :
        jgrid = copy.deepcopy(in_grid)  # Fork off from the originator (which means gui has it's own image data)

    start_ulX = jgrid.settings.ulX
    start_ulY = jgrid.settings.ulY
    start_lrX = jgrid.settings.lrX
    start_lrY = jgrid.settings.lrY
    juliabrot = Juliabrot(jgrid.settings.kernel_mode)
    
    '''
    Issues when using remote is a signal that is causing exceptions when loading pynq's xlnx prevent this from working for now!
    
    # Are we using this locally or remotely?  If exception, assume remote.
    try :
        juliabrot = Juliabrot(jgrid.settings.kernel_mode)
    except :
        from rpyc.utils.zerodeploy import DeployedServer
        from plumbum import SshMachine
        machine = SshMachine(remote_host, user=remote_user, password=remote_password, keyfile=remote_keyfile)
        server = DeployedServer(machine)
        rsession = server.classic_connect()
        print(rsession.modules.sys.platform)
        rsession.modules.os.chdir('/home/xilinx/jupyter_notebooks/pynq-juliabrot')
        rsys = rsession.modules.sys
        rsys.path.append('/home/xilinx/jupyter_notebooks/pynq-juliabrot')
        juliabrot = rsession.juliabrot.Juliabrot(jgrid.settings.kernel_mode)
    '''

def draw_roaming_ui() :
    global iter_slider, reset_button, color_it_button, juliabrot_button, canvases
    global drawing, uly_select, ulx_select, color_list, picker1, picker2, bump_ud_slider, hue_slider, sat_slider, val_slider
    global lry_select, lrx_select, color_it, modulo_slider, picker3, bump_lr_slider, zoom_slider, save_button

    # This establishes the size of the preview gui
    drawing = False
    color_it = True
    uly_select = 0
    ulx_select = 0
    lry_select = jgrid.settings.sizeY
    lrx_select = jgrid.settings.sizeX
    canvases = MultiCanvas(3, width=jgrid.settings.sizeX*2.5, height=jgrid.settings.sizeY+75)
    canvases[drawing_layer].font = '15px serif'
    canvases[drawing_layer].fill_style = '#aaaaaa'
    canvases[drawing_layer].line_width = 3
    canvases[interaction_layer].font = '35px serif'
    canvases[interaction_layer].fill_style = '#eee800'
    canvases[interaction_layer].stroke_style = '#ffffff'
    canvases[interaction_layer].line_width = 3
    iter_slider  = FloatLogSlider(description='Iterations:', base=10, value=jgrid.settings.max_iterations, min=1, max=7, step=.01, continuous_update=False)
    iter_slider.observe(handler=iter_slider_handler, names='value')
    max_lr_bump = jgrid.settings.sizeX
    max_ud_bump = jgrid.settings.sizeY
    bump_ud_slider = IntSlider(description='Bump UD pix:', value=1, min=0, max=max_ud_bump , step=1, continuous_update=False)
    bump_lr_slider = IntSlider(description='Bump LR pix:', value=1, min=0, max=max_lr_bump , step=1, continuous_update=False)
    zoom_slider = FloatSlider(description='Zoom:', value=2.0, min=0.0, max=1000.0, step=.001, continuous_update=False)
    #zoom_slider.observe(handler=zoom_button_handler, names='value')
    hue_slider = FloatSlider(description='Hue :', value=jgrid.settings.hue, min=0.0, max=1.0, step=.001, continuous_update=False)
    sat_slider = FloatSlider(description='Sat:', value=jgrid.settings.sat, min=0.0, max=1.0, step=.01, continuous_update=False)
    val_slider = FloatSlider(description='Val:', value=jgrid.settings.val, min=0.0, max=1.0, step=.02, continuous_update=False)
    hue_slider.observe(handler=hue_slider_handler, names='value')
    sat_slider.observe(handler=sat_slider_handler, names='value')
    val_slider.observe(handler=val_slider_handler, names='value')
    modulo_slider = IntSlider(description='Modulo:', value=jgrid.settings.modulo, min=1, max=1000000, step=1, continuous_update=False)
    modulo_slider.observe(handler=modulo_slider_handler, names='value')
    canvases[interaction_layer].on_mouse_down(on_mouse_down)
    canvases[interaction_layer].on_mouse_move(on_mouse_move)
    reset_button = Button(description='Zoom', disabled=False, button_style='', tooltip='Click to use zoom slider setting for zoom', icon='')
    reset_button.on_click(zoom_button_handler)
    save_button = Button(description='Save', disabled=False, button_style='', tooltip='Click to save as JSON settings file', icon='')
    save_button.on_click(save_button_handler)
    color_it_button = Button(description='Color/BW', disabled=False, button_style='', tooltip='Click for BW or Color', icon='')
    color_it_button.on_click(color_button_handler)
    juliabrot_button = Button(description='JM Mode', disabled=False, button_style='', tooltip='Click for Julia or Mandelbrot', icon='')
    juliabrot_button.on_click(juliabrot_button_handler)
    undo_button = Button(description='Undo', disabled=False, button_style='', tooltip='Click to revert to last view', icon='')
    undo_button.on_click(undo_button_handler)
    bleft_button = Button(description='Bump L', disabled=False, button_style='', tooltip='Click to nudge left num bump LR pixels', icon='')
    bleft_button.on_click(bleft_button_handler)
    bright_button = Button(description='Bump R', disabled=False, button_style='', tooltip='Click to nudge right num bump LR pixels', icon='')
    bright_button.on_click(bright_button_handler)
    bup_button = Button(description='Bump U', disabled=False, button_style='', tooltip='Click to nudge up num bump UD pixels', icon='')
    bup_button.on_click(bup_button_handler)
    bdown_button = Button(description='Bump D', disabled=False, button_style='', tooltip='Click to nudge down bump UD pixels', icon='')
    bdown_button.on_click(bdown_button_handler)
    picker1 = ColorPicker(description='M Color:', value=jgrid.settings.m_color)
    #picker2 = ColorPicker(description='Color 1:', value='#fff800')
    #picker3 = ColorPicker(description='Color 2:', value='#fff800')
    picker1.observe(color_picker1_handler, names='value')
    #picker2.observe(color_picker2_handler, names='value')
    #picker3.observe(color_picker3_handler, names='value')
    color_list = Dropdown(disabled=False, options=[('Rainbow', 1), ('Classic', 2), ('Log', 3), ('RGB Max Iter', 4), ('Rainbow 2', 5)], value=jgrid.settings.color_mode, description='Color Mode:', tooltip='Select built-in coloring options')
    color_list.observe(color_select_handler, names='value')
    draw_fractal(canvases, jgrid.tile_list)
    display_info(canvases, jgrid)
    return AppLayout(center=canvases, header=HBox((iter_slider, bump_ud_slider, bump_lr_slider, zoom_slider)), right_sidebar=VBox((picker1, color_list, hue_slider, sat_slider, val_slider, modulo_slider)), footer=HBox((bleft_button, bright_button, bup_button, bdown_button, color_it_button, juliabrot_button, reset_button, undo_button, save_button)))
