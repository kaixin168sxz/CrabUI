"""
main file
last edited: 2025.8.27
"""

from .config import *
from .libs import ufont, upbm, drawer, bufxor
import utime
from machine import I2C, Pin, Timer, SPI, SoftI2C, SoftSPI
import framebuf
from micropython import const
from gc import collect

# 判断环境, micropython无法导入pyi
try:
    from .libs.display import Display
except ImportError:
    Display = None
    collect()

def timeit(f, *_args, **_kwargs):
    myname = str(f).split(' ')[1]
    def new_func(*_args, **_kwargs):
        t = utime.ticks_us()
        result = f(*_args, **_kwargs)
        delta = utime.ticks_diff(utime.ticks_us(), t)
        print('{}  {:6.3f}ms'.format(myname, delta/1000))
        return result
    return new_func

class Pos:
    def __init__(self, x=0, y=0, w=0, h=0):
        self.x, self.y, self.w, self.h = x, y, w, h
        # 用于保存目标坐标(destination pos)
        self.dx, self.dy, self.dw, self.dh = x, y, w, h
        self.generator = None
        self.last_time = False
    
    def animation(self, pos: tuple, num_frames=None, only_xy=False, ease_func=None):
        self.generator = self._animation_generator(pos, num_frames, only_xy, ease_func)
    
    def _animation_generator(self, pos: tuple, num_frames=None, only_xy=False, ease_func=None):
        ease_func = ease_func if ease_func else default_ease
        if num_frames is None: num_frames = default_speed
        x, y, w, h = self.x, self.y, self.w, self.h
        ew, eh = 0, 0
        if not only_xy:
            ew = pos[2]
            eh = pos[3]
        dx, dy, dw, dh = pos[0]-x, pos[1]-y, ew-w, eh-h
        _num_frames_sub1 = num_frames - 1
        for i in range(num_frames):
            eased = ease_func(i / _num_frames_sub1)
            yield [int(x+dx*eased), int(y+dy*eased),
                   w if only_xy else int(w+dw*eased),
                   h if only_xy else int(h+dh*eased)]
    
    def update(self):
        # 防止动画因为帧数过高而变快
        now = utime.ticks_ms()
        if utime.ticks_diff(now, self.last_time) < base_ani_sleep: return
        self.last_time = now
        
        try:
            self.x, self.y, self.w, self.h = next(self.generator)
        except StopIteration:
            self.generator = None 
    
    def values(self):
        return self.x, self.y, self.w, self.h
    
    def __repr__(self):
        return str(self.values())

class Selector:
    def __init__(self):
        self.pos = Pos()
        self.fbuf = display
        if selector_fill:
            self.buf = bytearray(display_fb_size)
            self.fbuf = framebuf.FrameBuffer(self.buf, display_w, display_h, framebuf.MONO_VLSB)
        self.drw = drawer.list_selector
        self.selected = None
    
    # @timeit
    def update(self):
        pos = self.pos
        cam = manager.current_menu.camera
        if pos.generator:
            pos.update()
        if selector_fill:
            self.fbuf.fill(0)
        self.drw(self.fbuf, pos.x-cam.x+out_gap, pos.y-cam.y+top_gap, pos.w, pos.h, 1, selector_fill)

    # @timeit
    def select(self, child, update_cam=True):
        pos: Pos = child.pos
        menu: "ListMenu" | "IconMenu" = manager.current_menu
        menu_type = menu.type
        if menu_type == 'ListMenu':
            child_w = 0  # child pos w
            if hasattr(child, 'widget') and child.widget:
                child_w = child.widget.pos.w+widget_gap*2
            w = min(list_max_w-child_w, pos.w+list_selector_left_gap*2+1)
            # 1是选择器的宽度
            self.pos.animation((pos.dx, pos.dy, w, pos.h+list_selector_top_gap*2+1),
                               selector_speed, ease_func=selector_ease)
        elif menu_type == 'IconMenu':
            # 1是选择器的宽度
            self.pos.animation((pos.dx, pos.dy+xscrollbar_space+1, pos.w+icon_selector_gap*2,
                                pos.h+icon_selector_gap*2), selector_speed, ease_func=selector_ease)
        menu.change_selected(child)
        self.selected = child
        menu.selected_id = self.selected.id
        menu.scrollbar.update_val()
        if update_cam: menu.update_camera()
    
    def up(self):
        child_id = self.selected.id
        last_id = manager.current_menu.count_children-1
        if child_id == 0:
            if not menu_loop: return
            child_id = last_id
        else:
            child_id -= 1
        
        self.select(manager.current_menu.children[child_id])
    
    def down(self):
        child_id = self.selected.id
        last_id = manager.current_menu.count_children-1
        if child_id == last_id:
            if not menu_loop: return
            child_id = 0
        else:
            child_id += 1

        self.select(manager.current_menu.children[child_id])

class ButtonEvent:
    def __init__(self):
        self.event_dict = {}

    def add(self, btn_pin, link, callback_on_pressed=False):
        self.event_dict[btn_pin] = [Pin(btn_pin, Pin.IN, Pin.PULL_UP), False, link, callback_on_pressed]
    
    def update(self):
        for btn_data in self.event_dict.values():
            if btn_data[0].value():
                if not btn_data[1]: return
                btn_data[1] = False
                if not btn_data[3]: btn_data[2]()
            else:
                if btn_data[1]: return
                btn_data[1] = True
                if btn_data[3]: btn_data[2]()

class Manager:
    def __init__(self, driver=None, dis=None):
        global manager, display
        manager = self
        if not (driver or dis): raise ValueError('lost display and display_driver')
        if dis: display = dis
        else:
            print('using driver')
            if use_i2c:
                if hardware_i2c:
                    i2c = I2C(hardware_i2c, scl=Pin(display_scl), sda=Pin(display_sda), freq=i2c_freq)
                else:
                    i2c = SoftI2C(scl=Pin(display_scl), sda=Pin(display_sda), freq=i2c_freq)
                display = driver.DisplayI2C(i2c, display_w, display_h)
                del i2c
            elif use_spi:
                if hardware_spi:
                    spi = SPI(hardware_spi, mosi=Pin(display_mosi), miso=Pin(display_miso), sck=Pin(display_sck), baudrate=spi_freq)
                else:
                    spi = SoftSPI(mosi=Pin(display_mosi), miso=Pin(display_miso), sck=Pin(display_sck), baudrate=spi_freq)
                display = driver.DisplaySPI(spi, Pin(display_dc), Pin(display_res), Pin(display_cs), display_w, display_h)
                del spi
            collect()
        self.display = display
        self.selector = Selector()
        self.starting_up = True
        self.load_list = []  # 在启动时会遍历列表中的元素，执行元素的init方法进行加载
        self.count_fps = 0
        self.fps = 0
        self.history = []
        self.display_on = True
        self.others = []
        self.custom_page = False
        self.current_menu = None
        self.icon_menu_dashline = _BuiltinXDashLine()

        # self.btn_up_event = ButtonEvent(pin_up, lambda: self.btn_pressed(self.up))
        # self.btn_down_event = ButtonEvent(pin_down, lambda: self.btn_pressed(self.down))
        # self.btn_yes_event = ButtonEvent(pin_yes, lambda: self.btn_pressed(self.yes))
        # self.btn_back_event = ButtonEvent(pin_back, lambda: self.btn_pressed(self.back))

        self.btn_event = ButtonEvent()
        self.btn_event.add(pin_up, lambda: self.btn_pressed(self.up))
        self.btn_event.add(pin_down, lambda: self.btn_pressed(self.down))
        self.btn_event.add(pin_yes, lambda: self.btn_pressed(self.yes))
        self.btn_event.add(pin_back, lambda: self.btn_pressed(self.back))
        
        if check_fps:
            Timer(0, period=1000, callback=self.check_fps)
        
    def up(self):
        if self.custom_page:
            _func = self.current_menu.up
            if callable(_func):
                _func()
            return
        selected = self.selector.selected
        if hasattr(selected, 'widget') and hasattr(selected.widget, 'up'):
            func = selected.widget.up
            if callable(func):
                func()
                return
        self.selector.up()
        
    def down(self):
        if self.custom_page:
            _func = self.current_menu.down
            if callable(_func): _func()
            return
        selected = self.selector.selected
        if hasattr(selected, 'widget') and hasattr(selected.widget, 'down'):
            func = selected.widget.down
            if callable(func):
                func()
                return
        self.selector.down()
    
    def yes(self):
        if self.custom_page:
            _func = self.current_menu.yes
            if callable(_func):
                _func()
            return
        link = self.selector.selected.link
        if callable(link):
            link()
    
    def back(self):
        if len(self.history) <= 1:
            return
        self.history.pop(-1)
        self.page(self.history[-1], record_history=False)
    
    # @timeit
    def btn_pressed(self, func):
        if self.starting_up: return
        func()
    
    # @timeit
    def check_fps(self, _timer=None):
        self.fps = self.count_fps
        self.count_fps = 0
    
    def startup(self):
        """startup 启动加载函数"""
        dis = display
        if not show_startup_page:
            self.load()
            self.starting_up = False
            return
        text = ufont.BMFont()
        logo_w = text.init(logo_text)
        x = half_disw-logo_w//2
        y = half_dish-half_font_size
        pos = Pos(x=x, y=-10)
        pos.animation((x, y, logo_w, font_size))
        back = False
        while self.starting_up:
            if pos.generator: pos.update()
            dis.fill(0)
            text.text(display.blit, logo_text, pos.x, pos.y)
#             display.rect(0, pos.y + y, display_w, 2)
            dis.show()
            if pos.generator: continue
            # 动画播放结束
            if not back:     # logo已经显示
                self.load()  # 加载
                back = True
                pos.animation((x, -20, logo_w, font_size))    # 播放新的动画,让logo回到屏幕外
            else:
                self.starting_up = False     # logo已经回到屏幕外
        del text
        collect()
    
    # @timeit
    def load(self):
        load_list = self.load_list
        for _ in range(len(load_list)):
            load_list[0].init()
            self.load_list.pop(0)
        collect()
    
    # @timeit
    def page(self, menu: "ListMenu" | "IconMenu" | "Page", record_history=True):
        if self.starting_up:
            print('booting...')
            self.startup()
        if record_history: self.history.append(menu)
        if expand_ani:
            if self.current_menu:
                for i in self.current_menu.children:
                    i.pos.x = 0
                    i.pos.y = 0
            for i in menu.children:
                expand_ease = icon_expand_ease if menu.type == 'IconMenu' else list_expand_ease
                i.pos.animation((i.pos.dx, i.pos.dy), expand_speed, only_xy=True, ease_func=expand_ease)
        self.current_menu = menu
        if menu.type not in ('ListMenu', 'IconMenu'):
            self.custom_page = True
            return
        self.custom_page = False
        selector: Selector = self.selector
        if not menu.count_children:
            raise IndexError('a menu should have one or more items')
        selector.drw = {'ListMenu': drawer.list_selector,
                        'IconMenu': drawer.icon_selector}[menu.type]
        selector.select(menu.children[menu.selected_id], update_cam=True)
    
    # @timeit
    def update(self, *_args):
        if not self.display_on: return
        self.count_fps += 1
        self.btn_event.update()
        dis = display
        dis.fill(0)
        self.current_menu.update()
        if not self.custom_page: self.selector.update()
        dis.fill_rect(0, 0, display_w, top_gap, 0)
        dis.fill_rect(0, top_gap, out_gap, display_h, 0)
        dis.fill_rect(right_mask_x, top_gap, out_gap, display_h, 0)
        if selector_fill and not self.custom_page:
            bufxor.xor(dis.buffer, dis.buffer, self.selector.buf)
        if self.others:
            for i in self.others: i.update()
        if check_fps:
            dis.fill_rect(0, 0, 30, 8, 0)
            dis.text(str(self.fps), 0, 0)
        dis.show()

class XScrollBar:
    def __init__(self):
        self.pos = Pos()
        self.drw = display.fill_rect
    
    def update(self):
        # out_gap is x pos
        # top_gap is y pos
        pos = self.pos
        self.drw(out_gap, xscrollbar_mask_y, xscrollbar_w, xscrollbar_mask_h, 0)
        self.drw(out_gap, top_gap, pos.w, pos.h, 1)
    
    def update_val(self):
        menu = manager.current_menu
        if menu.count_children == 1:
            w = xscrollbar_w
        else:
            w = menu.selected_id/(menu.count_children-1)*xscrollbar_w

        self.pos.animation((out_gap, top_gap, round(w), xscrollbar_h), ease_func=scrollbar_ease)

class YScrollBar:
    def __init__(self):
        self.pos = Pos()
        self.drw = display.fill_rect
        self.line = display.line
    
    def update(self):
        # yscrollbar_x is x pos
        # top_gap is y pos
        pos = self.pos
        
        self.drw(yscrollbar_mask_x, top_gap, yscrollbar_mask_w, yscrollbar_h, 0)
        self.line(yscrollbar_line_x, top_gap, yscrollbar_line_x, yscrollbar_line_yh, 1)
        self.line(yscrollbar_x, yscrollbar_bottom_line_y, yscrollbar_line_xw, yscrollbar_bottom_line_y, 1)
        self.drw(yscrollbar_x, top_gap, pos.w, pos.h, 1)
    
    # @timeit
    def update_val(self):
        menu = manager.current_menu
        if menu.count_children == 1:
            h = yscrollbar_h
        else:
            h = menu.selected_id/(menu.count_children-1)*yscrollbar_h

        self.pos.animation((yscrollbar_x, top_gap, yscrollbar_w, round(h)), ease_func=scrollbar_ease)

class BaseMenu:
    def __init__(self):
        self.type = 'BaseMenu'
        cam = Pos()
        cam.w, cam.h = display_w, display_h
        self.camera = cam
        self.children = []
        self.others = []
        self.scrollbar = None
        self.count_children = 0
        self.selected_id = 0

class ListMenu(BaseMenu):
    def __init__(self):
        super().__init__()
        self.type = 'ListMenu'
        self.scrollbar = YScrollBar()
        self.others.append(self.scrollbar)
        self.camera.h = list_max_h
        self.left_space = out_gap
        self.top_space = top_gap
    
    def offset_pos(self, x, y):
        return (x-self.camera.x+list_selector_left_space+1,
                y-self.camera.y+list_selector_top_space)
    
    def update(self):
        if self.camera.generator: self.camera.update()
        for child in self.children:
            _pos = child.pos
            _y = _pos.y-self.camera.y+self.top_space
            if _pos.generator: _pos.update()
            if  _y>display_h or _y+_pos.h<0: continue
            child.update()
        for other in self.others:
            if other.pos.generator: other.pos.update()
            other.update()
    
    # @timeit
    def change_selected(self, child):
        pass
    
    # @timeit
    def update_camera(self):
        pos = manager.selector.selected.pos
        cam = self.camera
        y = pos.dy
        yh = y + pos.h + list_space
        x = cam.x
        # 1是选择器的宽度
        if y < cam.y:
            cam.animation((x, y), camera_speed, only_xy=True, ease_func=camera_ease)
        elif yh > cam.y+cam.h:
            cam.animation((x, yh-dish_gap+1), camera_speed, only_xy=True, ease_func=camera_ease)
    
    def add(self, child):
        child.parent = self
        child.id = const(self.count_children)
        pos = child.pos
        pos.dx = pos.x
        dy = 0
        for i in range(self.count_children):
            dy += list_space+self.children[i].pos.h
        pos.dy = dy
        if not expand_ani: pos.y = pos.dy
        self.children.append(child)
        self.count_children += 1

class IconMenu(BaseMenu):
    def __init__(self):
        super().__init__()
        self.type = 'IconMenu'
        self.scrollbar = XScrollBar()
        self.title_label = Label(self, '', append_list=False, offset_pos=False)
        self.title_label.pos.y = display_h
        self.others.append(self.title_label)
        self.others.append(self.scrollbar)
        self.others.append(manager.icon_menu_dashline)
        self.camera.w = icon_max_w
        self.left_space = icon_selector_left_space
        self.top_space = icon_selector_top_space

    def offset_pos(self, x, y):
        return (x-self.camera.x+icon_selector_left_space,
                y-self.camera.y+icon_selector_top_space)

    def update(self):
        if self.camera.generator: self.camera.update()
        for child in self.children:
            _pos = child.pos
            _x = _pos.x-self.camera.x+self.left_space
            if _pos.generator: _pos.update()
            if  _x>display_w or _x+_pos.w<0: continue
            child.update()
        for other in self.others:
            if other.pos.generator: other.pos.update()
            other.update()
    
    def change_selected(self, child):
        self.title_label.set_text(child.title)
        pos = self.title_label.pos
        pos.y = display_h
        pos.x = half_disw - pos.w // 2
        pos.dx = pos.x
        pos.dy = display_h - pos.h - icon_title_bottom
        pos.animation((pos.dx, pos.dy), only_xy=True, ease_func=icon_title_ease)
    
    def update_camera(self):
        pos = manager.selector.selected.pos
        cam = self.camera
        cam.animation((pos.dx-half_disw+pos.w//2, cam.y), camera_speed, only_xy=True, ease_func=camera_ease)
    
    def add(self, child):
        count_children = self.count_children
        child.parent = self
        child.id = const(count_children)
        pos = child.pos
        pos.dx = icon_item_space*count_children
        pos.dy = pos.y
        if not expand_ani: pos.x = pos.dx
        self.children.append(child)
        self.count_children += 1

class Dialog:
    def __init__(self):
        # TODO: 一个可以自定义的Dialog组件
        pass

class TextDialog:
    def __init__(self, text: str='', duration=False):
        # 此类原来应继承于Dialog
        self.type = 'TextDialog'
        self.duration = duration if duration else dialog_default_duration
        self.text = text
        self.pos = Pos()
        self.camera = Pos()  # 由Label调用，不起任何作用(但是不可删除)
        self.drw = drawer.list_selector  # 其实就是圆角矩形
        # TextDialog目前仅支持显示一个Label组件
        self.child = Label(self, text, append_list=False, offset_pos=False, load=False)
        self.closing = False
        self.opening = False
        self.opened = False
        self.open_time = False
        self.appended = False
        if self.child.pos.w > dialog_max_w:
            print('Dialog text too long')
        manager.load_list.append(self)
    
    def open(self, text):
        self.set_text(text)
        self.pop()
    
    # @timeit
    def init(self, reset_pos=True):
        self.child.init()
        cpos = self.child.pos
        pos = self.pos
        if reset_pos:
            pos.x = display_w
            pos.y = dialog_out_gap
        pos.w = min(dialog_max_w, cpos.w+dialog_in_gap_m2)
        pos.h = cpos.h+dialog_in_gap_m2
        pos.dx = max(dialog_max_x, dialog_base_x-cpos.w)
        pos.dy = dialog_out_gap
        if reset_pos:
            cpos.x = display_w
            cpos.y = dialog_out_gap+dialog_in_gap
        cpos.dx = pos.dx+dialog_in_gap
        cpos.dy = cpos.y
    
    def set_text(self, text):
        self.text = text
        self.child.set_text(text)
        self.init(False)
        self.animation()
    
    def animation(self):
        cpos = self.child.pos
        pos = self.pos
        pos.animation((pos.dx, pos.dy), dialog_speed, ease_func=dialog_ease, only_xy=True)
        cpos.animation((cpos.dx, cpos.dy), dialog_speed, ease_func=dialog_ease, only_xy=True)

    # @timeit
    def pop(self):
        self.animation()
        self.opening = True
        if not self.appended:
            manager.others.append(self)
            self.appended = True
    
    # @timeit
    def close(self, _timer=None):
        self.closing = True
        self.opened = False
        cpos = self.child.pos
        pos = self.pos
        pos.animation((display_w, dialog_out_gap), dialog_speed, ease_func=dialog_ease, only_xy=True)
        cpos.animation((display_w, dialog_out_gap+dialog_in_gap), dialog_speed, ease_func=dialog_ease, only_xy=True)
        
    # @timeit
    def update(self):
        pos = self.pos
        if self.opened and utime.ticks_diff(utime.ticks_ms(),self.open_time)>self.duration:
            self.close()
        if pos.generator: pos.update()
        elif self.closing and pos.x == display_w:
            self.appended = False
            self.closing = False
            manager.others.remove(self)
        elif self.opening:
            self.opening = False
            self.opened = True
            self.open_time = utime.ticks_ms()
        self.drw(display, pos.x-2, pos.y-2, pos.w+5, pos.h+5, 0, 1)
        if self.child.pos.generator: self.child.pos.update()
        self.child.update()
        _xw = pos.x+pos.w
        display.fill_rect(_xw-2, pos.y-2, display_w-_xw+2, pos.h+4, 0)
        self.drw(display, pos.x, pos.y, pos.w, pos.h, 1, 0)

class BaseWidget:
    def __init__(self, parent):
        self.parent = parent
        if parent: self.camera = parent.camera
        self.pos = Pos()
        self.id = 0
        self.type = 'BaseWidget'

class Label(BaseWidget):
    def __init__(self, parent, text=None, link=None, append_list: bool=True, offset_pos: bool=True,
                 always_scroll: bool=False, scroll_w: int | bool=False, try_scroll: bool=True,
                 scroll_speed: int | bool=False, load: bool=True, font: int | bool=False, size: int | bool=False):
        """
        Label标签组件
        parent(AnyWidget): 父组件
        text(str): 显示的内容
        link(callback): 单击后运行的函数
        append_list(bool): 是否自动调用父组件的add方法 (Builtin)
        offset_pos(bool): 是否根据相机等偏移量进行坐标偏移 (Builtin)
        always_scroll(bool): 是否在未被选中时进行滚动
        scroll_w(int): 触发滚动文本的宽度阈值 (Builtin)
        try_scroll(bool): 是否开启文本滚动
        scroll_speed(int): 滚动速度(每秒偏移的像素)
        load(int): 是否自动将self添加到manager的启动加载列表 (Builtin)
        """
        super().__init__(parent)
        self.type = 'LabelWidget'
        self.font = ufont.BMFont(font, size)
        self.text = text
        self.title = text
        self.link = link
        self.link_ = link
        self.pos.h = font_size if size is False else size
        self.drw = self.font.text
        self.xscroll = 0
        self.offset = offset_pos
        self.widget = None
        self.always_scroll = always_scroll
        self.try_scroll = try_scroll
        self.last_time = False
        if scroll_w is False:
            scroll_w = disw_gap_bar
        self.scroll_speed = scroll_speed
        if scroll_speed is False:
            self.scroll_speed = string_scroll_speed
        self.scroll_w = scroll_w
        self.scroll_w_ = scroll_w
        
        # 在启动时加载字体
        if load: manager.load_list.append(self)
        if append_list: parent.add(self)
    
    def add(self, widget):
        self.link = self.widget_callback
        self.widget = widget
    
    def init(self):
        # 耗时操作,会在启动时被manager调用加载
        self.pos.w = self.font.init(self.text)
    
    def widget_callback(self):
        self.widget.widget_callback()
        if callable(self.link_): self.link_()
    
    def set_text(self, text):
        self.text = text
        self.init()
        selector = manager.selector
        if selector.selected is self:
            selector.select(self)
    
    def scroll_text(self):
        _pos = self.pos
        now = utime.ticks_ms()
        if utime.ticks_diff(now, self.last_time) < base_ani_sleep: return
        self.last_time = now
        if manager.selector.selected is self or self.always_scroll or self.xscroll:
            scr_w = self.scroll_w
            _child_w = 0
            if self.widget:
                _child_w = self.widget.pos.w+widget_gap
                scr_w -= _child_w
            if _pos.w+out_gap > scr_w:
                self.xscroll += self.scroll_speed
                if manager.selector.selected is not self and abs(self.xscroll) < self.scroll_speed: self.xscroll = 0
                elif self.xscroll > _pos.w: self.xscroll = -list_max_w+_child_w

    # @timeit
    def update(self):
        pos = self.pos
        if self.try_scroll:
            self.scroll_text()
        x, y = pos.x, pos.y
        if self.offset:
            x, y = manager.current_menu.offset_pos(x, y)
        self.drw(display.blit, self.text, x-self.xscroll, y)
        if self.widget: self.widget.update()

class Icon(BaseWidget):
    def __init__(self, parent, filepath=None, title='', link=None, append_list: bool=True, offset_pos: bool=True):
        super().__init__(parent)
        self.type = 'IconWidget'
        self.pbm = upbm.PBMImg
        self.filepath = filepath
        self.link = link
        self.pos.h, self.pos.w = icon_size, icon_size
        self.drw = self.pbm.image
        self.title = title
        self.offset = offset_pos
        # 在启动时加载图片
        manager.load_list.append(self)
        if append_list: parent.add(self)
    
    def init(self):
        # 耗时操作,会在启动时被manager调用加载
        self.pbm.init(self.filepath)
    
    def set_image(self, filepath):
        self.filepath = filepath
        self.pbm.init(filepath)
    
    def update(self):
        pos = self.pos
        x, y = pos.x, pos.y
        if self.offset:
            x, y = manager.current_menu.offset_pos(x, y)
        self.drw(display.blit, self.filepath, x, y)

class CheckBox(BaseWidget):
    def __init__(self, parent, default=False, link=None, base_x=False):
        super().__init__(parent)
        self.value = default
        self.link_ = link
        self.base_x = base_x if base_x else list_max_w-list_selector_left_gap
        pos = self.pos
        pos.w = 8
        pos.h = 8
        pos.x = self.base_x-widget_gap-pos.w
        pos.y = self.parent.pos.dy+half_list_item_space-4
        self.parent.add(self)
    
    def update(self):
        pos = self.pos
        x, y = manager.current_menu.offset_pos(pos.x, pos.y)
        display.fill_rect(x-widget_gap, y-5, disw_wgap-x, list_item_space, 0)  # mask
        display.rect(x, y, pos.w, pos.h, 1)
        if self.value: display.fill_rect(x+2, y+2, pos.w-4, pos.h-4, 1)
    
    def widget_callback(self):
        self.value = not self.value
        if callable(self.link_): self.link_(self.value)

class ListSelector(BaseWidget):
    def __init__(self, parent, range_list, default_idx: int | bool=False, loop=False,
                 link=None, change_link=None, flash_speed: int | bool=False, base_x=False):
        super().__init__(parent)
        if not range_list: raise IndexError('a ListSelector Widget should has one or more items')
        self.idx = 0 if default_idx is False else default_idx
        self.max_idx = len(range_list)-1
        self.value = range_list[self.idx]
        self.range_list = range_list
        self.activate = False
        self.loop = loop
        self.link_ = link
        self.up_ = change_link
        self.down_ = change_link
        self.last_time = None
        self.flash_status = False
        self.flash_speed = flash_speed
        if flash_speed is False:
            self.flash_speed = widget_flash_speed
        self.child = Label(self, text=str(self.value), append_list=False, try_scroll=False, load=False)
        self.up, self.down = None, None
        self.base_x = base_x if base_x else list_max_w-list_selector_left_gap
        manager.load_list.append(self)
        self.parent.add(self)
    
    def update(self):
        pos = self.pos
        x, y = manager.current_menu.offset_pos(pos.x, pos.y)
        display.fill_rect(x-widget_gap, y, pos.w+widget_gap_m2, list_item_space, 0)
        now = utime.ticks_ms()
        if not self.activate: self.flash_status = True  # 未被激活时不闪烁
        elif utime.ticks_diff(now, self.last_time) > self.flash_speed:
            self.flash_status = not self.flash_status
            self.last_time = now
        
        if self.flash_status:
            self.child.update()
    
    def init(self):
        self.child.init()
        pos = self.pos
        cpos = self.child.pos
        pos.w = cpos.w
        pos.h = cpos.h
        pos.x = self.base_x-widget_gap-pos.w
        pos.y = self.parent.pos.dy
        cpos.x = pos.x
        cpos.y = pos.y
    
    def set_text(self, value):
        self.value = value
        self.child.set_text(str(value))
        self.init()
        if manager.selector.selected is self.parent:
            manager.selector.select(self.parent)
    
    def widget_callback(self):
        self.activate = not self.activate
        self.activate_widget(self.activate)
    
    def activate_widget(self, status):
        self.activate = status
        if status:
            self.up, self.down = self._up, self._down
            self.last_time = utime.ticks_ms()
        else:
            self.up, self.down = None, None
            if callable(self.link_): self.link_(self.idx)
    
    def _down(self):
        self.idx -= 1
        if self.idx < 0:
            self.idx = 0
            if self.loop: self.idx = self.max_idx
        if self.idx > self.max_idx:
            self.idx = self.max_idx
            if self.loop: self.idx = 0
        self.set_text(self.range_list[self.idx])
        if callable(self.down_): self.down_(self.idx)
    
    def _up(self):
        self.idx += 1
        if self.idx < 0:
            self.idx = 0
            if self.loop: self.idx = self.max_idx
        if self.idx > self.max_idx:
            self.idx = self.max_idx
            if self.loop: self.idx = 0
        self.set_text(self.range_list[self.idx])
        if callable(self.up_): self.up_(self.idx)

class NumberSelector(ListSelector):
    def __init__(self, parent, default_num=0, min_num=0, max_num=10, step=1, loop=False,
                 link=None, change_link=None, flash_speed=False, base_x=False):
        num_list = [i for i in range(min_num, max_num+1, step)]
        _change_link = change_link
        _link = link
        if callable(change_link): change_link = lambda v: _change_link(num_list[v])
        if callable(link): link = lambda v: _link(num_list[v])
        super().__init__(parent, num_list, num_list.index(default_num), loop, link, change_link, flash_speed, base_x)
        
class _BuiltinXDashLine:
    def __init__(self):
        self.type = 'XDashLine'
        
        self.pos = Pos()  # 所有组件必须拥有Pos
        fbuf = framebuf.FrameBuffer(bytearray(display_w), display_w, 1, framebuf.MONO_VLSB)
        self.drw = fbuf.line
        self.update = lambda: manager.display.blit(fbuf, 0, dashline_h)
        
        manager.load_list.append(self)
    
    def init(self):
        color = 0
        x = 0
        for _ in range(display_w // icon_dashline_split_length):
            to_x = x + icon_dashline_split_length
            self.drw(x, 0, to_x, 0, color)
            x = to_x
            color = not color
        del x, to_x, color
        collect()

class CustomWidget:
    # no parent widget
    def __init__(self, link=None, as_others: bool=True):
        self.type = 'CustomWidget'
        self.pos = Pos()
        self.link = link
        if as_others: manager.others.append(self)

class Page:
    def __init__(self, up=None, down=None, yes=None, page_type='CustomPage'):
        self.type = page_type
        self.children = []
        self.count_children = 0
        self.camera = Pos()
        self.up, self.down, self.yes = up, down, yes
    
    def offset_pos(self, x, y):
        return (x-self.camera.x+out_gap,
                y-self.camera.y+top_gap)
    
    def add(self, child):
        child.id = self.count_children
        self.children.append(child)
        self.count_children += 1
    
    def update(self):
        for child in self.children:
            if child.pos.generator: child.pos.update()
            child.update()

def item(parent, *args, **kws) -> "None" | "Label" | "Icon":
    if isinstance(parent, ListMenu): return Label(parent, *args, **kws)
    elif isinstance(parent, IconMenu): return Icon(parent, *args, **kws)
    else: print('[WARNING] Item: Unknown menu type.')
    return None

display: Display
manager: Manager