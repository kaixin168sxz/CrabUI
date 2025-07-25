'''
oled driver
last edited: 2025.7.16
'''

import framebuf
from ..config import *
from micropython import const

class SSD1306():
    def __init__(self,external_vcc):
        self.width = display_w
        self.height = display_h
        self.external_vcc = external_vcc
        self.pages = 8
        self.init_display()
 
    def init_display(self):
        for cmd in (
            0xae,        # 熄屏
            0x20, 0x00,  # 水平寻址
            0x40,        # 显示起始行地址
            0xa1,        # 正常列扫描
            0xa8, 63,    # 复用率
            0xc8,        # 正常行扫描
            0xd3, 0x00,  # 设置COM偏移量，即屏幕像上偏移的行数
            0xda, 0x12,  # 使用备选引脚配置，并禁用左右反置
            0xd5, 0x80,  # 设置分频因子与振荡频率
            0xd9, 0x22 if self.external_vcc else 0xf1,
            0xdb, 0x30,  # 设置vcomh电压为0.83*Vcc
            0x81, 0xff,  # 亮度最大
            0xa4,        # 使用GDDRAM中的数据显示
            0xa6,        # 设置GDDRAM中的0对应于像素点的暗
            # 关闭电荷泵
            0x8d, 0x10 if self.external_vcc else 0x14,
            0x2e,        # 禁止滚动
            0xaf):       # 开屏
            self.write_cmd(cmd)
        self.fill(0)
        self.show()

    #设置水平滚动，参数：滚动区域（滚动起始页，滚动结束页），滚动方向（默认向左，填0向右），滚动速度（0-7）  
    def h_scroll(self,start=0,end=7,d=1,speed=0): 
        self.write_cmd(0x2e)     # 关闭滚动
        self.write_cmd(0x26+d) # 向左
        self.write_cmd(0x00)
        self.write_cmd(start) # 起始页
        self.write_cmd(speed) # 滚动帧率
        self.write_cmd(end) # 结束页
        self.write_cmd(0x00)
        self.write_cmd(0xff)
        self.write_cmd(0x2f) # 开启滚动
        
    #默认开启竖直向上滚动与水平向右滚动
    def scroll(self,vScrollOn=0,vStart=0,vEnd=63,vSpeed=1,hScrollOn=1,direction=0,hSpeed=0,hScrollStartPage=0,hScrollEndPage=7,
               hScrollStartColumn=0,hScrollEndColumn=127):
        if vScrollOn:
            self.write_cmd(0x2e)# 关闭滚动
            self.write_cmd(0xa3)#设置竖直滚动命令
            self.write_cmd(vStart)#竖直滚动开始行
            self.write_cmd(vEnd)#竖直滚动结束行
        
        self.write_cmd(0x29+direction)#水平滚动方向向右
        self.write_cmd(hScrollOn) # 0,关闭水平滚动，1开启
        self.write_cmd(hScrollStartPage)# 水平滚动起始页
        self.write_cmd(hSpeed)#设置滚动速度0-7
        self.write_cmd(hScrollEndPage)# 水平滚动结束页
        self.write_cmd(vSpeed) # 每一帧的垂直偏移量
        self.write_cmd(hScrollStartColumn)#水平滚动区域的起始列
        self.write_cmd(hScrollEndColumn)#水平滚动区域的结束列
        self.write_cmd(0x2f)# 开启滚动

    def power(self, status: bool):
        self.write_cmd(0xaf if status else 0xae | 0x00)#熄屏

    #亮度，0x00-0xff
    def contrast(self, contrast):
        self.write_cmd(0x81)
        self.write_cmd(contrast)

    #正反相显示，输入1则反相，默认正相
    def invert(self, invert=0):
        self.write_cmd(0xa6 | invert)

    # 显示
    @micropython.native
    def show(self):
        cmd = self.write_cmd
        cmd(0x21) # 告诉GDDRAM列数
        cmd(0) # 列数从0-127
        cmd(127)
        cmd(0x22) # 告诉GDDRAM行数
        cmd(0) # 页数从0-7
        cmd(7)
        self.write_framebuf() # 写入1bit地址和1024bit数据

    # 水平翻转,0翻转，1正常（默认）
    def hv(self,b=1):
        self.write_cmd(0xc0 | b<<3)

    #竖直翻转,0翻转，1正常（默认）
    def vv(self,b=1):
        self.write_cmd(0xa0|b)

    #刷新缓冲区
    def fill(self, c):
        self.framebuf.fill(c)

    #画点，默认点亮，置0则暗
    def pixel(self, x, y, c=1):
        self.framebuf.pixel(x, y, c)

    #写字符
    def text(self, s, x, y, c=1):
        self.framebuf.text(s, x, y, c)

    #画水平直线
    def hline(self,x,y,w,c=1):
        self.framebuf.hline(x,y,w,c)

    #画竖直直线
    def vline(self,x,y,h,c=1):
        self.framebuf.vline(x,y,h,c)

    #画任意直线
    def line(self,x1,y1,x2,y2,c=1):
        self.framebuf.line(x1,y1,x2,y2,c)

    #画矩形，参数：起始左上角坐标，长宽，颜色默认为亮，是否填充
    def rect(self,x,y,w,h,c=1,f=False):
        self.framebuf.rect(x,y,w,h,c,f)

    #画椭圆，参数：起始圆心坐标，x半径，y半径，颜色默认为亮，是否填充，显示象限（0-15的数字）
    def ellipse(self,x,y,xr,yr,c=1,f=False,m=15):
        self.framebuf.ellipse(x,y,xr,yr,c,f,m)

    #画立方体，左上前点的坐标，边长
    def cube(self,x,y,l):
        self.rect(x,y,l,l)
        self.rect(x+int(0.5*l),int(y-0.5*l),l,l)
        self.line(x,y,int(x+0.5*l),int(y-0.5*l))
        self.line(x+l-1,y,int(x+1.5*l-1),int(y-0.5*l))
        self.line(x-1,y+l,int(x+0.5*l),int(y+0.5*l-1))
        self.line(x+l-1,y+l-1,int(x+1.5*l-1),int(y+0.5*l-1))
    
    @micropython.native
    def list_selector(self, x, y, w, h, c=1, f=0):
        x, y, w, h = int(x), int(y), int(w), int(h)
        framebuf= self.framebuf
        line = framebuf.line
        rect = framebuf.rect
        pixel = framebuf.pixel
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
        
        line = self.framebuf.line
        
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
    
    @micropython.native
    def blit(self, fbuf, x, y, key=-1, palette=None):
        self.framebuf.blit(fbuf, int(x), int(y), key, palette)


class DisplayI2C(SSD1306):
    def __init__(self,i2c, addr=0x3c, external_vcc=False):
        self.i2c = i2c
        self.addr = addr
        self.temp = bytearray(2)
        # buffer需要8 * 128的显示字节加1字节命令
        self.buffer = bytearray(8 * display_w + 1)
        self.buffer[0] = 0x40  # Co=0, D/C=1
        self.framebuf = framebuf.FrameBuffer1(memoryview(self.buffer)[1:], 128, 64)
        super().__init__(external_vcc)
    
    @micropython.native
    def write_cmd(self, cmd: int):
        self.temp[0] = 0x80 # Co=1, D/C#=0
        self.temp[1] = cmd
        self.i2c.writeto(self.addr, self.temp)

    def write_framebuf(self):
        self.i2c.writeto(self.addr, self.buffer)

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
        self.buffer = bytearray(8 * display_w + 1)
        self.buffer[0] = 0x40  # Co=0, D/C=1
        self.framebuf = framebuf.FrameBuffer1(memoryview(self.buffer)[1:], 128, 64)
        super().__init__(external_vcc)

    def write_cmd(self, cmd):
        self.spi.init(baudrate=spi_freq, polarity=0, phase=0)
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, buf):
        self.spi.init(baudrate=self.rate, polarity=0, phase=0)
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(buf)
        self.cs(1)
    
    def write_framebuf(self):
        self.spi.writeto(self.buffer)
