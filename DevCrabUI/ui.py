"""
main file
last edited: 2025.8.27
"""

from .config import *
from .libs import ufont, upbm, drawer
import bufxor
import utime
from machine import I2C, Pin, Timer, SPI, SoftI2C, SoftSPI
import framebuf
from gc import collect

class Pos:
    """
    位置类，用于管理组件的位置和动画
    """
    def __init__(self, x=0, y=0, w=0, h=0):
        """
        初始化位置对象

        Args:
            x: x坐标
            y: y坐标
            w: 宽度
            h: 高度
        """
        self.x, self.y, self.w, self.h = x, y, w, h
        # 用于保存目标坐标(destination pos)
        self.dx, self.dy, self.dw, self.dh = x, y, w, h
        self.generator = None
        self.last_time = False

    def animation(self, pos: tuple, num_frames=None, only_xy=False, ease_func=None):
        """
        设置位置动画

        Args:
            pos: 目标位置元组 (x, y, w, h)
            num_frames: 动画帧数
            only_xy: 是否只动画x,y坐标
            ease_func: 缓动函数
        """
        self.generator = self._animation_generator(pos, num_frames, only_xy, ease_func)

    def _animation_generator(self, pos: tuple, num_frames=None, only_xy=False, ease_func=None):
        """
        位置动画生成器

        Args:
            pos: 目标位置元组
            num_frames: 动画帧数
            only_xy: 是否只动画x,y坐标
            ease_func: 缓动函数

        Yields:
            每一帧的位置信息
        """
        ease_func = ease_func if ease_func else default_ease
        if num_frames is None: num_frames = default_speed
        x, y, w, h = self.x, self.y, self.w, self.h
        _num_frames_sub1 = num_frames - 1
        if only_xy:
            dx, dy = pos[0]-x, pos[1]-y
            for i in range(num_frames):
                eased = ease_func(i / _num_frames_sub1)
                yield [int(x+dx*eased), int(y+dy*eased), w, h]
        else:
            dx, dy, dw, dh = pos[0]-x, pos[1]-y, pos[2]-w, pos[3]-h
            for i in range(num_frames):
                eased = ease_func(i / _num_frames_sub1)
                yield [int(x+dx*eased), int(y+dy*eased), int(w+dw*eased), int(h+dh*eased)]

    def update(self):
        """更新位置动画"""
        # 防止动画因为帧数过高而变快
        now = utime.ticks_ms()
        if utime.ticks_diff(now, self.last_time) < base_ani_sleep: return
        self.last_time = now

        try:
            self.x, self.y, self.w, self.h = next(self.generator)
        except StopIteration:
            self.generator = None

    def centre(self, x:int=0, y:int=0):
        return (display_w // 2 - self.w // 2) + x, (display_h // 2 - self.h // 2) + y

class Selector:
    """
    选择器类，用于在菜单中显示当前选中项
    """
    def __init__(self):
        """初始化选择器"""
        self.pos = Pos()
        self.fbuf = display
        if selector_fill:
            self.buf = bytearray(display_fb_size)
            self.fbuf = framebuf.FrameBuffer(self.buf, display_w, display_h, framebuf.MONO_VLSB)
        self.drw = drawer.round_rect
        self.selected = None

    # @timeit
    def update(self):
        """更新选择器显示"""
        pos = self.pos
        cam = manager.current_menu.camera
        if pos.generator:
            pos.update()
        if selector_fill:
            self.fbuf.fill(0)
        self.drw(self.fbuf, pos.x-cam.x+out_gap, pos.y-cam.y+top_gap, pos.w, pos.h, 1, selector_fill)

    # @timeit
    def select(self, child, update_cam=True):
        """
        选择指定子项

        Args:
            child: 要选择的子项
            update_cam: 是否更新相机位置
        """
        pos: Pos = child.pos
        menu = manager.current_menu
        if menu.type == 0:
            child_w = 0  # child pos w
            if hasattr(child, 'widget') and child.widget:
                child_w = child.widget.pos.w+widget_gap*2
            w = min(list_max_w-child_w, pos.w+list_selector_left_gap*2+1)
            # 1是选择器的宽度
            self.pos.animation((pos.dx, pos.dy, w, pos.h+list_selector_top_gap*2+1),
                               selector_speed, ease_func=selector_ease)
        elif menu.type == 1:
            # 1是选择器的宽度
            self.pos.animation((pos.dx, pos.dy+xscrollbar_space+1, pos.w+icon_selector_gap*2,
                                pos.h+icon_selector_gap*2), selector_speed, ease_func=selector_ease)
        menu.change_selection(child)
        self.selected = child
        menu.selected_id = self.selected.id
        menu.scrollbar.update_val()
        if update_cam: menu.update_camera()

    def up(self):
        """选择上一个项目"""
        child_id = self.selected.id
        last_id = manager.current_menu.count_children-1
        if child_id == 0:
            if not menu_loop: return
            child_id = last_id
        else:
            child_id -= 1

        self.select(manager.current_menu.children[child_id])

    def down(self):
        """选择下一个项目"""
        child_id = self.selected.id
        last_id = manager.current_menu.count_children-1
        if child_id == last_id:
            if not menu_loop: return
            child_id = 0
        else:
            child_id += 1

        self.select(manager.current_menu.children[child_id])

class ButtonEvent:
    """
    按钮事件处理类
    """
    def __init__(self):
        """初始化按钮事件处理器"""
        self.events = []

    def add(self, btn_pin, link, callback_on_pressed=False):
        """
        添加按钮事件

        Args:
            btn_pin: 按钮引脚
            link: 回调函数
            callback_on_pressed: 是否在按下时回调
        """
        self.events.append([Pin(btn_pin, Pin.IN, Pin.PULL_UP), False, link, callback_on_pressed])

    def update(self):
        """更新按钮状态并处理事件"""
        for btn_data in self.events:
            if btn_data[0].value():
                if not btn_data[1]: continue
                btn_data[1] = False
                if not btn_data[3]: btn_data[2]()
            else:
                if btn_data[1]: continue
                btn_data[1] = True
                if btn_data[3]: btn_data[2]()

class Manager:
    """
    管理器类，负责整个应用程序的管理
    """
    def __init__(self, driver=None, dis=None):
        """
        初始化管理器

        Args:
            driver: 显示驱动
            dis: 显示对象
        """
        global manager, display
        manager = self
        if not (driver or dis): raise ValueError('lost display and display_driver')
        if dis: display = dis
        else:
            if use_i2c:
                # i2c display
                if hardware_i2c:
                    i2c = I2C(hardware_i2c, scl=Pin(display_scl), sda=Pin(display_sda), freq=i2c_freq)
                else:
                    i2c = SoftI2C(scl=Pin(display_scl), sda=Pin(display_sda), freq=i2c_freq)
                display = driver.DisplayI2C(i2c, display_w, display_h)
                del i2c
            elif use_spi:
                # spi display
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
        self.current_menu: "ListMenu" | "IconMenu" | "Page" | None = None
        self.icon_menu_dashline = _XDashLine()

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

    def add(self, child):
        self.others.append(child)

    def up(self):
        """处理向上按键"""
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
        """处理向下按键"""
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
        """处理确认按键"""
        if self.custom_page:
            _func = self.current_menu.yes
            if callable(_func):
                _func()
            return
        link = self.selector.selected.link
        if callable(link):
            link()

    def back(self):
        """处理返回按键"""
        if len(self.history) <= 1:
            return
        self.history.pop(-1)
        self.page(self.history[-1], record_history=False)

    # @timeit
    def btn_pressed(self, func):
        """
        处理按钮按下事件

        Args:
            func: 要执行的函数
        """
        if self.starting_up: return
        func()

    # @timeit
    def check_fps(self, _timer=None):
        """检查并更新FPS"""
        self.fps = self.count_fps
        self.count_fps = 0

    def startup(self):
        """启动加载函数"""
        dis = display
        if not show_startup_page:
            self.load()
            self.starting_up = False
            return
        text = ufont.bitmap_font()
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
        """加载启动列表中的项目"""
        load_list = self.load_list
        for _ in range(len(load_list)):
            load_list[0].init()
            self.load_list.pop(0)
        collect()

    # @timeit
    def page(self, menu: "ListMenu" | "IconMenu" | "Page", record_history=True):
        """
        切换到指定页面

        Args:
            menu: 要切换到的菜单页面
            record_history: 是否记录到历史记录
        """
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
                expand_ease = icon_expand_ease if menu.type == 1 else list_expand_ease
                i.pos.animation((i.pos.dx, i.pos.dy), expand_speed, only_xy=True, ease_func=expand_ease)
        self.current_menu = menu
        if menu.type not in (0, 1):
            self.custom_page = True
            return
        self.custom_page = False
        selector: Selector = self.selector
        if not menu.count_children:
            raise IndexError('a menu should have one or more items')
        selector.drw = {0: drawer.round_rect,
                        1: drawer.icon_selector}[menu.type]
        selector.select(menu.children[menu.selected_id], update_cam=True)

    # @timeit
    def update(self, *_args):
        """更新显示内容"""
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
            for i in self.others:
                if i.pos.generator: i.pos.update()
                i.update()
        if check_fps:
            dis.fill_rect(0, 0, 30, 8, 0)
            dis.text(str(self.fps), 0, 0)
        dis.show()

class XScrollBar:
    """
    水平滚动条类
    """
    def __init__(self):
        """初始化水平滚动条"""
        self.pos = Pos()

    def update(self):
        """更新滚动条显示"""
        # out_gap is x pos
        # top_gap is y pos
        pos = self.pos
        display.fill_rect(out_gap, xscrollbar_mask_y, xscrollbar_w, xscrollbar_mask_h, 0)
        display.fill_rect(out_gap, top_gap, pos.w, pos.h, 1)

    def update_val(self):
        """更新滚动条值"""
        menu = manager.current_menu
        if menu.count_children == 1:
            w = xscrollbar_w
        else:
            w = (menu.selected_id + 1 ) / menu.count_children * xscrollbar_w

        self.pos.animation((out_gap, top_gap, round(w), xscrollbar_h), ease_func=scrollbar_ease)

class YScrollBar:
    """
    垂直滚动条类
    """
    def __init__(self):
        """初始化垂直滚动条"""
        self.pos = Pos()

    def update(self):
        """更新滚动条显示"""
        # yscrollbar_x is x pos
        # top_gap is y pos
        pos = self.pos

        display.fill_rect(yscrollbar_mask_x, top_gap, yscrollbar_mask_w, yscrollbar_h, 0)
        display.line(yscrollbar_line_x, top_gap, yscrollbar_line_x, yscrollbar_line_yh, 1)
        display.line(yscrollbar_x, yscrollbar_bottom_line_y, yscrollbar_line_xw, yscrollbar_bottom_line_y, 1)
        display.fill_rect(yscrollbar_x, top_gap, pos.w, pos.h, 1)

    # @timeit
    def update_val(self):
        """更新滚动条值"""
        menu = manager.current_menu
        if menu.count_children == 1:
            h = yscrollbar_h
        else:
            h = (menu.selected_id + 1 ) / menu.count_children * yscrollbar_h

        self.pos.animation((yscrollbar_x, top_gap, yscrollbar_w, round(h)), ease_func=scrollbar_ease)

class Page:
    """
    页面类
    """
    def __init__(self, up=None, down=None, yes=None, page_type=-1):
        """
        初始化页面

        Args:
            up: 向上按键处理函数
            down: 向下按键处理函数
            yes: 确认按键处理函数
            page_type: 页面类型
        """
        self.type = page_type
        self.children = []
        self.count_children = 0
        self.camera = Pos()
        self.camera.w, self.camera.h = display_w, display_h
        self.up, self.down, self.yes = up, down, yes
        self.others = []
        self.scrollbar = None
        self.selected_id = 0
        self.x_offset = out_gap
        self.y_offset = top_gap

    def offset_pos(self, x, y):
        """
        计算偏移后的位置

        Args:
            x: 原始x坐标
            y: 原始y坐标

        Returns:
            tuple: 偏移后的坐标
        """
        return (x-self.camera.x+self.x_offset,
                y-self.camera.y+self.y_offset)

    def add(self, child):
        """
        添加子项到页面

        Args:
            child: 要添加的子项
        """
        child.id = self.count_children
        self.children.append(child)
        self.count_children += 1

    def update(self):
        """更新页面显示"""
        for child in self.children:
            if child.pos.generator: child.pos.update()
            child.update()

class ListMenu(Page):
    """
    列表菜单类
    """
    def __init__(self):
        """初始化列表菜单"""
        super().__init__(page_type=0)
        self.scrollbar = YScrollBar()
        self.others.append(self.scrollbar)
        self.camera.h = list_max_h
        self.x_offset = list_selector_left_space+1
        self.y_offset = list_selector_top_space

    def update(self):
        """更新菜单显示"""
        if self.camera.generator: self.camera.update()
        for child in self.children:
            _pos = child.pos
            _y = _pos.y-self.camera.y+top_gap
            if _pos.generator: _pos.update()
            if  _y>display_h or _y+_pos.h<0: continue
            child.update()
        for other in self.others:
            if other.pos.generator: other.pos.update()
            other.update()

    # @timeit
    def change_selection(self, child):
        """
        更改选中项

        Args:
            child: 新的选中项
        """
        pass

    # @timeit
    def update_camera(self):
        """更新相机位置"""
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
        """
        添加子项到菜单

        Args:
            child: 要添加的子项
        """
        child.parent = self
        child.id = self.count_children
        pos = child.pos
        pos.dx = pos.x
        dy = 0
        for i in range(self.count_children):
            dy += list_space+self.children[i].pos.h
        pos.dy = dy
        if not expand_ani: pos.y = pos.dy
        self.children.append(child)
        self.count_children += 1

class IconMenu(Page):
    """
    图标菜单类
    """
    def __init__(self):
        """初始化图标菜单"""
        super().__init__(page_type=1)
        self.scrollbar = XScrollBar()
        self.title_label = Label(self, '', append_list=False, offset_pos=False)
        self.title_label.pos.y = display_h
        self.others.append(self.title_label)
        self.others.append(self.scrollbar)
        self.others.append(manager.icon_menu_dashline)
        self.camera.w = icon_max_w
        self.x_offset = icon_selector_left_space
        self.y_offset = icon_selector_top_space

    def update(self):
        """更新菜单显示"""
        if self.camera.generator: self.camera.update()
        for child in self.children:
            _pos = child.pos
            _x = _pos.x-self.camera.x+out_gap
            if _pos.generator: _pos.update()
            if  _x>display_w or _x+_pos.w<0: continue
            child.update()
        for other in self.others:
            if other.pos.generator: other.pos.update()
            other.update()

    def change_selection(self, child):
        """
        更改选中项

        Args:
            child: 新的选中项
        """
        self.title_label.set_text(child.title)
        pos = self.title_label.pos
        pos.y = display_h
        pos.x = half_disw - pos.w // 2
        pos.dx = pos.x
        pos.dy = display_h - pos.h - icon_title_bottom
        pos.animation((pos.dx, pos.dy), only_xy=True, ease_func=icon_title_ease)

    def update_camera(self):
        """更新相机位置"""
        pos = manager.selector.selected.pos
        cam = self.camera
        cam.animation((pos.dx-half_disw+pos.w//2, cam.y), camera_speed, only_xy=True, ease_func=camera_ease)

    def add(self, child):
        """
        添加子项到菜单

        Args:
            child: 要添加的子项
        """
        child.parent = self
        child.id = self.count_children
        pos = child.pos
        pos.dx = icon_item_space*self.count_children
        pos.dy = pos.y
        if not expand_ani: pos.x = pos.dx
        self.children.append(child)
        self.count_children += 1

# class Dialog:
#     def __init__(self):
#         # TODO: 一个可以自定义的Dialog组件
#         pass

class TextDialog:
    """
    文本对话框类
    """
    def __init__(self, text: str='', duration=False):
        """
        初始化文本对话框

        Args:
            text: 显示的文本
            duration: 显示持续时间
        """
        # 此类原来应继承于Dialog
        self.type = 'TextDialog'
        self.duration = duration if duration else dialog_default_duration
        self.text = text
        self.pos = Pos()
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
        """
        打开对话框并显示文本

        Args:
            text: 要显示的文本
        """
        self.set_text(text)
        self.pop()

    # @timeit
    def init(self, reset_pos=True):
        """
        初始化对话框

        Args:
            reset_pos: 是否重置位置
        """
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
        """
        设置对话框文本

        Args:
            text: 新的文本内容
        """
        self.text = text
        self.child.set_text(text)
        self.init(False)
        self.animation()

    def animation(self):
        """设置对话框动画"""
        cpos = self.child.pos
        pos = self.pos
        pos.animation((pos.dx, pos.dy), dialog_speed, ease_func=dialog_ease, only_xy=True)
        cpos.animation((cpos.dx, cpos.dy), dialog_speed, ease_func=dialog_ease, only_xy=True)

    # @timeit
    def pop(self):
        """弹出对话框"""
        self.animation()
        self.opening = True
        if not self.appended:
            manager.others.append(self)
            self.appended = True

    # @timeit
    def close(self, _timer=None):
        """关闭对话框"""
        self.closing = True
        self.opened = False
        cpos = self.child.pos
        pos = self.pos
        pos.animation((display_w, dialog_out_gap), dialog_speed, ease_func=dialog_ease, only_xy=True)
        cpos.animation((display_w, dialog_out_gap+dialog_in_gap), dialog_speed, ease_func=dialog_ease, only_xy=True)

    # @timeit
    def update(self):
        """更新对话框显示"""
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
        drawer.round_rect(display, pos.x-2, pos.y-2, pos.w+5, pos.h+5, 0, 1)
        if self.child.pos.generator: self.child.pos.update()
        self.child.update()
        _xw = pos.x+pos.w
        display.fill_rect(_xw-2, pos.y-2, display_w-_xw+2, pos.h+4, 0)
        drawer.round_rect(display, pos.x, pos.y, pos.w, pos.h, 1, 0)

class BaseWidget:
    """
    组件基类
    """
    def __init__(self, parent=None, link=None, add_self:bool=False):
        """
        初始化基础组件

        Args:
            parent: 父组件
        """
        self.parent = parent
        self.pos = Pos()
        self.id = 0
        self.type = -1
        self.link = link
        if add_self: parent.add(self)

class Label(BaseWidget):
    """
    标签组件类
    """
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
        self.type = 0
        self.font = ufont.bitmap_font(font, size)
        self.pos.w = self.font.update_width(text)
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
        self.scroll_w = disw_gap_bar if scroll_w is False else scroll_w
        self.scroll_speed = string_scroll_speed if scroll_speed is False else scroll_speed
        
        # 在启动时加载字体
        if load: manager.load_list.append(self)
        if append_list: parent.add(self)

    def add(self, widget):
        """
        添加子组件

        Args:
            widget: 要添加的组件
        """
        self.link = self.widget_callback
        self.widget = widget

    def init(self):
        """初始化标签，加载字体"""
        # 耗时操作,会在启动时被manager调用加载
        self.pos.w = self.font.init(self.text)

    def widget_callback(self):
        """组件回调函数"""
        self.widget.widget_callback()
        if callable(self.link_): self.link_()

    def set_text(self, text):
        """
        设置标签文本

        Args:
            text: 新的文本内容
        """
        self.text = text
        self.init()
        selector = manager.selector
        if selector.selected is self:
            selector.select(self)

    def scroll_text(self):
        """滚动文本显示"""
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
        """更新标签显示"""
        if self.try_scroll:
            self.scroll_text()
        x, y = self.pos.x, self.pos.y
        if self.offset:
            x, y = manager.current_menu.offset_pos(x, y)
        self.drw(display.blit, self.text, x-self.xscroll, y)
        if self.widget: self.widget.update()

class Icon(BaseWidget):
    """
    图标组件类
    """
    def __init__(self, parent, filepath=None, title='', link=None, append_list: bool=True, offset_pos: bool=True):
        """
        初始化图标组件

        Args:
            parent: 父组件
            filepath: 图片文件路径
            title: 图标标题
            link: 点击回调函数
            append_list: 是否自动添加到父组件
            offset_pos: 是否使用偏移坐标
        """
        super().__init__(parent)
        self.type = 1
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
        """初始化图标，加载图片"""
        # 耗时操作,会在启动时被manager调用加载
        self.pbm.init(self.filepath)

    def set_image(self, filepath):
        """
        设置图标图片

        Args:
            filepath: 新的图片文件路径
        """
        self.filepath = filepath
        self.pbm.init(filepath)

    def update(self):
        """更新图标显示"""
        pos = self.pos
        x, y = pos.x, pos.y
        if self.offset:
            x, y = manager.current_menu.offset_pos(x, y)
        self.drw(display.blit, self.filepath, x, y)

class CheckBox(BaseWidget):
    """
    复选框组件类
    """
    def __init__(self, parent, default=False, link=None, base_x=False):
        """
        初始化复选框

        Args:
            parent: 父组件
            default: 默认值
            link: 回调函数
            base_x: 基础x坐标
        """
        super().__init__(parent)
        self.type = 2
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
        """更新复选框显示"""
        pos = self.pos
        x, y = manager.current_menu.offset_pos(pos.x, pos.y)
        display.fill_rect(x-widget_gap, y-5, disw_wgap-x, list_item_space, 0)  # mask
        display.rect(x, y, pos.w, pos.h, 1)
        if self.value: display.fill_rect(x+2, y+2, pos.w-4, pos.h-4, 1)

    def widget_callback(self):
        """组件回调函数"""
        self.value = not self.value
        if callable(self.link_): self.link_(self.value)

class ListSelect(BaseWidget):
    """
    列表选择器组件类
    """
    def __init__(self, parent, range_list, default_idx: int | bool=False, loop=False,
                 link=None, change_link=None, flash_speed: int | bool=False, base_x=False):
        """
        初始化列表选择器

        Args:
            parent: 父组件
            range_list: 选择范围列表
            default_idx: 默认索引
            loop: 是否循环选择
            link: 回调函数
            change_link: 值改变时的回调函数
            flash_speed: 闪烁速度
            base_x: 基础x坐标
        """
        super().__init__(parent)
        self.type = 3
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
        """更新选择器显示"""
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
        """初始化选择器"""
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
        """
        设置选择器文本

        Args:
            value: 新的值
        """
        self.value = value
        self.child.set_text(str(value))
        self.init()
        if manager.selector.selected is self.parent:
            manager.selector.select(self.parent)

    def widget_callback(self):
        """组件回调函数"""
        self.activate = not self.activate
        self.activate_widget(self.activate)

    def activate_widget(self, status):
        """
        激活/取消激活组件

        Args:
            status: 激活状态
        """
        self.activate = status
        if status:
            self.up, self.down = self._up, self._down
            self.last_time = utime.ticks_ms()
        else:
            self.up, self.down = None, None
            if callable(self.link_): self.link_(self.idx)

    def _down(self):
        """向下选择"""
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
        """向上选择"""
        self.idx += 1
        if self.idx < 0:
            self.idx = 0
            if self.loop: self.idx = self.max_idx
        if self.idx > self.max_idx:
            self.idx = self.max_idx
            if self.loop: self.idx = 0
        self.set_text(self.range_list[self.idx])
        if callable(self.up_): self.up_(self.idx)

class NumSelect(ListSelect):
    """
    数字选择器组件类
    """
    def __init__(self, parent, default_num=0, min_num=0, max_num=10, step=1, loop=False,
                 link=None, change_link=None, flash_speed=False, base_x=False):
        """
        初始化数字选择器

        Args:
            parent: 父组件
            default_num: 默认数字
            min_num: 最小值
            max_num: 最大值
            step: 步长
            loop: 是否循环
            link: 回调函数
            change_link: 值改变时的回调函数
            flash_speed: 闪烁速度
            base_x: 基础x坐标
        """
        self.type = 4
        num_list = [i for i in range(min_num, max_num+1, step)]
        _change_link = change_link
        _link = link
        if callable(change_link): change_link = lambda v: _change_link(num_list[v])
        if callable(link): link = lambda v: _link(num_list[v])
        super().__init__(parent, num_list, num_list.index(default_num), loop, link, change_link, flash_speed, base_x)

class _XDashLine:
    """
    内置水平虚线类
    """
    def __init__(self):
        """初始化虚线"""
        self.type = 5

        self.pos = Pos()  # 所有组件必须拥有Pos
        fbuf = framebuf.FrameBuffer(bytearray(display_w), display_w, 1, framebuf.MONO_VLSB)
        self.drw = fbuf.line
        self.update = lambda: display.blit(fbuf, 0, dashline_h)

        manager.load_list.append(self)

    def init(self):
        """初始化虚线显示"""
        color = 0
        x = 0
        for _ in range(display_w // icon_dashline_split_length):
            to_x = x + icon_dashline_split_length
            self.drw(x, 0, to_x, 0, color)
            x = to_x
            color = not color
        del x, to_x, color
        collect()

def item(parent, *args, **kws) -> "None" | "Label" | "Icon":
    """
    创建项目组件

    Args:
        parent: 父组件
        *args: 位置参数
        **kws: 关键字参数

    Returns:
        创建的组件对象或None
    """
    if isinstance(parent, ListMenu): return Label(parent, *args, **kws)
    elif isinstance(parent, IconMenu): return Icon(parent, *args, **kws)
    else: print('[WARNING] Item: Unknown menu type.')
    return None

display: None
manager: Manager