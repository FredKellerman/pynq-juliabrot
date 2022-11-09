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

from pynq.lib.dma import DMA
from pynq import allocate
import numpy as np

class CmaBufferFactory():
    def __init__(self):
        pass
        
    def make_cma_buf(self, shape, data_type):
        assert shape != [], RuntimeError
        return allocate(shape=shape, cacheable=1, dtype=data_type)
    
    def del_cma_buf(self, cma_buf):
        cma_buf.close()

"""
This class hides the details of the CMA buffers and DMA itself.
This class can be used with any compatible IP block connected to the DMA.
"""
class SimpleDmaDriver(DMA, CmaBufferFactory):
     # This line is always the same for any driver
    def __init__(self, description):
        DMA.__init__(self, description=description)
        CmaBufferFactory.__init__(self)
        self.txbuf = []
        self.rxbuf = []
        
    bindto = ['xilinx.com:ip:axi_dma:7.1']
    
    def resize_bufs(self, shape, dtype, which='both'):
        assert which == 'rx' or which == 'tx' or which == 'both', RuntimeError
        assert shape != [], RuntimeError
        if which == 'tx' or which == 'both' :
            if self.txbuf != [] :
                self.del_cma_buf(self.txbuf)
            self.txbuf = self.make_cma_buf(shape, dtype)
        if which == 'rx' or which == 'both' :
            if self.rxbuf != [] :
                self.del_cma_buf(self.rxbuf)
            self.rxbuf = self.make_cma_buf(shape, dtype)

    def send_dma(self, wait=True):
        self.send_cma_buf(self.txbuf, wait)
        
    def rcv_dma(self, wait=True):
        self.rcv_cma_buf(self.rxbuf, wait)
        
    def send_cpy(self, data, wait=True):
        """
        Copy data into DMA buffer and send it, waits for send to complete before returning
        """
        tx_buf = self.make_cma_buf(data.shape, data.dtype)
        tx_buf[0:len(tx_buf)] = data
        self.send_cma_buf(tx_buf, wait)
        self.del_cma_buf(tx_buf)

    def rcv_cpy(self, shape, dtype, wait=True):
        """
        Attempts to read up to max_num words, it waits until the transfer is complete before returning
        """
        rx_buf = self.make_cma_buf(shape, dtype)
        self.rcv_cma_buf(rx_buf, wait)
        data = np.array(rx_buf)
        self.del_cma_buf(rx_buf)
        return data
    
    def rcv_cma_buf(self, cma_only_buf, wait=True):
        """
        Attempts to read up to max_num words, it waits until the transfer is complete before returning
        """
        self.recvchannel.transfer(cma_only_buf)
        if wait == True :
            self.recvchannel.wait()

    def send_cma_buf(self, cma_only_buf, wait=True):
        """
        Copy data into DMA buffer and send it, waits for send to complete before returning
        """
        self.sendchannel.transfer(cma_only_buf)
        if wait == True :
            self.sendchannel.wait()
