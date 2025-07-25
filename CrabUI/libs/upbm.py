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
        self.display = display
    
    def init(self):
        global image_list
        filepath = self.filepath
        if filepath in image_list: return
        # pbm file
        with open(filepath, 'rb') as f:
            f.readline() # 忽略 pbm 文件首行内容
            # 从文件第二行获取图片长宽
            size = f.readline().replace(b'\n', b'').split(b' ')
            w = int(size[0])
            h = int(size[1])
            self.w = w
            self.h = h
            if w != icon_size or h != icon_size:
                print(f'Illegal image size: {w}x{h}')
            # 文件其余内容为图像数据
            buffer = bytearray(memoryview(f.read()))
            image_list[filepath] = framebuf.FrameBuffer(buffer, self.w, self.h, framebuf.MONO_HLSB)

    
    @micropython.viper
    def image(self, x, y):
        self.display.blit(image_list[self.filepath], int(x), int(y))
