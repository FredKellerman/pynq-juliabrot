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
from juliabrot import JuliabrotTile, JuliabrotGrid
from cv2 import cvtColor, COLOR_HSV2RGB, COLOR_HSV2BGR, COLOR_RGB2HSV

def rgb_iter_max(in_tile, h=1.0, s=1.0, v=1.0, modulo=255, in_colors = None) :
    if in_colors == None :
        in_colors = []
        in_colors.append("#000000")
    pix_mod = -10
    iter_mod = 7
    grad_factor = 100
    pix_mod2 = 10
    max_iter = in_tile.grid.max_iterations
    data = in_tile.data.iterations
    rgb = np.empty([data.shape[0], data.shape[1], 3], dtype=np.uint8)
    pix = np.uint8(data[:,:] * (255.5 / max_iter * modulo))
    rgb[:,:,0] = pix[:,:] * pix_mod
    rgb[:,:,1] =  0 #pix[:,:]
    rgb[:,:,2] =  0 #pix[:,:]
    mandel_rgb = int(in_colors[0][1::],16)
    rgb[data[:,:] == max_iter,2] = (mandel_rgb & 0xff)
    rgb[data[:,:] == max_iter,1] = ((mandel_rgb >> 8) & 0xff)
    rgb[data[:,:] == max_iter,0] = ((mandel_rgb >> 16) & 0xff)
    rgb[data[:,:] <= (max_iter/grad_factor-1), 0] = pix_mod2 * pix[data[:,:] <= (max_iter/grad_factor-1)]
    rgb[data[:,:] <= (max_iter/grad_factor-1), 1] = pix_mod2 * pix[data[:,:] <= (max_iter/grad_factor-1)]
    rgb[data[:,:] <= (max_iter/grad_factor-1), 2] = pix_mod2 * pix[data[:,:] <= (max_iter/grad_factor-1)]
    return rgb

def color_log(in_tile, h=1.0, s=1.0, v=1.0, modulo=255, in_colors = None) :
    if in_colors == None :
        in_colors = []
        in_colors.append("#000000")
    color = np.empty(shape=(1, 1, 3), dtype=np.float32)
    max_iter = in_tile.grid.max_iterations
    data = in_tile.data.iterations
    mandel_rgb = int(in_colors[0][1::],16)
    hsv = np.empty(shape=(data.shape[0], data.shape[1], 3), dtype=np.float32)
    hsv[:,:,0] = h * 360
    hsv[:,:,1] = s
    l_data = np.log10(1+(data[:,:]%modulo))
    l_max = np.max(l_data)
    hsv[:,:,2] = l_data[:,:] * v / l_max
    color[0,0,2] = (mandel_rgb & 0xff) / 255
    color[0,0,1] = ((mandel_rgb >> 8) & 0xff) / 255
    color[0,0,0] = ((mandel_rgb >> 16) & 0xff) / 255
    color_hsv = cvtColor(color, COLOR_RGB2HSV)
    hsv[data[:,:] == max_iter, :] = color_hsv
    rgb = (cvtColor(hsv, COLOR_HSV2RGB) * 255).astype(np.uint8)
    return rgb

def color_rainbow(in_tile, h=1.0, s=1.0, v=1.0, modulo=255, in_colors=None) :
    if in_colors == None :
        in_colors = []
        in_colors.append("#000000")
    rgb = int(in_colors[0][1::],16)
    mandel_rgb = np.empty(shape=(1,1,3), dtype=np.float32)
    mandel_rgb[0,0,2] = (rgb & 0xff) / 255
    mandel_rgb[0,0,1] = ((rgb >> 8) & 0xff) / 255
    mandel_rgb[0,0,0] = ((rgb >> 16) & 0xff) / 255
    mandel_hsv = cvtColor(mandel_rgb, COLOR_RGB2HSV)
    data = in_tile.data.iterations
    max_iter = int(in_tile.grid.max_iterations)
    color_hsv = np.empty(shape=(data.shape[0], data.shape[1], 3), dtype=np.float32)
    inv_mod = 1 / modulo
    color_hsv[:,:,0] = 360 * ((h + (data[:,:] % modulo) * inv_mod ) % 1.0) # cv2 treats h as 0-360 degrees!
    color_hsv[:,:,1] = s
    color_hsv[data[:,:] < max_iter, 2] = v
    color_hsv[data[:,:] == max_iter, :] = mandel_hsv
    rgb = (cvtColor(color_hsv, COLOR_HSV2RGB) * 255).astype(np.uint8)
    return rgb

def color_rainbow2(in_tile, h=1.0, s=1.0, v=1.0, modulo=255, in_colors=None) :
    if in_colors == None :
        in_colors = []
        in_colors.append("#000000")
    rgb = int(in_colors[0][1::],16)
    mandel_rgb = np.empty(shape=(1,1,3), dtype=np.float32)
    mandel_rgb[0,0,2] = (rgb & 0xff) / 255
    mandel_rgb[0,0,1] = ((rgb >> 8) & 0xff) / 255
    mandel_rgb[0,0,0] = ((rgb >> 16) & 0xff) / 255
    mandel_hsv = cvtColor(mandel_rgb, COLOR_RGB2HSV)
    data = in_tile.data.iterations
    max_iter = int(in_tile.grid.max_iterations)
    color_hsv = np.empty(shape=(data.shape[0], data.shape[1], 3), dtype=np.float32)
    inv_mod = 1 / modulo
    color_hsv[:,:,0] = 360 * ((h + (data[:,:] % modulo) * inv_mod ) % 1.0)
    color_hsv[:,:,1] = (.3 + (s + (data[:,:] % modulo) * inv_mod ) % 1.0)
    color_hsv[color_hsv[:,:,1] > 1.0, 1] = s
    color_hsv[data[:,:] < max_iter, 2] = v
    color_hsv[data[:,:] == max_iter, :] = mandel_hsv
    rgb = (cvtColor(color_hsv, COLOR_HSV2RGB) * 255).astype(np.uint8)
    return rgb

def color_classic(in_tile, h=1.0, s=1.0, v=1.0, modulo=255, in_colors=None) :
    if in_colors == None :
        in_colors = []
        in_colors.append("#000000")
    rgb = int(in_colors[0][1::],16)
    mandel_rgb = np.empty(shape=(1,1,3), dtype=np.float32)
    mandel_rgb[0,0,2] = (rgb & 0xff) / 255
    mandel_rgb[0,0,1] = ((rgb >> 8) & 0xff) / 255
    mandel_rgb[0,0,0] = ((rgb >> 16) & 0xff) / 255
    mandel_hsv = cvtColor(mandel_rgb, COLOR_RGB2HSV)
    data = in_tile.data.iterations
    max_iter = in_tile.grid.max_iterations
    color_hsv = np.empty(shape=(data.shape[0], data.shape[1], 3), dtype=np.float32)
    color_hsv[:,:,0] = 360 * ((h + (data[:,:] % modulo) * (4/max_iter)) % 1.0)
    color_hsv[:,:,1] = s
    color_hsv[data[:,:] < max_iter, 2] = v
    color_hsv[data[:,:] == max_iter,:] = mandel_hsv
    rgb = (cvtColor(color_hsv, COLOR_HSV2RGB) * 255).astype(np.uint8)
    return rgb

# TBD - not working
'''
def color_range(in_tile, h=1.0, s=1.0, v=1.0, in_colors=None) :
    if in_colors == None :
        in_colors = []
        in_colors.append("#000000")
        in_colors.append("#ff8000")
        in_colors.append("#0000ff")
    rgb = int(in_colors[0][1::],16)
    mandel_rgb = np.empty(shape=(1,1,3), dtype=np.float32)
    mandel_rgb[0,0,2] = (rgb & 0xff) / 255
    mandel_rgb[0,0,1] = ((rgb >> 8) & 0xff) / 255
    mandel_rgb[0,0,0] = ((rgb >> 16) & 0xff) / 255
    mandel_hsv = rgb2hsv(mandel_rgb)
    rgb = int(in_colors[1][1::],16)
    bound1 = np.empty(shape=(1,1,3), dtype=np.float32)
    bound1[0,0,2] = (rgb & 0xff) / 255
    bound1[0,0,1] = ((rgb >> 8) & 0xff) / 255
    bound1[0,0,0] = ((rgb >> 16) & 0xff) / 255
    bound1_hsv = rgb2hsv(bound1)
    rgb = int(in_colors[2][1::],16)
    bound2 = np.empty(shape=(1,1,3), dtype=np.float32)
    bound2[0,0,2] = (rgb & 0xff) / 255
    bound2[0,0,1] = ((rgb >> 8) & 0xff) / 255
    bound2[0,0,0] = ((rgb >> 16) & 0xff) / 255
    bound2_hsv = rgb2hsv(bound2)

    data = in_tile.data.iterations
    max_iter = in_tile.grid.max_iterations
    color_hsv = np.empty(shape=(data.shape[0], data.shape[1], 3), dtype=np.float32)
    
    if (bound1_hsv[0,0,0] > bound2_hsv[0,0,0]) :
        u = bound1_hsv[0,0,0] + .0000000001
        l = bound2_hsv[0,0,0] + .0000000001
        print(u,l)
        r = u - l
    else :
        u = bound2_hsv[0,0,0] + .0000000001
        l = bound1_hsv[0,0,0] + .0000000001
        print(u,l)
        r = l - u

    color_hsv[:,:,0] = (l + r * data[:,:] * (1/max_iter)) % 1.0
    color_hsv[:,:,1] = s
    color_hsv[data[:,:] < max_iter, 2] = v
    color_hsv[data[:,:] == max_iter,:] = mandel_hsv
    rgb = hsv2rgb(color_hsv) * 255
    return rgb
'''