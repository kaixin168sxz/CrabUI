'''
icon display
last edited: 2025.7.15
'''

import framebuf
from ..config import *

image_list = {}

class PBMImage:
    def __init__(self, display, filepath):
        self.w = icon_size
        self.h = icon_size
        self.filepath = filepath
        blit = display.blit
        self.image = lambda x, y: blit(image_list[filepath], int(x), int(y))
    
    def init(self):
        global image_list
        _filepath = self.filepath
        if _filepath in image_list.keys(): return
        # pbm file
        with open(_filepath, 'rb') as f:
            f.readline() # 忽略 pbm 文件首行内容
            # 从文件第二行获取图片长宽
            size = f.readline().replace(b'\n', b'').split(b' ')
            self.w, self.h = int(size[0]), int(size[1])
            if (self.w, self.h) != (icon_size, icon_size):
                print(f'Illegal image size: {self.w}x{self.h}')
            # 文件其余内容为图像数据
            buffer = bytearray(memoryview(f.read()))
            image_list[_filepath] = framebuf.FrameBuffer(buffer, self.w, self.h, framebuf.MONO_HLSB)