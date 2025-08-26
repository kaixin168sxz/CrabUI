"""
font display

last edited: 2025.8.24
MIT License
Copyright (c) 2022 AntonVanke
Copyright (c) 2025 kaixin168sxz
"""

import struct
import framebuf
from ..config import font_size, font_path, half_font_size, display_h
from micropython import const

class BMFont:
    def __init__(self, font=False, size=False):
        self.str_cache = {}
        # 载入字体文件
        self.font = open(font if font else font_path, "rb")
        # 获取字体文件信息
        self.bmf_info = self.font.read(16)
        # 位图开始字节
        # 位图数据位于文件尾，需要通过位图开始字节来确定字体数据实际位置
        self.start_bitmap = const(struct.unpack(">I", b'\x00' + self.bmf_info[4:7])[0])
        # 点阵所占字节
        # 用来定位字体数据位置
        self.bitmap_size = const(self.bmf_info[8])
        del self.bmf_info
        
        self.w = 0
        self.font_size = font_size if size is False else size
        self.half_font_size = half_font_size if size is False else size//2
    
    def blit_text(self, blit_func, string, x=0, y=0):
        x = x
        for char in string:
            blit_func(framebuf.FrameBuffer(bytearray(list(self.get_bitmap(char))),
                                           self.font_size, self.font_size, framebuf.MONO_HLSB), x, y, 0)
            x += self.half_font_size if ord(char) < 128 else self.font_size

    def text(self, blit_func, string, x, y):
        if y > display_h: return
        blit_func(self.str_cache[string], x, y, 0)
    
    def init(self, string) -> int:
        w = 0
        for char in string:
            # 英文字符半格显示
            w += self.half_font_size if ord(char) < 128 else self.font_size
        self.w = w
        buf = bytearray(max(((w + 7) // 8) * self.font_size, ((self.font_size + 7) // 8) * self.font_size))
        fbuf = framebuf.FrameBuffer(buf, max(w, self.font_size), self.font_size, framebuf.MONO_HLSB)
        self.blit_text(fbuf.blit, string)
        self.str_cache[string] = fbuf
        del fbuf, buf
        return w
    
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

bmf_cache = {}

def bitmap_font(font_file=False, size=False):
    font_file = font_file if font_file else font_path
    size = size if size else font_size
    if font_file not in bmf_cache:
        bmf_cache[font_file] = {}
    if size not in bmf_cache[font_file]:
        bmf_cache[font_file][size] = BMFont(font_file, size)
    return bmf_cache[font_file][size]
