"""
draw icons

last edited: 2025.8.24
"""

import framebuf
from ..config import icon_size

class PBMImage:
    """
    PBM图像类，用于显示PBM格式的图像
    """
    def __init__(self):
        """初始化PBM图像处理器"""
        self.img_cache = {}
        self.w = icon_size
        self.h = icon_size
        self.image = lambda blit_func, filepath, x, y: blit_func(self.img_cache[filepath], x, y)

    def init(self, filepath):
        """
        初始化并缓存PBM图像

        Args:
            filepath: PBM文件路径
        """
        if filepath in self.img_cache.keys(): return
        # pbm file
        with open(filepath, 'rb') as f:
            f.readline() # 忽略 pbm 文件首行内容
            # 从文件第二行获取图片长宽
            size = f.readline().replace(b'\n', b'').split(b' ')
            self.w, self.h = int(size[0]), int(size[1])
            # 文件其余内容为图像数据
            self.img_cache[filepath] = framebuf.FrameBuffer(bytearray(f.read()), self.w, self.h, framebuf.MONO_HLSB)
            
pbm_image = PBMImage()