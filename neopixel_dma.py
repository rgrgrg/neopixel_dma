#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#
#                                                                           #
#    RP2 NeoPixel_DMA Library v0.2                                          #
#    (c) 2026 Radosław Gancarz <radgan99@gmail.com>                         #
#                                                                           #
#    This Source Code Form is subject to the terms of the Mozilla Public    #
#    License, v. 2.0. If a copy of the MPL was not distributed with this    #
#    file, You can obtain one at http://mozilla.org/MPL/2.0/.               #
#                                                                           #
#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#@#
from machine import idle
from time import sleep_us
import array
import rp2
#PIO:   https://github.com/raspberrypi/pico-micropython-examples/blob/master/pio/pio_ws2812.py
#       more compatible 800 kHz timings:
#       https://github.com/raspberrypi/pico-examples/blob/master/pio/ws2812/ws2812.pio
#DMA:   https://docs.micropython.org/en/latest/library/rp2.DMA.html
#WS281x https://learn.adafruit.com/adafruit-neopixel-uberguide/advanced-coding
@rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW, out_shiftdir=rp2.PIO.SHIFT_LEFT,
             autopull=True,fifo_join=rp2.PIO.JOIN_TX)
def ws2812():
    T1 = 3#2
    T2 = 3#5
    T3 = 4#3
    wrap_target()
    label("bitloop")
    out(x, 1)               .side(0)    [T3 - 1]
    jmp(not_x, "do_zero")   .side(1)    [T1 - 1]
    jmp("bitloop")          .side(1)    [T2 - 1]
    label("do_zero")
    nop()                   .side(0)    [T2 - 1]
    wrap()


#additional parameters:
# sm    = PIO state machine index (required, RP2040: 0-7, RP2350: 0-11)
# order = pixel order (optional, default GRBW)
# idle  = use machine.idle() when waiting for end of transfer (optional, default True)
#
# only timing = 1 and bpp=3 was tested


class NeoPixel:
    ORDER = (1,0,2,3) #neopixel.py default
    def __init__(self, pin, n, bpp=3, timing=1,**kwargs):
        
        self._idx_sm = -1
        self._idle   = True
        self.timing  = timing
        self.bpp     = bpp
        self.pin     = pin
        self.n       = n
        self.buf     = None #Not implemented
        
        if n<1:
            raise ValueError("incorrect length")
        
        if timing not in [0, 1]:
            raise ValueError("only timing 0 and 1 supported")
        
        if bpp not in [3,4]:
            raise ValueError("only 3 and 4 bpp supported")
        
        #Pause before DMA start (no DMA, fifo empty):
        # 50 us - tReset (WS2811 datasheet)
        # 8bit * 1.25 us = 10us
        self._tflush_us = (50 + 10 * bpp) << (1 - self.timing)
        
        
        for k, v in kwargs.items():
            if k == 'idle':
                self._idle = v
            elif k == 'order':
                self.ORDER = v
            elif k == 'sm':
                self._idx_sm = v
            else:
                raise KeyError(f"unknown {key=}")
        if self._idx_sm<0:
            raise ValueError("StateMachine number (sm) is required")
        
        self.pin.init(pin.OUT,value=0)
        
        # RAW buffer
        self._raw = array.array("I", [0 for _ in range(self.n)])
        
        self._sm = rp2.StateMachine(self._idx_sm, ws2812, freq = (4_000_000 << self.timing),
                                    sideset_base = self.pin, pull_thresh = 8*self.bpp)
        self._sm.active(1)
        
        self._dma = rp2.DMA()
        #See RP2040 datasheet 2.5.3.1/RP2350 datasheet 12.6.4.1
        dreq_index = ((self._idx_sm // 4) << 3 ) | (self._idx_sm & 3)
        self._dma_ctrl=self._dma.pack_ctrl(size = 2, inc_write = False, bswap=True,
                                         treq_sel = dreq_index )
        
        
    def __len__(self):
        return self.n
        
        
    def __setitem__(self,idx,val):
        v=0
        for i in range(self.bpp):
            v |= ( (val[i] & 0xff) << (self.ORDER[i]<<3) )
        self._raw[idx] = v
        
        
    def __getitem__(self,idx):
        return tuple( ( ( self._raw[idx] >> (self.ORDER[i]<<3) )  & 0xff ) for i in range(self.bpp))
        
        
    def fill(self,val):
        v=0
        for i in range(self.bpp):
            v |= ( (val[i] & 0xff) << (self.ORDER[i]<<3) )
    
        for i in range (self.n):
            self._raw[i] = v
        
        
    def write(self):
        while self._dma.active():
            if self._idle:
                idle()
        while self._sm.tx_fifo()>0:
            if self._idle:
                idle()
        sleep_us(self._tflush_us)
        
        self._dma.config( read=self._raw, write=self._sm, count=len(self._raw),
                          ctrl=self._dma_ctrl, trigger=True)
        
        
    #Additional methods
        
    #Check if DMA is transferring data 
    def busy(self):
        return self._dma.active()
        
        
                          