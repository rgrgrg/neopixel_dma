# neopixel_dma
Hardware offloaded RP2 NeoPixel library

- Mostly compatible with MicroPython neopixel library
- Asynchronous transfers using DMA and PIO
- RP2 devices (RP2040 and RP2350)

## Differences

  Additional parameters:
  | Name | Required? | Description | Default
  -------|-----------|-------------|-------
  |sm=&lt;number&gt;  | Yes | Index of PIO State Machine to use | N/A
  |order=(tuple)| No  | Subpixel order (same as Neopixel.ORDER) |(1, 0, 2, 3) #GRBW
  |idle = True\|False | No | use machine.idle() when waiting for end of transfer |True

  Additional methods:
  - busy() - check if DMA is transferring data

  Not implemented:
  - bpp values other than 3 and 4
  - timing values other than 0 and 1
  - Neopixel.buf


