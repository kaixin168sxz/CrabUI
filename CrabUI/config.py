'''
config file
last edited: 2025.7.25
'''

# 目前的配置有点乱

from micropython import const
import math
# 使用常量(const)来提高性能

debug = const(True)

# pin config
# 引脚配置

# i2c display
use_i2c = const(False)
hardware_i2c = const(True)
i2c_freq = const(1_000_000)
display_sda = 21
display_scl = 22

# spi display
use_spi = const(True)
hardware_spi = const(2)
spi_freq = const(30_000_000)
display_sck = 18   # d0
display_mosi = 8   # d1
# 一般来说miso应该为0(如果不被占用的话),4线spi屏幕(d0, d1, res, dc, cs)不需要用的miso,所以只需要设置一个不被占用引脚
display_miso = 0
display_res = 9
display_dc = 10
display_cs = 11

pin_up = 7
pin_down = 6
pin_yes = 5
pin_back = 4

##########################################

# gap config
# 间距配置
out_gap = const(0)
top_gap = const(10)

list_item_gap = const(2)
list_selector_left_gap = const(2)
list_selector_top_gap = const(1)
list_scrollbar_gap = const(5)

icon_item_gap = const(4)
icon_selector_gap = const(1)
icon_dashline_bottom = const(20)
icon_title_bottom = const(2)
icon_scrollbar_gap = const(2)

dialog_out_gap = const(2)
dialog_in_gap = const(5)

widget_gap = const(2)

##########################################

# display config
# 显示器配置
display_w = const(128)
display_h = const(64)
half_disw = const(display_w//2)

##########################################

# font config
# 字体配置
font_size = const(16)
half_font_size = const(8)
driver_enfont_w = const(8)  # framebuf原生显示的字体宽度
driver_enfont_h = const(8)  # framebuf原生显示的字体高度
font_path = 'files/font.bmf'

##########################################

# menu config
# 菜单配置
menu_loop = const(True)
btn_sleep_time = const(200)   # ms
check_fps = const(True)
icon_size = const(30)
icon_selector_length = const(4)
icon_dashline_split_length = const(3)  # 虚线每一段的长度

xscrollbar_w = const(display_w-out_gap*2)
xscrollbar_h = const(5)
yscrollbar_w = const(5)
yscrollbar_h = const(display_h-top_gap)

dialog_max_w = const(display_w-dialog_in_gap*2-dialog_out_gap-2)

##########################################

# startup config
# 启动配置
show_startup_page = const(True)
logo_text = 'CrabUI'
logo_length = len(logo_text)*driver_enfont_w

##########################################

# animation config
# 动画设置
stop_last_ani = const(True)
expand_ani = const(True)

# 动画时长

# 在指定帧数内到达目的地
default_speed = const(40)
camera_speed = const(23)
selector_speed = const(40)
expand_speed = const(20)
dialog_speed = const(40)

string_scroll_speed = const(1)  # px(速度:像素)
widget_flash_speed = const(250) # 闪烁间隙(当子控件被激活时) ms(时间:毫秒)

# 动画函数 (https://easings.net)
# x取值0~1之间的浮点数
def ease_out_quad(x):
    return 1 - (1 - x) ** 2

c4 = (2 * math.pi) / 3  # 下面动画函数用的，如果更换了动画函数，可能可以删除
def ease_out_elastic(x):
    return 0 if x==0 else 1 if x==1 else math.pow(2, -10 * x) * math.sin((x * 10 - 0.75) * c4) + 1

def ease_out_circ(x):
    return math.sqrt(1 - math.pow(x - 1, 2))

camera_ease = ease_out_quad
selector_ease = ease_out_elastic
expand_ease = ease_out_quad
default_ease = ease_out_quad
scrollbar_ease = ease_out_elastic
icon_title_ease = ease_out_circ
dialog_ease = ease_out_circ

##########################################

# builtin values
# 内部值
# ! WARNING: BUILTIN VALUES, PLEASE DO NOT EDIT THEM!
disw_gap_bar = const(display_w-out_gap-yscrollbar_w-list_scrollbar_gap)
dish_gap = const(display_h-top_gap)
right_mask_x = const(display_w-out_gap)

xscrollbar_space = const(xscrollbar_h+icon_scrollbar_gap)
list_space = const(list_item_gap+list_selector_top_gap)
list_item_space = const(font_size+list_space)
half_list_item_space = const(list_item_space//2)
list_selector_space = const(list_selector_left_gap+out_gap)
icon_item_space = const(icon_size+icon_item_gap)
icon_selector_left_space = const(icon_selector_gap+out_gap)
icon_selector_top_space = const(icon_selector_gap+top_gap+1+xscrollbar_space)   # 1是选择器的高度
dashline_h = const(display_h-icon_dashline_bottom)

list_max_w = const(disw_gap_bar-out_gap)
list_max_h = const(display_h-top_gap)
icon_max_w = const(display_w-out_gap*2)

yscrollbar_x = const(right_mask_x-yscrollbar_w)
yscrollbar_line_yh = const(top_gap+yscrollbar_h)
yscrollbar_line_x = const(yscrollbar_x+yscrollbar_w//2)
yscrollbar_line_xw = const(yscrollbar_x+yscrollbar_w)
yscrollbar_mask_x = const(yscrollbar_x-list_scrollbar_gap)
yscrollbar_mask_w = const(yscrollbar_w+list_scrollbar_gap)
yscrollbar_bottom_line_y = const(yscrollbar_line_yh-1)

xscrollbar_mask_y = const(top_gap-icon_scrollbar_gap)
xscrollbar_mask_h = const(xscrollbar_h+list_scrollbar_gap)

dialog_base_x = const(display_w-dialog_in_gap*2-dialog_out_gap-2)  # TextDialog的基础x坐标, -2是因为TextDialog的两条矩形边框各占用1像素
dialog_in_gap_m2 = const(dialog_in_gap*2)
dialog_max_x = const(dialog_base_x-dialog_max_w)

##########################################