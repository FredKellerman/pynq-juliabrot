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

import os, copy, struct
import numpy as np
#from fxpmath import Fxp
from IPython.display import clear_output
from datetime import datetime
import zlib
import json

# This can be used to determine if this module is not being run on a PYNQ host
#  Nothing is currently implemented to do that though!
try :
    from pynq import Overlay
    import axidma # This is a pynq derived class also
except ImportError :
    Overlay = None

try :
    if os.environ['BOARD'] != 'ZUBoard_1CG' and os.environ['BOARD'] != 'Ultra96' and os.environ['BOARD'] != 'Pynq-Z1' and os.environ['BOARD'] != 'Pynq-Z2':
        print("Only for ZUBoard-1CG, Ultra96, Pynq-Z1 or Pynq-Z2 Board")
        exit(1)
except :
    pass

class JuliabrotData :
    def __init__(self) :
        self.iterations = None
        self.z = None

class JuliabrotGrid :
    def __init__(self, grid_settings, json_name=None) :
        if type(json_name) == str :
            grid_settings.load_json(json_name)
        self.settings = grid_settings
        self.tile_list = []
        JuliabrotTile(self)  # Create 1 Tile (which will self attach to tile_list)

    def set_size(self, X, Y) :
        self.settings.sizeX = int(X)
        self.settings.sizeY = int(Y)
        # Proportionally change all tiles attached and scrub data
        for tile in self.tile_list :
            tile.scale(X, Y)
            tile.data = None

class JuliabrotGridSettings :
    def __init__(self) :
        self.sizeX = None
        self.sizeY = None
        self.max_iterations = None
        self.ulX = None
        self.ulY = None
        self.lrX = None
        self.lrY = None
        self.cX  = None
        self.cY  = None
        self.mandelbrot_mode = None
        self.kernel_mode = 0
        self.color_mode = 1
        self.hue = 1.0
        self.val = 1.0
        self.sat = 1.0
        self.modulo = 255
        self.m_color = "#000000"
        self._pre_json_save = None
        self._post_json_load = None

    def save_json(self, path, color_mode, desc, hue, val, sat, modulo, m_color):
        self._to_json(0, 0, color_mode, desc, hue, val, sat, modulo, m_color)
        now = datetime.now()
        date_str = now.strftime("%d_%m_%Y-%H_%M_%S")
        name = "juliabrot_" + self._gen_crc() + "_" + date_str
        with open(path + name + ".json", "w") as write_file:
            json.dump(self._pre_json_save, write_file)
        return name

    def _gen_crc(self) :
        s = str(self.sizeX) + str(self.sizeY) + str(self.max_iterations) + str(self.ulX) \
                + str(self.ulY) + str(self.lrX) + str(self.lrY) + str(self.cX) + str(self.cY) + str(self.mandelbrot_mode)
        return hex(zlib.crc32(s.encode()))

    def _to_json(self, n_word, n_frac, color_mode, desc, hue, val, sat, modulo, m_color) :
        comments = "color desc: " + str(desc)
        
        self._pre_json_save = {
            "sizeX" : self.sizeX,
            "sizeY" : self.sizeY,
            "max_iterations" : self.max_iterations,
            "precision:" : "longdouble",
            "ulX" : str(self.ulX),
            "ulY" : str(self.ulY),
            "lrX" : str(self.lrX),
            "lrY" : str(self.lrY),
            "cX" : str(self.cX),
            "cY" : str(self.cY),
            "mandelbrot_mode" : self.mandelbrot_mode,
            "crc" : self._gen_crc(),
            "kernel_mode" : self.kernel_mode,
            "color" : {
                "mode" : color_mode,
                "hue" : hue,
                "value" : val,
                "saturation" : sat,
                "modulo" : modulo,
                "m_color" : m_color
            },
            "comments" : comments
        }

    def load_json(self, name) :
        with open(name, "r") as read_file :
            self._post_json_load = json.load(read_file)
        #Sprint(self._post_json_load)
        s = self._post_json_load
        self.sizeX = s["sizeX"]
        self.sizeY = s["sizeY"]
        self.max_iterations = s["max_iterations"]
        self.ulX = np.longdouble(s["ulX"])
        self.ulY = np.longdouble(s["ulY"])
        self.lrX = np.longdouble(s["lrX"])
        self.lrY = np.longdouble(s["lrY"])
        self.cX  = np.longdouble(s["cX"])
        self.cY  = np.longdouble(s["cY"])
        self.mandelbrot_mode = s["mandelbrot_mode"]
        self.kernel_mode = s["kernel_mode"]
        self.color_mode = s["color"]["mode"]
        self.hue = s["color"]["hue"]
        self.val = s["color"]["value"]
        self.sat = s["color"]["saturation"]
        self.modulo = s["color"]["modulo"]
        self.m_color = s["color"]["m_color"]

class JuliabrotTile :
    def __init__(self, grid, limits = (-1,-1,-1,-1)) :
        # This will create a parent grid, settings here that depend
        #  directly on grid settings will be updated via ref alias 
        self.grid = grid.settings
        self.sizeX = None  # set_size will set both X and Y
        self.sizeY = None
        self.set_size(limits)
        # Add self to grid tile list
        grid.tile_list.append(self)
        
    def free_data(self) :
        self.data = None

    def set_size(self, limits) :
        self.free_data()
        self.limits = []
        # When bound to full-size of grid, sizes will auto-adjust
        #  due to Python reference behaviour
        if limits[0] == -1 and limits[1] == -1 and limits[2] == -1 and limits[3] == -1 :
            self.limits.append(0)
            self.limits.append(0)
            self.limits.append(self.grid.sizeX - 1)
            self.limits.append(self.grid.sizeY - 1)
            self.sizeX = self.grid.sizeX
            self.sizeY = self.grid.sizeY
        else :
            self.limits.append(limits[0])
            self.limits.append(limits[1])
            self.limits.append(limits[2])
            self.limits.append(limits[3])
            self.sizeX = limits[2] - limits[0] + 1
            self.sizeY = limits[3] - limits[1] + 1
            assert limits[0] >= 0 and limits[1] >= 0 and limits[2] >= 0 and limits[3] >= 0
            assert limits[0] < self.grid.sizeX and limits[1] < self.grid.sizeY and limits[2] < self.grid.sizeX and limits[3] < self.grid.sizeY
            assert self.sizeX > 0 and self.sizeY > 0

    def sub_tile(self, limits) :
        assert len(limits) == 4
        if not (limits[0] >= 0 and limits[1] >=0 and limits[2] >= 0 and limits[3] >= 0) :
            print('Warn: out bounds < 0, will correct')
        if not (limits[0] < self.grid.sizeX and limits[1] < self.grid.sizeY and limits[2] < self.grid.sizeX and limits[3] < self.grid.sizeY) :
            print('Warn: off the grid, will correct')
        # Keep tiles within grid
        for i in range(len(limits)) :
            if limits[i] < 0 :
                limits[i] = 0

        if limits[0] >= self.grid.sizeX :
            limits[0] = self.grid.sizeX - 1
        if limits[2] >= self.grid.sizeX :
            limits[2] = self.grid.sizeX - 1

        if limits[1] >= self.grid.sizeY :
            limits[1] = self.grid.sizeY - 1
        if limits[3] >= self.grid.sizeY :
            limits[3] = self.grid.sizeY - 1

        for i in range(len(limits)) :
            self.limits[i] = int(limits[i])
        
        self.sizeX = int(limits[2] - limits[0] + 1)
        self.sizeY = int(limits[3] - limits[1] + 1)

        # Sanity checks
        assert self.sizeX > 0, 'Invalid tile size X'
        assert self.sizeY > 0, 'Invalid tile size Y'

    def scale(self, X, Y) :
        assert X > 0 and Y > 0, 'Invalid grid size!'
        # Discard tile data
        self.free_data()
        rx = X / self.sizeX
        self.sizeX = int(round(self.sizeX * rx))
        if self.sizeX > self.grid.sizeX :
            print("Warn: tile scale larger than grid!")
            self.sizeX = self.grid.sizeX
        self.limits[2] = int(round((self.limits[2] + 1) * rx - 1))
        if self.limits[2] > (self.grid.sizeX - 1) :
            self.limits[2] = self.grid.sizeX - 1
            print("Warn: edge lr X of tile off grid!")
        ry = Y / self.sizeY
        self.sizeY = int(round(self.sizeY * ry))
        if self.sizeY > self.grid.sizeY :
            print("Warn: tile scale larger than grid!")
            self.sizeY = self.grid.sizeY
        self.limits[3] = int(round((self.limits[3] + 1) * ry - 1))
        if self.limits[3] > (self.grid.sizeY - 1) :
            self.limits[3] = self.grid.sizeY - 1
            print("Warn: edge ul Y of tile off grid!")
        assert self.sizeX > 0 and self.sizeY > 0, 'Cannot shrink tiles!'

# Depends on pynq, must only be used locally on a PYNQ board/system
class Juliabrot :
    
    def __init__(self, deepMode) :
    #  64 - 6x kernels @ 64bits, 95 - 4x kernels @ 95 bits, 160 - 1x kernels @ 160bits (@ 300MHz)
    #  64 is the fastest, 160 the highest precision
    # PYNQ Z1-Z2 boards have 1 overlay for 3x kernels @ 64 bits @ 125MHz
        if os.environ['BOARD'] == 'Ultra96' :
            if deepMode == 64 :
                overlay_name = './overlays/juliabrot96b.bit'
            elif deepMode == 95 :
                overlay_name = './overlays/juliabrot96b_mid.bit'
            elif deepMode == 160 :
                overlay_name = './overlays/juliabrot96b_deep.bit'
            else :
                overlay_name = './overlays/juliabrot96b_mid.bit'
        elif os.environ['BOARD'] == 'ZUBoard_1CG' :
            overlay_name = './overlays/juliabrotzu1.bit'
        else :
            # Should work for Z1 and Z2 (doesn't use any external I/O)
            overlay_name = './overlays/juliabrotz1.bit'
        overlay = Overlay(overlay_name)
        self._X = []
        self._Y = []
        self._tile = []
        self._jb = overlay.juliabrot
        self._config_dma = overlay.config_dma
        self._iter_dma = overlay.iter_dma
        self._nPkts = []
        self._pktSize = []
        self._lastPktSize = []
        self._n_configs = 0
        self._colorize = overlay.juliabrot_colorize
        # Turn on iter stream output and set modes, this will go away in the future (if I have the time),
        #  these settings will then come from the streaming config instead 1 per requested grid
        self._colorize.write(self._colorize.register_map.inStreamEnables.address, 0x1)
        self._colorize.write(self._colorize.register_map.inMaxIter.address, 1000)
        self._colorize.write(self._colorize.register_map.inMode.address, 0x0)
        
    def _config(self, in_tile, pktSize=-1) :
        '''
        Setup PL to generate Mandelbrot or Julia set.  For each call to config 1 set will be generated.
        Configs will queue up to the size of the input fifo (about 1K words) until fifo full then this
        method will block until there is room for another config
        '''
        assert in_tile.sizeX > 0 and in_tile.sizeY > 0
        # Going to get new data, free up memory now since it will be stale anyways
        in_tile.data = None
        cfg, n_pkts, pkt_size, last_pkt_size = self._create_cfg_words(in_tile, pktSize)
        #print("npkts: " + str(n_pkts) + " pkt size: " + str(pkt_size) + " last pkt: " + str(last_pkt_size))
        self._config_dma.resize_bufs(shape=(len(cfg),), which='tx', dtype=np.uint32)
        self._iter_dma.resize_bufs(shape=(pkt_size,), which='rx', dtype=np.uint32)
        self._config_dma.txbuf[:] = cfg
        self._config_dma.send_dma()  # This starts the PL to generate the fractal data
        self._n_configs += 1
        # Create a queue of settings for fetch to use
        self._X.append(in_tile.sizeX)
        self._Y.append(in_tile.sizeY)
        self._pktSize.append(pkt_size)
        self._lastPktSize.append(last_pkt_size)
        self._nPkts.append(n_pkts)
        self._tile.append(in_tile)
        
    def _fetch_iter(self, progress_report = False) :
        '''
        Retrieves the data generated from a configuration request.  This method will block until the entire
        set is complete.  A numpy array size from the xSetMax,ySetMax config settings will be created.
        If you would like to see a text output progress report, set progress_report True
        '''
        assert self._n_configs > 0    # IF fires, the PL has not been configured
        data = JuliabrotData()
        # Acquire the tile and update its attributes
        tile = self._tile.pop()
        if tile.data != None :
            print("Info: tile already had data: discarding old!")
        tile.data = data
        xMax = int(self._X.pop())
        yMax = int(self._Y.pop())
        pkt_size = self._pktSize.pop()
        last_pkt_size = self._lastPktSize.pop()
        n_pkts = self._nPkts.pop()
        data.iterations = np.empty((xMax*yMax,), dtype=np.uint32)
        for i in range(n_pkts) :
            #print("pkt" + str(i))
            #print(self._read_ncol())
            #print(self._read_nrow())
            self._iter_dma.rcv_dma()
            data.iterations[i*pkt_size:i*pkt_size+pkt_size] = self._iter_dma.rxbuf
            if progress_report == True :
                self._update_progress(i / n_pkts)
        if last_pkt_size > 0 :
            #print("last small pkt")
            self._iter_dma.rcv_dma()
            data.iterations[n_pkts*pkt_size:n_pkts*pkt_size+last_pkt_size] = self._iter_dma.rxbuf[0:last_pkt_size]
        if progress_report == True :
            self._update_progress(1)
        data.iterations = np.reshape(data.iterations, (yMax, xMax))
        self._n_configs -= 1
        return tile
    
    def compute(self, in_tile, in_progress_report=False) :
        NK = self._read_N()
        pad = NK - (in_tile.sizeX % NK)
        if pad != NK :
            # if tile size will exceed grid size, warn and make grid larger
            if (in_tile.sizeX + pad) > in_tile.grid.sizeX :
                #print("Warn: grid sizeX adjusted to tile sizeX + " + str(pad) + " !")
                in_tile.grid.sizeX = in_tile.sizeX + pad
            if (in_tile.limits[2] + pad + 1) > in_tile.grid.sizeX :
                #print("Warn: grid sizeX adjusted to tile right limit + " + str(pad) + " !")
                in_tile.grid.sizeX = in_tile.limits[2] + pad + 1 # limits are 0-indexed based coordinates (so +1)
            #print("Info: hardware only supports x" + str(NK) + " multiples for X width, increasing tile size!")
            in_tile.set_size( (in_tile.limits[0], in_tile.limits[1], in_tile.limits[2]+pad, in_tile.limits[3]) )
        #print("tile xul: " + str(in_tile.limits[0]))
        #print("tile yul: " + str(in_tile.limits[1]))
        #print("tile xlr: " + str(in_tile.limits[2]))
        #print("tile xlr: " + str(in_tile.limits[3]))
        self._config(in_tile)
        tile = self._fetch_iter(in_progress_report)
        return tile

    def still_computing(self) :
        return self._read_nrow() > 0 and self._read_ncol() > 0
    
    def print_progress(self) :
        print(self._read_ncol())
        print(self._read_nrow())
    
    def _read_xMax(self) :
        return self._jb.read(self._jb.register_map.xMaxOut.address)
    
    def _read_yMax(self) :
        return self._jb.read(self._jb.register_map.yMaxOut.address)
    
    def _read_nrow(self) :
        return self._jb.read(self._jb.register_map.nRowOut.address)
    
    def _read_ncol(self) :
        return self._jb.read(self._jb.register_map.nColOut.address)
    
    def _read_N(self) :
        return self._jb.read(self._jb.register_map.nkOut.address)
    
    def _longdouble_to_int32_quad(self, x) :
        b = np.longdouble(x).tobytes()
        w1 = int.from_bytes(b[0:4], "little")
        w2 = int.from_bytes(b[4:8], "little")
        w3 = int.from_bytes(b[8:12], "little")
        w4 = int.from_bytes(b[12:16], "little")
        return w1, w2, w3, w4
    
    def _to_fixed256(self, x) :
        i = int(x)
        f = x - i
        if i > 3 :
            i = 3
        elif i < -3 :
            i = -3
        x = i + f
        # Just truncate and convert to a Q 3.253
        fxp = int(np.longdouble(x) * (2.0 ** 253))
        #fxp = Fxp(x, True, 256, 256-3)
        return fxp
    
    def _fixed256_to_int32_oct(self, x) :
        h = int(x).to_bytes(32, byteorder='big', signed=True).hex()
        w8 = int(h[0 :  8], base=16)
        w7 = int(h[8 : 16], base=16)
        w6 = int(h[16: 24], base=16)
        w5 = int(h[24: 32], base=16)
        w4 = int(h[32: 40], base=16)
        w3 = int(h[40: 48], base=16)
        w2 = int(h[48: 56], base=16)
        w1 = int(h[56: 64], base=16)
        return w1, w2, w3, w4, w5, w6, w7, w8
    
    def _double_to_int_pair(self, x) :
        b = struct.pack('<%sd' % 1, x)
        l = int.from_bytes(b[0:4], "little")
        u = int.from_bytes(b[4:8], "little")
        return l, u
    
    def _update_progress(self, progress) :
        # Thank you Bartosz
        bar_length = 20
        if isinstance(progress, int) :
            progress = float(progress)
        if not isinstance(progress, float) :
            progress = 0
        if progress < 0 :
            progress = 0
        if progress >= 1 :
            progress = 1
        block = int(round(bar_length * progress))
        clear_output(wait = True)
        text = "Progress: [{0}] {1:.1f}%".format( "#" * block + "-" * (bar_length - block), progress * 100)
        print(text)

    def _create_cfg_words(self, in_tile, pktSize=-1) :
        """
        Returns a 32-bit unsigned array of config words.

        The 32-bit config words look like the following:

            [0]     mandelbrotMode - int    (1 - 32-bit word) 0x1, Mandelbrot, 0x0, Julia
            [1]     xSetMax        - int    (1 - 32-bit word)
            [2]     ySetMax        - int    (1 - 32-bit word)
            [ 3 - 10]  ulXIn       - ap_fixed<256, 3> (8 - 32-bit words)
            [11 - 18]  ulYIn       - ap_fixed<256, 3> (8 - 32-bit words)
            [19 - 26]  h_stepIn    - ap_fixed<256, 3> (8 - 32-bit words)
            [27 - 34]  v_stepIn    - ap_fixed<256, 3> (8 - 32-bit words)
            [35 - 42]  cXIn        - ap_fixed<256, 3> (8 - 32-bit words)
            [43 - 50]  cYIn        - ap_fixed<256, 3> (8 - 32-bit words)
            [51]  maxIterIn        - int    (1 - 32-bit word)
            [52]  pktSize          - int    (1 - 32-bit word)

        Multi-int values must be packed little endian
        """
        assert in_tile.sizeX <= self._read_xMax()
        assert in_tile.sizeY <= self._read_yMax()
        cfg = [0] * 53
        if (in_tile.grid.mandelbrot_mode == True) :
            cfg[0] = 0x1
        cfg[1] = int(in_tile.sizeX)
        cfg[2] = int(in_tile.sizeY)
        h_step = (in_tile.grid.lrX - in_tile.grid.ulX) * (1 / in_tile.grid.sizeX)
        w1,w2,w3,w4,w5,w6,w7,w8 = self._fixed256_to_int32_oct(self._to_fixed256(in_tile.grid.ulX + h_step * in_tile.limits[0]))
        cfg[3] = w1
        cfg[4] = w2
        cfg[5] = w3
        cfg[6] = w4
        cfg[7] = w5
        cfg[8] = w6
        cfg[9] = w7
        cfg[10] = w8
        #l,u = self._double_to_int_pair(in_tile.grid.ulX + h_step * in_tile.limits[0])
        #cfg[3] = l
        #cfg[4] = u
        w1,w2,w3,w4,w5,w6,w7,w8 = self._fixed256_to_int32_oct(self._to_fixed256(in_tile.grid.ulY + h_step * in_tile.limits[1]))
        cfg[11] = w1
        cfg[12] = w2
        cfg[13] = w3
        cfg[14] = w4
        cfg[15] = w5
        cfg[16] = w6
        cfg[17] = w7
        cfg[18] = w8
        #l,u = self._double_to_int_pair(in_tile.grid.ulY + h_step * in_tile.limits[1])
        #cfg[5] = l
        #cfg[6] = u
        w1,w2,w3,w4,w5,w6,w7,w8 = self._fixed256_to_int32_oct(self._to_fixed256(h_step))
        cfg[19] = w1
        cfg[20] = w2
        cfg[21] = w3
        cfg[22] = w4
        cfg[23] = w5
        cfg[24] = w6
        cfg[25] = w7
        cfg[26] = w8
#        l,u = self._double_to_int_pair(h_step)
#        cfg[7] = l
#        cfg[8] = u
        w1,w2,w3,w4,w5,w6,w7,w8 = self._fixed256_to_int32_oct(self._to_fixed256(h_step))
        cfg[27] = w1
        cfg[28] = w2
        cfg[29] = w3
        cfg[30] = w4
        cfg[31] = w5
        cfg[32] = w6
        cfg[33] = w7
        cfg[34] = w8
#        l,u = self._double_to_int_pair(h_step)  # Square pixel grid so just re-use h for v_step
#        cfg[9] = l
#        cfg[10] = u
        w1,w2,w3,w4,w5,w6,w7,w8 = self._fixed256_to_int32_oct(self._to_fixed256(in_tile.grid.cX))
        cfg[35] = w1
        cfg[36] = w2
        cfg[37] = w3
        cfg[38] = w4
        cfg[39] = w5
        cfg[40] = w6
        cfg[41] = w7
        cfg[42] = w8
#        l,u = self._double_to_int_pair(in_tile.grid.cX)
#        cfg[11] = l
#        cfg[12] = u
        w1,w2,w3,w4,w5,w6,w7,w8 = self._fixed256_to_int32_oct(self._to_fixed256(in_tile.grid.cY))
        cfg[43] = w1
        cfg[44] = w2
        cfg[45] = w3
        cfg[46] = w4
        cfg[47] = w5
        cfg[48] = w6
        cfg[49] = w7
        cfg[50] = w8
#        l,u = self._double_to_int_pair(in_tile.grid.cY)
#        cfg[13] = l
#        cfg[14] = u      
        cfg[51] = int(in_tile.grid.max_iterations)
        totalPix = int(in_tile.sizeX*in_tile.sizeY)
        if pktSize == -1 :
            if totalPix < 64*1024 :
                pktSize = int(totalPix)
            else :
                pktSize = int(24 * 1024)
        else :
            if totalPix < pktSize :
                pktSize = int(totalPix)
        nPkts = int(float(totalPix) / pktSize)
        lastPktSize = int(totalPix - (nPkts * pktSize))
        cfg[52] = pktSize
        return cfg, nPkts, pktSize, lastPktSize
