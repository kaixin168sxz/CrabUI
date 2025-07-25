'''
MicroPython SSD1306 OLED driver, I2C and SPI interfaces

Last edited 2025.7.20
'''

from micropython import const
import framebuf
from ..config import *

# register definitions
SET_CONTRAST = const(0x81)
SET_ENTIRE_ON = const(0xA4)
SET_NORM_INV = const(0xA6)
SET_DISP = const(0xAE)
SET_MEM_ADDR = const(0x20)
SET_COL_ADDR = const(0x21)
SET_PAGE_ADDR = const(0x22)
SET_DISP_START_LINE = const(0x40)
SET_SEG_REMAP = const(0xA0)
SET_MUX_RATIO = const(0xA8)
SET_COM_OUT_DIR = const(0xC0)
SET_DISP_OFFSET = const(0xD3)
SET_COM_PIN_CFG = const(0xDA)
SET_DISP_CLK_DIV = const(0xD5)
SET_PRECHARGE = const(0xD9)
SET_VCOM_DESEL = const(0xDB)
SET_CHARGE_PUMP = const(0x8D)

# Subclassing FrameBuffer provides support for graphics primitives
# http://docs.micropython.org/en/latest/pyboard/library/framebuf.html
class SSD1306(framebuf.FrameBuffer):
    def __init__(self, external_vcc):
        self.external_vcc = external_vcc
        self.pages = display_h // 8
        self.buffer = bytearray(self.pages * display_w)
        super().__init__(self.buffer, display_w, display_h, framebuf.MONO_VLSB, display_w)
        self.init_display()
        self.poweron()

    def init_display(self):
        for cmd in (
            SET_DISP | 0x00,  # off
            # address setting
            SET_MEM_ADDR,
            0x00,  # horizontal
            # resolution and layout
            SET_DISP_START_LINE | 0x00,
            SET_SEG_REMAP | 0x01,  # column addr 127 mapped to SEG0
            SET_MUX_RATIO,
            display_h - 1,
            SET_COM_OUT_DIR | 0x08,  # scan from COM[N] to COM0
            SET_DISP_OFFSET,
            0x00,
            SET_COM_PIN_CFG,
            0x02 if display_w > 2 * display_h else 0x12,
            # timing and driving scheme
            SET_DISP_CLK_DIV,
            0x80,
            SET_PRECHARGE,
            0x22 if self.external_vcc else 0xF1,
            SET_VCOM_DESEL,
            0x30,  # 0.83*Vcc
            # display
            SET_CONTRAST,
            0xFF,  # maximum
            SET_ENTIRE_ON,  # output follows RAM contents
            SET_NORM_INV,  # not inverted
            # charge pump
            SET_CHARGE_PUMP,
            0x10 if self.external_vcc else 0x14,
            SET_DISP | 0x01,
        ):  # on
            self.write_cmd(cmd)
        self.fill(0)
        self.show()

    def poweroff(self):
        self.write_cmd(SET_DISP | 0x00)

    def poweron(self):
        self.write_cmd(SET_DISP | 0x01)

    def contrast(self, contrast):
        self.write_cmd(SET_CONTRAST)
        self.write_cmd(contrast)

    def invert(self, invert):
        self.write_cmd(SET_NORM_INV | (invert & 1))

    def show(self):
        x0 = 0
        x1 = display_w - 1
        if display_w == 64:
            # displays with width of 64 pixels are shifted by 32
            x0 += 32
            x1 += 32
        self.write_cmd(SET_COL_ADDR)
        self.write_cmd(x0)
        self.write_cmd(x1)
        self.write_cmd(SET_PAGE_ADDR)
        self.write_cmd(0)
        self.write_cmd(self.pages - 1)
        self.write_data(self.buffer)
    
    @micropython.native
    def list_selector(self, x, y, w, h, c=1, f=0):
        x, y, w, h = int(x), int(y), int(w), int(h)
        line = self.line
        rect = self.rect
        pixel = self.pixel
        if f:
            line(x+2, y, x+w-3, y, c)
            line(x+1, y+1, x+w-2, y+1, c)
            rect(x, y+2, w, h-3, c, True)
            line(x+1, y+h-1, x+w-2, y+h-1, c)
            line(x+2, y+h, x+w-3, y+h, c)
        else:
            line(x+2, y, x+w-3, y, c)
            pixel(x+1, y+1, c)
            pixel(x+w-2, y+1, c)
            line(x, y+2, x, y+h-2, c)
            line(x+w-1, y+2, x+w-1, y+h-2, c)
            pixel(x+1, y+h-1, c)
            pixel(x+w-2, y+h-1, c)
            line(x+2, y+h, x+w-3, y+h, c)
    
    @micropython.native
    def icon_selector(self, x, y, w, h, c=1, f=0):
        x, y, w, h = int(x), int(y), int(w), int(h)

        length = icon_selector_length
        gap = icon_selector_gap
        x_sub = x-gap
        y_sub = y-gap
        
        line = self.line
        
        # left up
        line(x_sub, y_sub, x_sub+length, y_sub, c)
        line(x_sub, y_sub+1, x_sub, y_sub+length, c)
        # right up
        line(x+w-length, y_sub, x+w, y_sub, c)
        line(x+w, y_sub+1, x+w, y_sub+length, c)
        # left bottom
        line(x_sub, y+h, x_sub+length, y+h, c)
        line(x_sub, y+h-length, x_sub, y+h, c)
        # right bottom
        line(x+w-length, y+h, x+w, y+h, c)
        line(x+w, y+h-length, x+w, y+h, c)


class DisplayI2C(SSD1306):
    def __init__(self, i2c, addr=0x3C, external_vcc=False):
        self.i2c = i2c
        self.addr = addr
        self.temp = bytearray(2)
        self.write_list = [b"\x40", None]  # Co=0, D/C#=1
        super().__init__(external_vcc)

    def write_cmd(self, cmd):
        self.temp[0] = 0x80  # Co=1, D/C#=0
        self.temp[1] = cmd
        self.i2c.writeto(self.addr, self.temp)

    def write_data(self, buf):
        self.write_list[1] = buf
        self.i2c.writevto(self.addr, self.write_list)


class DisplaySPI(SSD1306):
    def __init__(self, spi, dc, res, cs, external_vcc=False):
        dc.init(dc.OUT, value=0)
        res.init(res.OUT, value=0)
        cs.init(cs.OUT, value=1)
        self.spi = spi
        self.dc = dc
        self.res = res
        self.cs = cs
        import time

        self.res(1)
        time.sleep_ms(1)
        self.res(0)
        time.sleep_ms(10)
        self.res(1)
        super().__init__(external_vcc)

    def write_cmd(self, cmd):
        self.spi.init(baudrate=spi_freq, polarity=0, phase=0)
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, buf):
        self.spi.init(baudrate=spi_freq, polarity=0, phase=0)
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(buf)
        self.cs(1)
