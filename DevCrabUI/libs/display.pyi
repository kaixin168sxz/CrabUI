"""
[pyi] display

last edited: 2025.8.27
"""

from framebuf import FrameBuffer

class Display(FrameBuffer):
    """
    显示屏类，继承自FrameBuffer
    """
    buffer: bytearray

    def __init__(self):
        """初始化显示屏"""

    def show(self):
        """显示缓冲区内容到屏幕"""

    def fill_rect(self, x, y, w, h, c):
        """
        填充矩形区域

        Args:
            x: 矩形左上角x坐标
            y: 矩形左上角y坐标
            w: 矩形宽度
            h: 矩形高度
            c: 填充颜色
        """