"""
draw more shapes

last edited: 2025.8.3
"""

from ..config import icon_selector_length, icon_selector_gap

def list_selector(fbuf, x, y, w, h, c=1, f=0):
    x, y, w, h = int(x), int(y), int(w), int(h)
    line = fbuf.line
    if f:
        line(x+1, y, x+w-2, y, c)
        fbuf.rect(x, y+1, w, h-2, c, True)
        line(x+1, y+h-1, x+w-2, y+h-1, c)
    else:
        line(x+1, y, x+w-2, y, c)
        line(x, y+1, x, y+h-1, c)
        line(x+w-1, y+1, x+w-1, y+h-1, c)
        line(x+1, y+h, x+w-2, y+h, c)

def icon_selector(fbuf, x, y, w, h, c=1, f=0):
    x, y, w, h = int(x), int(y), int(w), int(h)

    length = icon_selector_length
    gap = icon_selector_gap
    x_sub = x-gap
    y_sub = y-gap
    
    line = fbuf.line
    
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