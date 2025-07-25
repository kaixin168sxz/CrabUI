'''
main file
last edited: 2025.7.24
'''

from .config import *
from .libs import oled, ufont, upbm
import utime
from random import randint
from .apis import *
import framebuf

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
        self.dx, self.dy, self.dw, self.dh = None, None, None, None
        self.pos_buffer = []
    
    @micropython.native
    def animation(self, pos: tuple, num_frames=None, only_xy=False, ease_func=None):
        if stop_last_ani: self.pos_buffer.clear()
        if not ease_func: ease_func = default_ease
        if num_frames is None: num_frames = default_speed
        x, y, w, h = self.x, self.y, self.w, self.h
        ex = pos[0]
        ey = pos[1]
        ew, eh = 0, 0
        if not only_xy:
            ew = pos[2]
            eh = pos[3]
        dx, dy, dw, dh = ex-x, ey-y, ew-w, eh-h
        num_frames_sub1 = num_frames - 1
        for i in range(num_frames):
            eased = ease_func(i / num_frames_sub1)
            res = [int(x+dx*eased), int(y+dy*eased),
                   False if only_xy else int(w+dw*eased),
                   False if only_xy else int(h+dh*eased)]
            self.pos_buffer.append(res)
    
    @micropython.native
    def update(self):
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
    
    @micropython.native
    # @timeit
    def update(self):
        menu = manager.current_menu
        pos = self.pos
        cam = menu.camera
        dis = self.display
        if pos.pos_buffer: pos.update()
        self.drw(pos.x-cam.x+out_gap, pos.y-cam.y+top_gap, pos.w, pos.h)
    
    @micropython.native
    # @timeit
    def select(self, child, scroll_page=False, update_cam=True):
        pos: Pos = child.pos
        menu: Menu = manager.current_menu
        menu_type = menu.type
        if menu_type == 'ListMenu':
            cposw = 0
            if child.widget:
                cposw = child.widget.pos.w+widget_gap
            w = min(list_max_w-cposw, pos.w+list_selector_left_gap*2)
            self.pos.animation((pos.dx, pos.dy, w, pos.h+list_selector_top_gap*2),
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
    
    @micropython.native
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
    
    @micropython.native
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
            self.display.init_display()
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
        if check_fps:
            Timer(0, period=1000, callback=self.check_fps)
        
        btn_up = Pin(pin_up, Pin.IN, Pin.PULL_UP)
        btn_down = Pin(pin_down, Pin.IN, Pin.PULL_UP)
        btn_yes = Pin(pin_yes, Pin.IN, Pin.PULL_UP)
        btn_back = Pin(pin_back, Pin.IN, Pin.PULL_UP)
        
        btn_callback = self.btn_pressed
        IRQ_RISING = Pin.IRQ_RISING
        btn_up.irq(lambda n: btn_callback(self.up), IRQ_RISING)
        btn_down.irq(lambda n: btn_callback(self.down), IRQ_RISING)
        btn_yes.irq(lambda n: btn_callback(self.yes), IRQ_RISING)
        btn_back.irq(lambda n: btn_callback(self.back), IRQ_RISING)
    
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
    
    @micropython.native
    def startup(self):
        dis = self.display
        if not show_startup_page:
            self.load()
            self.starting_up = False
            return

        x = int(display_w/2)-int(logo_length/2)
        y = int(display_h/2)-int(driver_enfont_h/2)
        pos = Pos(x=x, y=-10)
        pos.animation((x, y, logo_length, driver_enfont_h))
        back = False
        while self.starting_up:
            if pos.pos_buffer: pos.update()
            dis.fill(0)
            dis.text(logo_text, pos.x, pos.y)  # centre 居中显示
#             self.display.rect(0, pos.y + y, display_w, 2)
            dis.show()
            if pos.pos_buffer: continue
            # 动画播放结束
            if not back:     # logo已经显示
                self.load()  # 加载
                back = True
                pos.animation((x, -10, logo_length, driver_enfont_h))    # 播放新的动画,让logo回到屏幕外
            else:
                self.starting_up = False     # logo已经回到屏幕外
    
    @timeit
    def load(self):
        load_list = self.load_list
        for _ in range(len(load_list)):
            load_list[0].init()
            self.load_list.pop(0)
    
    def yes(self):
        link = self.selector.selected.link
        if callable(link): link()
    
    def back(self):
        if len(self.history) > 1:
            self.history.pop(-1)
            self.set_menu(self.history[-1], record_history=False)
    
    def up(self):
        if hasattr(self.selector.selected.widget, 'up'):
            func = self.selector.selected.widget.up
            if callable(func):
                func()
                return
        self.selector.up()
    
    def down(self):
        if hasattr(self.selector.selected.widget, 'down'):
            func = self.selector.selected.widget.down
            if callable(func):
                func()
                return
        self.selector.down()
    
    # @timeit
    def btn_pressed(self, func):
        if self.starting_up: return
        new_time = utime.ticks_ms()
        if (new_time - self.last_pressed) < btn_sleep_time: return 
        self.last_pressed = new_time
        func()
    
    @micropython.native
    # @timeit
    def set_menu(self, menu: Menu, record_history=True):
        if record_history: self.history.append(menu)
        if expand_ani:
            if self.current_menu:
                for i in self.current_menu.children:
                    i.pos.x = 0
                    i.pos.y = 0
            for i in menu.children:
                i.pos.animation((i.pos.dx, i.pos.dy), expand_speed, only_xy=True, ease_func=expand_ease)
        selector = self.selector
        dis = self.display
        if self.starting_up:
            print('booting...')
            self.startup()
        if not menu.count_children:
            raise IndexError('a menu should have one or more items')
        self.current_menu = menu
        selector.drw = {'ListMenu': dis.list_selector,
                        'IconMenu': dis.icon_selector}[menu.type]
        selector.select(menu.children[menu.selected_id], update_cam=True)
    
    @micropython.native
    # @timeit
    def update(self, *args):
        if not self.display_on: return
        self.display.fill(0)
        self.count_fps += 1
        self.current_menu.update()
        self.selector.update()
        fb = self.display
        fb.rect(0, 0, display_w, top_gap, 0, 1)
        fb.rect(0, top_gap, out_gap, display_h, 0, 1)
        fb.rect(right_mask_x, top_gap, out_gap, display_h, 0, 1)
        if self.others:
            for i in self.others: i.update()
        if check_fps:
            fb.rect(0, 0, 25, 6, 0, 1)
            fb.text(str(self.fps), 0, 0)
        self.display.show()

class ScrollBar:
    def __init__(self):
        self.display = manager.display
        self.pos = Pos()

class XScrollBar(ScrollBar):
    def __init__(self):
        super().__init__()
        self.drw = self.display.rect
    
    @micropython.native
    def update(self):
        # out_gap is x pos
        # top_gap is y pos
        pos = self.pos
        if pos.pos_buffer: pos.update()
        self.drw(out_gap, xscrollbar_mask_y, xscrollbar_w, xscrollbar_mask_h, 0, 1)
        self.drw(out_gap, top_gap, pos.w, pos.h, 1, 1)
    
    @micropython.native
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
    
    @micropython.native
    def update(self):
        # yscrollbar_x is x pos
        # top_gap is y pos
        pos = self.pos
        if pos.pos_buffer: pos.update()
        
        self.drw(yscrollbar_mask_x, top_gap, yscrollbar_mask_w, yscrollbar_h, 0, 1)
        self.line(yscrollbar_line_x, top_gap, yscrollbar_line_x, yscrollbar_line_yh, 1)
        self.line(yscrollbar_x, yscrollbar_bottom_line_y, yscrollbar_line_xw, yscrollbar_bottom_line_y, 1)
        self.drw(yscrollbar_x, top_gap, pos.w, pos.h, 1, 1)
    
    @micropython.native
    # @timeit
    def update_val(self):
        menu = manager.current_menu
        if menu.count_children == 1:
            h = yscrollbar_h
        else:
            h = menu.selected_id/(menu.count_children-1)*yscrollbar_h

        self.pos.animation((yscrollbar_x, top_gap, yscrollbar_w, round(h)), ease_func=scrollbar_ease)

class Menu:
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
    
    @micropython.native
    # @timeit
    def update(self):
        cam = self.camera
        cam_y = cam.y
        cam_yh = cam_y+display_h
        if cam.pos_buffer: cam.update()
        selected_id = self.selected_id
        for child in self.children:
            child.update()
        for other in self.others:
            other.update()

class ListMenu(Menu):
    def __init__(self):
        super().__init__()
        self.type = 'ListMenu'
        self.scrollbar = YScrollBar()
        self.others.append(self.scrollbar)
        self.camera.h = list_max_h
    
    # @timeit
    def change_selected(self, child):
        pass
    
    @micropython.native
    # @timeit
    def update_camera(self, scroll_page=False):
        pos = manager.selector.selected.pos
        cam = self.camera
        y = pos.dy
        yh = y + pos.h + list_space
        x = cam.x
        if scroll_page or y < cam.y:
            cam.animation((x, y), camera_speed, only_xy=True, ease_func=camera_ease)
        elif yh > cam.y+cam.h:
            cam.animation((x, yh - dish_gap), camera_speed, only_xy=True, ease_func=camera_ease)
    
    def add(self, child):
        count_children = self.count_children
        child.parent = self
        child.id = const(count_children)
        pos = child.pos
        pos.dx = pos.x
        pos.dy = list_item_space*count_children
        if not expand_ani: pos.y = pos.dy
        self.children.append(child)
        self.count_children += 1

class IconMenu(Menu):
    def __init__(self):
        super().__init__()
        self.type = 'IconMenu'
        self.scrollbar = XScrollBar()
        self.dash_line = _BuiltinXDashLine(0, display_w, dashline_h, builtin_allow='AllowByBuiltinWidget')
        self.title_label = Label(self, '', append_list=False, offset_pos=False)
        self.title_label.pos.y = display_h
        self.others.append(self.title_label)
        self.others.append(self.scrollbar)
        self.others.append(self.dash_line)
        self.camera.w = icon_max_w
    
    def change_selected(self, child):
        self.title_label.set_text(child.title)
        pos = self.title_label.pos
        pos.y = display_h
        pos.x = half_disw - pos.w / 2
        pos.dx = pos.x
        pos.dy = display_h - pos.h - icon_title_bottom
        pos.animation((pos.dx, pos.dy), only_xy=True, ease_func=icon_title_ease)
    
    @micropython.native
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
        # TODO: 优化
        self.type = 'TextDialog'
        self.timer = Timer(1)
        self.duration = duration
        self.text = text
        self.pos = Pos()
        self.camera = Pos()  # 由Label调用，不起任何作用(但是不可删除)
        self.display = manager.display
        self.drw = self.display.list_selector  # 其实就是圆角矩形
        # TextDialog目前仅支持显示一个Label组件
        self.child = Label(self, text, append_list=False, offset_pos=False)
        self.closing = False
        self.opening = False
        self.opened = False
        self.open_time = 0
        self.appended = False
        if self.child.pos.w > dialog_max_w:
            print('Dialog text too long')
        manager.load_list.append(self)
    
    # @timeit
    @micropython.native
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
    
    @micropython.native
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
    @micropython.native
    def open(self):
        self.animation()
        self.opening = True
        if not self.appended:
            manager.others.append(self)
            self.appended = True
    
    # @timeit
    @micropython.native
    def close(self, n=False):
        self.closing = True
        self.opened = False
        cpos = self.child.pos
        pos = self.pos
        pos.animation((display_w, dialog_out_gap), dialog_speed, ease_func=dialog_ease, only_xy=True)
        cpos.animation((display_w, dialog_out_gap+dialog_in_gap), dialog_speed, ease_func=dialog_ease, only_xy=True)
        
    # @timeit
    @micropython.native
    def update(self):
        pos = self.pos
        if self.opened and utime.ticks_diff(utime.ticks_ms(), self.open_time) > self.duration:
            self.close()
        if pos.pos_buffer:
            pos.update()
        elif self.closing and pos.x == display_w:
            self.appended = False
            manager.others.remove(self)
            self.closing = False
        elif self.opening:
            self.opening = False
            self.opened = True
            self.open_time = utime.ticks_ms()
        self.drw(pos.x-2, pos.y-2, pos.w+4, pos.h+4, 0, 1)
        self.child.update()
        self.drw(pos.x+pos.w-2, pos.y-2, display_w, pos.h+4, 0, 1)
        self.drw(pos.x, pos.y, pos.w, pos.h)
        

class Widget:
    def __init__(self, parent):
        self.display = manager.display
        self.parent = parent
        self.camera = parent.camera
        self.pos = Pos()
        self.id = 0
        self.type = 'BaseWidget'

class Label(Widget):
    def __init__(self, parent, text=None, link=None, append_list: bool=True, offset_pos: bool=True,
                 always_scroll: bool=False, scroll_w=False, try_scroll: bool=True, scroll_speed=False):
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
        self.scroll = False
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
        manager.load_list.append(self)
        if append_list: parent.add(self)
    
    def add(self, widget):
        self.link = self.widget_callback
        self.widget = widget
    
    @micropython.native
    def init(self):
        # 耗时操作,会在启动时被manager调用加载
        self.pos.w = self.font.init(self.text)
    
    def widget_callback(self):
        self.widget.widget_callback()
        if callable(self.link_): self.link_()
    
    @micropython.native
    def set_text(self, text):
        self.text = text
        self.init()
        selector = manager.selector
        if selector.selected is self:
            selector.select(self)
    
    @micropython.native
    # @timeit
    def update(self):
        cam = self.camera
        pos = self.pos
        if pos.pos_buffer: pos.update()
        if self.try_scroll:
            scr_w = self.scroll_w
            cposw = 0
            widget = self.widget
            if widget:
                cposw = widget.pos.w+widget_gap
                scr_w -= cposw
            self.scroll = (manager.selector.selected is self or self.always_scroll) and pos.w+out_gap > scr_w
            if self.scroll or self.xscroll:
                self.xscroll += self.scroll_speed
                if self.xscroll > pos.w: self.xscroll = -list_max_w+cposw
        x, y = pos.x, pos.y
        if self.offset:
            x = x-cam.x+list_selector_space
            y = y-cam.y+top_gap
        self.drw(x-self.xscroll, y)
        if self.widget: self.widget.update()

class Icon(Widget):
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
    
    @micropython.native
    def init(self):
        # 耗时操作,会在启动时被manager调用加载
        self.pbm.init()
    
    @micropython.native
    def set_image(self, filepath):
        self.filepath = filepath
        self.pbm.filepath = filepath
        self.pbm.init()
    
    @micropython.viper
    def update(self):
        cam = self.camera
        pos = self.pos
        if pos.pos_buffer: pos.update()
        x, y = pos.x, pos.y
        if self.offset:
            x = x-cam.x+icon_selector_left_space
            y = y-cam.y+icon_selector_top_space
        self.drw(x, y)

class CheckBox(Widget):
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
    
    @micropython.native
    def update(self):
        pos = self.pos
        cam = self.camera
        x = pos.x-cam.x+list_selector_space
        y = pos.y-cam.y+top_gap
        self.display.rect(x-widget_gap, y-half_list_item_space+5, display_w-(x-widget_gap), font_size, 0, 1)  # mask
        self.display.rect(x, y, pos.w, pos.h, 1, 0)
        if self.value: self.display.rect(x+2, y+2, pos.w-4, pos.h-4, 1, 1)
    
    def widget_callback(self):
        self.value = not self.value
        if callable(self.link_): self.link_(self.idx)

class ListSelector(Widget):
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
        self.child = Label(self, text=str(self.value), append_list=False, try_scroll=False)
        self.up, self.down = None, None
        manager.load_list.append(self)
        self.parent.add(self)
    
    @micropython.native
    def update(self):
        pos = self.pos
        cam = self.camera
        x = pos.x-cam.x+list_selector_space
        y = pos.y-cam.y+top_gap
        self.display.rect(x-widget_gap, y, pos.w+widget_gap*2, pos.h, 0, 1)
        now = utime.ticks_ms()
        if not self.activate: self.flash_sataus = True  # 未被激活时不闪烁
        elif utime.ticks_diff(now, self.last_time) > self.flash_speed:
            self.flash_sataus = not self.flash_sataus
            self.last_time = now
        
        if self.flash_sataus:
            self.child.update()
    
    @micropython.native
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
    
    @micropython.native
    def set_text(self, value):
        self.value = value
        self.child.set_text(str(value))
        self.init()
        if manager.selector.selected is self.parent:
            manager.selector.select(self.parent)
    
    def widget_callback(self):
        self.activate = not self.activate
        if self.activate:
            self.up, self.down = self._up, self._down
            self.last_time = utime.ticks_ms()
        else:
            self.up, self.down = None, None
            if callable(self.link_): self.link_(self.idx)
    
    @micropython.native
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
    
    @micropython.native
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
        num_range = [i for i in range(min_num, max_num+1, step)]
        _change_link = change_link
        change_link = lambda v: _change_link(num_range[v])
        super().__init__(parent, num_range, default_num-min_num, loop, link, change_link, flash_speed)
        
class _BuiltinXDashLine:
    def __init__(self, from_x, to_x, y, **kws):
        # 验证是否有内部类调用，而不是由用户调用(可删除)
        if 'builtin_allow' not in kws.keys():
            if kws['builtin_allow'] != 'AllowByBuiltinWidget':
                print('! WARNING: Using A Builtin-Widget XDashLine Widget')
        
        self.type = '(Builtin)XDashLineWidget'
        self.display = manager.display
        self.drw = self.display.line
        self.from_x = from_x
        self.to_x = to_x
        self.y = y
        self.length = to_x - from_x
        self.split_num = self.length // icon_dashline_split_length
    
    @micropython.native
    def update(self):
        color = 0
        x, y = self.from_x, self.y
        for _ in range(self.split_num):
            to_x = x + icon_dashline_split_length
            self.drw(x, y, to_x, y, color)
            x = to_x
            color = not color

def Item(parent, *args, **kws):
    if isinstance(parent, ListMenu): return Label(parent, *args, **kws)
    elif isinstance(parent, IconMenu): return Icon(parent, *args, **kws)

def text_dialog(dialog, text):
    dialog.set_text(text)
    dialog.open()
