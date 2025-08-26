from framebuf import FrameBuffer

class Display(FrameBuffer):
    buffer: bytearray

    def __init__(self):
        pass

    def show(self):
        """
        Display the window
        :return: None
        """

    def fill_rect(self, x, y, w, h, c):
        """
        :param x: pos x
        :param y: pos y
        :param w: width
        :param h: height
        :param c: color
        :return: None
        """