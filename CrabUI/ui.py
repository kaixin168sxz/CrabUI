'''
main file
last edited: 2025.7.30
'''

from .config import *
from .libs import oled, ufont, upbm
import utime
from random import randint
from .apis import *
import framebuf
from micropython import const

manager = None
_print = print

def timeit(f, *args, **kwargs):
    myname = str(f).split(' ')[1]
    def new_func(*args, **kwargs):
        t = utime.ticks_us()
        result = f(*args, **kwargs)
        delta = utime.ticks_diff(utime.ticks_us(), t)
        print('{}  {:6.3f}ms'.format(myname, delta/1000))
        return result
    return new_func

def print(*args, **kws):
    if debug: _print(*args, **kws)

class Pos:
    def __init__(self, x=0, y=0, w=0, h=0):
        self.x, self.y, self.w, self.h = x, y, w, h
        # 用于保存目标坐标([d]estination [pos(xywh)])
        self.dx, self.dy, self.dw, self.dh = x, y, w, h
        self.pos_buffer = []
        self.last_time = False
    
    def set_pos(self, x=False, y=False, w=False, h=False, edit_pos=False, edit_dpos=True):
        x = x if x else self.x
        y = y if y else self.y
        w = w if w else self.w
        h = h if h else self.h
        if edit_pos: self.x, self.y, self.w, self.h = x, y, w, h
        # 用于保存目标坐标([d]estination [pos(xywh)])
        if edit_dpos: self.dx, self.dy, self.dw, self.dh = x, y, w, h
    
    def animation(self, pos: tuple, num_frames=None, only_xy=False, ease_func=None):
        if stop_last_ani: self.pos_buffer.clear()
        ease_func = ease_func if ease_func else default_ease
        if num_frames is None: num_frames = default_speed
        x, y, w, h = self.x, self.y, self.w, self.h
        ex = pos[0]
        ey = pos[1]
        ew, eh = 0, 0
        if not only_xy:
            ew = pos[2]
            eh = pos[3]
        dx, dy, dw, dh = ex-x, ey-y, ew-w, eh-h
        _num_frames_sub1 = num_frames - 1
        for i in range(num_frames):
            eased = ease_func(i / _num_frames_sub1)
            res = [int(x+dx*eased), int(y+dy*eased),
                   False if only_xy else int(w+dw*eased),
                   False if only_xy else int(h+dh*eased)]
            self.pos_buffer.append(res)
    
    def update(self):
        # 防止动画因为帧数过高而变快
        now = utime.ticks_ms()
        if utime.ticks_diff(now, self.last_time) < base_ani_sleep: return
        self.last_time = now
        
        new_pos = self.pos_buffer[0]
        self.x, self.y = new_pos[0], new_pos[1]
        if not (new_pos[-1] is False):  # 判断是否需要更新 w和h
            self.w, self.h = new_pos[2], new_pos[3]
            
        self.pos_buffer.pop(0)
    
    def values(self):
        return self.x, self.y, self.w, self.h
    
    def __repr__(self):
        return str(self.values())

class Selector:
    def __init__(self):
        self.pos = Pos()
        self.display = manager.display
        self.drw = None
        self.selected = None
    
    # @timeit
    def update(self):
        pos = self.pos
        cam = manager.current_menu.camera
        if pos.pos_buffer: pos.update()
        self.drw(pos.x-cam.x+out_gap, pos.y-cam.y+top_gap, pos.w, pos.h, 1)
    
    # @timeit
    def select(self, child, scroll_page=False, update_cam=True):
        pos: Pos = child.pos
        menu: Menu = manager.current_menu
        menu_type = menu.type
        if menu_type == 'ListMenu':
            cposw = 0
            if hasattr(child, 'widget') and child.widget:
                cposw = child.widget.pos.w+widget_gap
            w = min(list_max_w-cposw, pos.w+list_selector_left_gap*2)
            # 1是选择器的宽度
            self.pos.animation((pos.dx, pos.dy, w, pos.h+list_selector_top_gap*2+1),
                               selector_speed,ease_func=selector_ease)
        elif menu_type == 'IconMenu':
            # 1是选择器的宽度
            self.pos.animation((pos.dx, pos.dy+xscrollbar_space+1, pos.w+icon_selector_gap*2,
                                pos.h+icon_selector_gap*2), selector_speed,
                               ease_func=selector_ease)
        menu.change_selected(child)
        self.selected = child
        menu.selected_id = self.selected.id
        menu.scrollbar.update_val()
        if update_cam: menu.update_camera(scroll_page)
    
    def up(self):
        scroll_page = False
        child_id = self.selected.id
        menu = manager.current_menu
        last_id = manager.current_menu.count_children-1
        if child_id == 0:
            if not menu_loop: return
            children = menu.children
            display_length = display_w if menu.type == 'IconMenu' else display_h
            scroll_page = children[last_id].pos.dy - children[child_id].pos.dy >= display_length
            child_id = last_id
        else:
            child_id -= 1
        
        self.select(manager.current_menu.children[child_id], scroll_page)
    
    def down(self):
        scroll_page = False
        child_id = self.selected.id
        menu = manager.current_menu
        last_id = menu.count_children-1
        if child_id == last_id:
            if not menu_loop: return
            children = menu.children
            display_length = display_w if menu.type == 'IconMenu' else display_h
            scroll_page = children[child_id].pos.dy - children[0].pos.dy >= display_length
            child_id = 0
        else:
            child_id += 1

        self.select(manager.current_menu.children[child_id], scroll_page)

class ButtonEvent:
    def __init__(self, btn_pin, link, callback_on_pressed=False):
        self.btn = Pin(btn_pin, Pin.IN, Pin.PULL_UP)
        self.press = False
        self.link = link
        self.callback_on_pressed = callback_on_pressed
    
    def update(self):
        if self.btn.value():
            if not self.press: return
            self.press = False
            if not self.callback_on_pressed: self.link()
        else:
            if self.press: return
            self.press = True
            if self.callback_on_pressed: self.link()

class Manager:
    def __init__(self):
        global manager
        manager = self
        if use_i2c:
            # -1为软i2c,0为硬i2c
            self.display = oled.DisplayI2C(I2C(hardware_i2c-1, scl=Pin(display_scl), sda=Pin(display_sda), freq=i2c_freq))
        elif use_spi:
            if hardware_spi:
                spi = SPI(hardware_spi, mosi=Pin(display_mosi), miso=Pin(display_miso), sck=Pin(display_sck))
            else:
                spi = SoftSPI(mosi=Pin(display_mosi), miso=Pin(display_miso), sck=Pin(display_sck))
            self.display = oled.DisplaySPI(spi, dc=Pin(display_dc), res=Pin(display_res), cs=Pin(display_cs))
        self.current_menu = None
        self.selector = Selector()
        self.last_pressed = 0
        self.starting_up = True
        self.load_list = []  # 在启动时会遍历列表中的元素，执行元素的init方法进行加载
        self.count_fps = 0
        self.fps = 0
        self.history = []
        self.display_on = True
        self.others = []
        self.custom_page = False
        self.icon_menu_dashline = _BuiltinXDashLine(0, display_w, dashline_h, builtin_allow='AllowByBuiltinWidget')

        self.btn_up_event = ButtonEvent(pin_up, lambda: self.btn_pressed(self.up))
        self.btn_down_event = ButtonEvent(pin_down, lambda: self.btn_pressed(self.down))
        self.btn_yes_event = ButtonEvent(pin_yes, lambda: self.btn_pressed(self.yes))
        self.btn_back_event = ButtonEvent(pin_back, lambda: self.btn_pressed(self.back))
        
        if check_fps:
            Timer(0, period=1000, callback=self.check_fps)
        
    def up(self):
        if self.custom_page:
            _func = self.current_menu.up
            if callable(_func): _func()
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
            if callable(_func): _func()
            return
        link = self.selector.selected.link
        if callable(link): link()
    
    def back(self):
        if len(self.history) <= 1: return
        self.history.pop(-1)
        self.set_menu(self.history[-1], record_history=False)
    
    # @timeit
    def btn_pressed(self, func):
        if self.starting_up: return
        new_time = utime.ticks_ms()
        if (new_time - self.last_pressed) < btn_wait: return 
        self.last_pressed = new_time
        func()
    
    # @timeit
    def check_fps(self, n=False):
        self.fps = self.count_fps
        self.count_fps = 0
    
    def power(self, status: bool):
        if power:
            self.display.poweron()
        else:
            self.display.poweroff()
        self.display_on = status
    
    def startup(self):
        '''startup 启动加载函数'''
        dis = self.display
        if not show_startup_page:
            self.load()
            self.starting_up = False
            return
        text = ufont.BMFont(dis, font_path)
        logo_w = text.init(logo_text)
        x = half_disw-logo_w//2
        y = half_dish-half_font_size
        pos = Pos(x=x, y=-10)
        pos.animation((x, y, logo_w, font_size))
        back = False
        while self.starting_up:
            if pos.pos_buffer: pos.update()
            dis.fill(0)
            text.text(pos.x, pos.y)
#             self.display.rect(0, pos.y + y, display_w, 2)
            dis.show()
            if pos.pos_buffer: continue
            # 动画播放结束
            if not back:     # logo已经显示
                self.load()  # 加载
                back = True
                pos.animation((x, -10, logo_w, font_size))    # 播放新的动画,让logo回到屏幕外
            else:
                self.starting_up = False     # logo已经回到屏幕外
    
    @timeit
    def load(self):
        load_list = self.load_list
        for _ in range(len(load_list)):
            load_list[0].init()
            self.load_list.pop(0)
    
    # @timeit
    def set_menu(self, menu: Menu, record_history=True):
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
                i.pos.animation((i.pos.dx, i.pos.dy), expand_speed, only_xy=True, ease_func=expand_ease)
        self.current_menu = menu
        if menu.type not in ('ListMenu', 'IconMenu'):
            self.custom_page = True
            return
        self.custom_page = False
        selector = self.selector
        dis = self.display
        if not menu.count_children:
            raise IndexError('a menu should have one or more items')
        selector.drw = {'ListMenu': dis.list_selector,
                        'IconMenu': dis.icon_selector}[menu.type]
        selector.select(menu.children[menu.selected_id], update_cam=True)
    
    # @timeit
    def update(self, *args):
        if not self.display_on: return
        self.btn_up_event.update()
        self.btn_down_event.update()
        self.btn_yes_event.update()
        self.btn_back_event.update()
        dis = self.display
        dis.fill(0)
        self.count_fps += 1
        self.current_menu.update()
        if not self.custom_page: self.selector.update()
        dis.rect(0, 0, display_w, top_gap, 0, 1)
        dis.rect(0, top_gap, out_gap, display_h, 0, 1)
        dis.rect(right_mask_x, top_gap, out_gap, display_h, 0, 1)
        if self.others:
            for i in self.others: i.update()
        if check_fps:
            dis.rect(0, 0, 25, 6, 0, 1)
            dis.text(str(self.fps), 0, 0)
        dis.show()

class ScrollBar:
    def __init__(self):
        self.display = manager.display
        self.pos = Pos()

class XScrollBar(ScrollBar):
    def __init__(self):
        super().__init__()
        self.drw = self.display.rect
    
    def update(self):
        # out_gap is x pos
        # top_gap is y pos
        pos = self.pos
        self.drw(out_gap, xscrollbar_mask_y, xscrollbar_w, xscrollbar_mask_h, 0, 1)
        self.drw(out_gap, top_gap, pos.w, pos.h, 1, 1)
    
    def update_val(self):
        menu = manager.current_menu
        if menu.count_children == 1:
            w = xscrollbar_w
        else:
            w = menu.selected_id/(menu.count_children-1)*xscrollbar_w

        self.pos.animation((out_gap, top_gap, round(w), xscrollbar_h), ease_func=scrollbar_ease)

class YScrollBar(ScrollBar):
    def __init__(self):
        super().__init__()
        self.drw = self.display.rect
        self.line = self.display.line
    
    def update(self):
        # yscrollbar_x is x pos
        # top_gap is y pos
        pos = self.pos
        
        self.drw(yscrollbar_mask_x, top_gap, yscrollbar_mask_w, yscrollbar_h, 0, 1)
        self.line(yscrollbar_line_x, top_gap, yscrollbar_line_x, yscrollbar_line_yh, 1)
        self.line(yscrollbar_x, yscrollbar_bottom_line_y, yscrollbar_line_xw, yscrollbar_bottom_line_y, 1)
        self.drw(yscrollbar_x, top_gap, pos.w, pos.h, 1, 1)
    
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
        return (x-self.camera.x+list_selector_left_space,
                y-self.camera.y+list_selector_top_space)
    
    def update(self):
        if self.camera.pos_buffer: self.camera.update()
        for child in self.children:
            _pos = child.pos
            _y = _pos.y-self.camera.y+self.top_space
            if _pos.pos_buffer: _pos.update()
            if  _y>display_h or _y+_pos.h<0: continue
            child.update()
        for other in self.others:
            if other.pos.pos_buffer: other.pos.update()
            other.update()
    
    # @timeit
    def change_selected(self, child):
        pass
    
    # @timeit
    def update_camera(self, scroll_page=False):
        pos = manager.selector.selected.pos
        cam = self.camera
        y = pos.dy
        yh = y + pos.h + list_space
        x = cam.x
        # 1是选择器的宽度
        if scroll_page or y < cam.y:
            cam.animation((x, y), camera_speed, only_xy=True, ease_func=camera_ease)
        elif yh > cam.y+cam.h:
            cam.animation((x, yh-dish_gap+1), camera_speed, only_xy=True, ease_func=camera_ease)
    
    def add(self, child):
        child.parent = self
        child.id = const(self.count_children)
        pos = child.pos
        pos.dx = pos.x
        pos.dy = list_item_space*self.count_children
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
        if self.camera.pos_buffer: self.camera.update()
        for child in self.children:
            if child.pos.pos_buffer: child.pos.update()
            child.update()
        for other in self.others:
            if other.pos.pos_buffer: other.pos.update()
            other.update()
    
    def change_selected(self, child):
        self.title_label.set_text(child.title)
        pos = self.title_label.pos
        pos.y = display_h
        pos.x = half_disw - pos.w // 2
        pos.dx = pos.x
        pos.dy = display_h - pos.h - icon_title_bottom
        pos.animation((pos.dx, pos.dy), only_xy=True, ease_func=icon_title_ease)
    
    def update_camera(self, scroll_page=False):
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
    def __init__(self, text: str='', duration: int=1000):
        # 此类原来应继承于Dialog
        self.type = 'TextDialog'
        self.duration = duration
        self.text = text
        self.pos = Pos()
        self.camera = Pos()  # 由Label调用，不起任何作用(但是不可删除)
        self.display = manager.display
        self.drw = self.display.list_selector  # 其实就是圆角矩形
        self.rect = self.display.rect
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
    def open(self):
        self.animation()
        self.opening = True
        if not self.appended:
            manager.others.append(self)
            self.appended = True
    
    # @timeit
    def close(self, n=False):
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
        if pos.pos_buffer: pos.update()
        elif self.closing and pos.x == display_w:
            self.appended = False
            self.closing = False
            manager.others.remove(self)
        elif self.opening:
            self.opening = False
            self.opened = True
            self.open_time = utime.ticks_ms()
        self.rect(pos.x-2, pos.y-2, pos.w+4, pos.h+4, 0, 1)
        if self.child.pos.pos_buffer: self.child.pos.update()
        self.child.update()
        _xw = pos.x+pos.w
        self.rect(_xw-2, pos.y-2, display_w-_xw+2, pos.h+4, 0, 1)
        self.drw(pos.x, pos.y, pos.w, pos.h, 1, 0)

class BaseWidget:
    def __init__(self, parent):
        self.display = manager.display
        self.parent = parent
        if parent: self.camera = parent.camera
        self.pos = Pos()
        self.id = 0
        self.type = 'BaseWidget'

class Label(BaseWidget):
    def __init__(self, parent, text=None, link=None, append_list: bool=True, offset_pos: bool=True,
                 always_scroll: bool=False, scroll_w=False, try_scroll: bool=True, scroll_speed=False,
                 load: bool=True):
        ''' Label标签组件
        Args:
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
        '''
        super().__init__(parent)
        self.type = 'LabelWidget'
        font = ufont.BMFont(self.display, font_path)
        self.font = font
        self.text = text
        self.title = text
        self.link = link
        self.link_ = link
        self.pos.h = font_size
        self.drw = font.text
        self.xscroll = 0
        self.offset = offset_pos
        self.widget = None
        self.always_scroll = always_scroll
        self.try_scroll = try_scroll
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
    
    # @timeit
    def update(self):
        pos = self.pos
        if self.try_scroll:
            # TODO: 或需可以使用framebuffer的滚动功能？
            if manager.selector.selected is self or self.always_scroll or self.xscroll:
                scr_w = self.scroll_w
                _cposw = 0
                if self.widget:
                    _cposw = self.widget.pos.w+widget_gap
                    scr_w -= _cposw
                if pos.w+out_gap > scr_w:
                    self.xscroll += self.scroll_speed
                    if manager.selector.selected is not self and abs(self.xscroll) < self.scroll_speed: self.xscroll = 0
                    if self.xscroll > pos.w: self.xscroll = -list_max_w+_cposw
        x, y = pos.x, pos.y
        if self.offset:
            x, y = manager.current_menu.offset_pos(x, y)
        self.drw(x-self.xscroll, y)
        if self.widget: self.widget.update()

class Icon(BaseWidget):
    def __init__(self, parent, filepath=None, title='', link=None, append_list: bool=True, offset_pos: bool=True):
        super().__init__(parent)
        self.type = 'IconWidget'
        pbm = upbm.PBMImage(self.display, filepath)
        self.pbm = pbm
        self.link = link
        self.pos.h, self.pos.w = icon_size, icon_size
        self.drw = pbm.image
        self.title = title
        self.offset = offset_pos
        # 在启动时加载图片
        manager.load_list.append(self)
        if append_list: parent.add(self)
    
    def init(self):
        # 耗时操作,会在启动时被manager调用加载
        self.pbm.init()
    
    def set_image(self, filepath):
        self.filepath = filepath
        self.pbm.filepath = filepath
        self.pbm.init()
    
    def update(self):
        cam = self.camera
        pos = self.pos
        x, y = pos.x, pos.y
        if self.offset:
            x, y = manager.current_menu.offset_pos(x, y)
        self.drw(x, y)

class CheckBox(BaseWidget):
    def __init__(self, parent, default=False, link=None):
        super().__init__(parent)
        self.value = default
        self.link_ = link
        pos = self.pos
        pos.w = 10
        pos.h = 10
        pos.x = list_max_w-widget_gap-pos.w
        pos.y = self.parent.pos.dy+half_list_item_space-5
        self.parent.add(self)
    
    def update(self):
        pos = self.pos
        cam = self.camera
        x = pos.x-cam.x+list_selector_left_space
        y = pos.y-cam.y+top_gap
        self.display.rect(x-widget_gap, y-5, display_w-x+widget_gap, font_size, 0, 1)  # mask
        self.display.rect(x, y, pos.w, pos.h, 1, 0)
        if self.value: self.display.rect(x+2, y+2, pos.w-4, pos.h-4, 1, 1)
    
    def widget_callback(self):
        self.value = not self.value
        if callable(self.link_): self.link_(self.idx)

class ListSelector(BaseWidget):
    def __init__(self, parent, range_list, default_idx=False, loop=False,
                 link=None, change_link=None, flash_speed=False):
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
        self.flash_sataus = False
        self.flash_speed = flash_speed
        if flash_speed is False:
            self.flash_speed = widget_flash_speed
        self.child = Label(self, text=str(self.value), append_list=False, try_scroll=False, load=False)
        self.up, self.down = None, None
        manager.load_list.append(self)
        self.parent.add(self)
    
    def update(self):
        pos = self.pos
        cam = self.camera
        x = pos.x-cam.x+list_selector_left_space
        y = pos.y-cam.y+top_gap
        self.display.rect(x-widget_gap, y, pos.w+widget_gap_m2, pos.h, 0, 1)
        now = utime.ticks_ms()
        if not self.activate: self.flash_sataus = True  # 未被激活时不闪烁
        elif utime.ticks_diff(now, self.last_time) > self.flash_speed:
            self.flash_sataus = not self.flash_sataus
            self.last_time = now
        
        if self.flash_sataus:
            self.child.update()
    
    def init(self):
        self.child.init()
        pos = self.pos
        cpos = self.child.pos
        pos.w = cpos.w
        pos.h = cpos.h
        pos.x = list_max_w-widget_gap-pos.w
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
    def __init__(self, parent, default_num=0, min_num=0, max_num=10, step=1,
                 loop=False, link=None, change_link=None, flash_speed=False):
        num_list = [i for i in range(min_num, max_num+1, step)]
        _change_link = change_link
        _link = link
        if callable(change_link): change_link = lambda v: _change_link(num_list[v])
        if callable(link): link = lambda v: _link(num_list[v])
        super().__init__(parent, num_list, num_list.index(default_num), loop, link, change_link, flash_speed)
        
class _BuiltinXDashLine:
    def __init__(self, from_x, to_x, y, **kws):
        # 验证是否有内部类调用，而不是由用户调用(可删除)
        if 'builtin_allow' not in kws.keys():
            if kws['builtin_allow'] != 'AllowByBuiltinWidget':
                print('! WARNING: Using A Builtin-Widget XDashLine Widget')
        
        self.type = '(Builtin)XDashLineWidget'
        self.display = manager.display
        
        self.pos = Pos()  # 所有组件必须拥有Pos
        self.from_x = from_x
        self.to_x = to_x
        self.y = const(y+top_gap)
        self.w = to_x-from_x
        self.length = to_x - from_x
        self.split_num = self.length // icon_dashline_split_length
        
        self.buffer = bytearray(self.w)
        self.fb = framebuf.FrameBuffer(self.buffer, self.w, 1, framebuf.MONO_HLSB)
        self.drw = self.fb.line
        blit = self.display.blit
        self.update = lambda: blit(self.fb, self.from_x, self.y)
        
        manager.load_list.append(self)
    
    def init(self):
        color = 0
        x = 0
        for _ in range(self.split_num):
            to_x = x + icon_dashline_split_length
            self.drw(x, 0, to_x, 0, color)
            x = to_x
            color = not color

class CustomWidget:
    # no parent widget
    def __init__(self, link=None, as_others: bool=True):
        self.display = manager.display
        self.type = 'CustomWidget'
        self.pos = Pos()
        self.link = link
        if as_others: manager.others.append(self)

class Page:
    def __init__(self, up=None, down=None, yes=None):
        self.type = 'CustomPage'
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
            if child.pos.pos_buffer: child.pos.update()
            child.update()

def Item(parent, *args, **kws):
    if isinstance(parent, ListMenu): return Label(parent, *args, **kws)
    elif isinstance(parent, IconMenu): return Icon(parent, *args, **kws)
    else: print('Unknown menu type, it\'s maybe a custom page.DO NOT use function "Item" in a custom page.')

def open_dialog(dialog, text):
    dialog.set_text(text)
    dialog.open()
