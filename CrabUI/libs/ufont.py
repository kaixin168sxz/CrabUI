'''
font display
last edited: 2025.7.22

MIT License
Copyright (c) 2022 AntonVanke
Copyright (c) 2025 kaixin168sxz
'''

__version__ = 3

import time
import struct
import framebuf
from ..config import *

font_list = {}

class BMFont:
    def __init__(self, display, font_file):
        # 载入字体文件
        self.font = open(font_file, "rb")
        # 获取字体文件信息
        self.bmf_info = self.font.read(16)
        # 位图开始字节
        # 位图数据位于文件尾，需要通过位图开始字节来确定字体数据实际位置
        self.start_bitmap = const(struct.unpack(">I", b'\x00' + self.bmf_info[4:7])[0])
        # 点阵所占字节
        # 用来定位字体数据位置
        self.bitmap_size = const(self.bmf_info[8])
        
        self.w = 0
        self.string = ''
        self.display = display
        self.blit = display.blit

    @micropython.viper
    def text(self, x: int, y: int):
        if y > int(display_h): return
        dis_w = int(display_w)
        for char in self.string:
            if x > dis_w: return 
            self.blit(font_list[char], x, y, 0)
            x += int(half_font_size) if int(ord(char)) < 128 else int(font_size)
    
    @micropython.viper
    def init(self, string) -> int:
        global font_list
        fs = int(font_size)
        self.string = string
        w = 0
        for char in string:
            if char not in font_list:
                font_list[char] = framebuf.FrameBuffer(bytearray(list(self.get_bitmap(char))), fs, fs, framebuf.MONO_HLSB)
            # 英文字符半格显示
            w += int(half_font_size) if int(ord(char)) < 128 else fs
        self.w = w
        return w
    
    @micropython.native
    def _get_index(self, word: str) -> int:
        """
        获取索引
        Args:
            word: 字符
        """
        word_code = ord(word)
        start = 0x10
        end = self.start_bitmap

        while start <= end:
            mid = ((start + end) // 4) * 2
            self.font.seek(mid, 0)
            target_code = struct.unpack(">H", self.font.read(2))[0]
            if word_code == target_code:
                return (mid - 16) >> 1
            elif word_code < target_code:
                end = mid - 2
            else:
                start = mid + 2
        return -1

    @micropython.native
    def get_bitmap(self, word: str) -> bytes:
        """获取点阵图

        Args:
            word: 字符

        Returns:
            bytes 字符点阵
        """
        index = self._get_index(word)
        if index == -1:
            return b'\xff\xff\xff\xff\xff\xff\xff\xff\xf0\x0f\xcf\xf3\xcf\xf3\xff\xf3\xff\xcf\xff?\xff?\xff\xff\xff' \
                   b'?\xff?\xff\xff\xff\xff'

        self.font.seek(self.start_bitmap + index * self.bitmap_size, 0)
        return self.font.read(self.bitmap_size)
