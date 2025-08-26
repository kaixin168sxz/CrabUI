'''
config file
last edited: 2025.8.15
'''

# 目前的配置有点乱
import math
from micropython import const

# 使用常量(const)来提高性能
# 使用const后，值不可修改

debug = const(True)

# pin config
# 引脚配置

# i2c display
use_i2c = const(True)
hardware_i2c = const(True)
i2c_freq = const(1_000_000)
display_sda = 27
display_scl = 26

# spi display
use_spi = const(False)
hardware_spi = const(1)  # spi id号
spi_freq = const(30_000_000)
display_sck = 14   # d0/scl
display_mosi = 13   # d1/sda
# 4线spi屏幕不需要用的miso,所以只需要设置一个不被占用引脚
display_miso = 12
display_res = 17
display_dc = 16
display_cs = 18

# 按钮对应的引脚
pin_up = 35
pin_down = 34
pin_yes = 39
pin_back = 36

##########################################

# gap config
# 间距配置
out_gap = const(0)
top_gap = const(10)

list_item_gap = const(1)
list_selector_left_gap = const(1)
list_selector_top_gap = const(1)
list_scrollbar_gap = const(2)

icon_item_gap = const(4)
icon_selector_gap = const(1)
icon_dashline_bottom = const(24)
icon_title_bottom = const(0)
icon_scrollbar_gap = const(1)

dialog_out_gap = const(2)
dialog_in_gap = const(3)

widget_gap = const(2)

##########################################

# display config
# 显示器配置
display_w = const(128)
display_h = const(64)

##########################################

# font config
# 字体配置
font_size = const(12)
font_path = 'files/output.bmf'
fbuf_cache = const(False)  # 是否使用framebuffer缓存，而不是bytearray
text_cache = const(True)  # 是否缓存Label的文字
char_cache = const(False) # 是否缓存Label的字符
index_cache = const(False)

##########################################

# menu config
# 菜单配置
menu_loop = const(True)
check_fps = const(True)
icon_size = const(30)
icon_selector_length = const(3)
icon_dashline_split_length = const(3)  # 虚线每一段的长度

xscrollbar_w = const(display_w-out_gap*2)
xscrollbar_h = const(3)
yscrollbar_w = const(5)
yscrollbar_h = const(display_h-top_gap)
dialog_max_w = const(display_w-dialog_out_gap*2-dialog_in_gap)

selector_fill = const(True)  # 是否将选择器填充
# 但是在启用后，会降低性能，并会提高内存占用
# 启用后需要执行异或操作，建议使用c版本的异或运算，可以提升10+fps

##########################################

# startup config
# 启动配置
show_startup_page = const(True)
logo_text = '欢迎使用!'

##########################################

# animation config
# 动画设置
expand_ani = const(True)
base_ani_fps = const(60)   # 动画的最大帧数

# 动画时长

# 在指定帧数内到达目的地
default_speed = const(20)
camera_speed = const(20)
selector_speed = const(16)
expand_speed = const(20)
dialog_speed = const(14)
dialog_default_duration = const(2000) # ms

string_scroll_speed = const(2)  # px(速度:像素)
widget_flash_speed = const(250) # 闪烁间隙(当子控件被激活时) ms(时间:毫秒)

# 动画函数 (https://easings.net)
# x取值0~1之间的浮点数
def ease_out_circ(x):
    return math.sqrt(1 - math.pow(x - 1, 2))

c1 = 1.70158
c2 = c1 * 1.525

def ease_in_out_back(x):
    return (math.pow(2 * x, 2) * ((c2 + 1) * 2 * x - c2)) / 2 if x < 0.5 else \
           (math.pow(2 * x - 2, 2) * ((c2 + 1) * (x * 2 - 2) + c2) + 2) / 2

camera_ease = ease_in_out_back
selector_ease = ease_in_out_back
icon_expand_ease = ease_out_circ
list_expand_ease = ease_out_circ
default_ease = ease_in_out_back
scrollbar_ease = ease_in_out_back
icon_title_ease = ease_in_out_back
dialog_ease = ease_in_out_back

##########################################

# builtin values
# 内部值
# ! WARNING: BUILTIN VALUES, PLEASE DO NOT EDIT THEM!
# ! 警告：内部常量, 请勿修改!
# 整个项目最难的部分 ↓

half_disw = const(display_w//2)
half_dish = const(display_h//2)
half_font_size = const(font_size//2)
display_fb_size = const((display_h+7)//8*display_w)

disw_gap_bar = const(display_w-out_gap-yscrollbar_w-list_scrollbar_gap)
dish_gap = const(display_h-top_gap)
right_mask_x = const(display_w-out_gap)

list_space = const(list_item_gap+list_selector_top_gap+1)
list_item_space = const(font_size+list_space)
half_list_item_space = const(list_item_space//2)
list_selector_left_space = const(list_selector_left_gap+out_gap)
list_selector_top_space = const(top_gap+list_selector_top_gap+1)   # 1是选择器的高度

xscrollbar_space = const(xscrollbar_h+icon_scrollbar_gap)
icon_item_space = const(icon_size+icon_item_gap)
icon_selector_left_space = const(icon_selector_gap+out_gap)
icon_selector_top_space = const(icon_selector_gap+top_gap+1+xscrollbar_space)   # 1是选择器的高度
dashline_h = const(display_h-icon_dashline_bottom+top_gap)

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
xscrollbar_mask_h = const(xscrollbar_h)

dialog_base_x = const(display_w-dialog_in_gap*2-dialog_out_gap-2)  # TextDialog的基础x坐标, -2是因为弹窗矩形两条边框各占用1像素
dialog_in_gap_m2 = const(dialog_in_gap*2)
dialog_max_x = const(dialog_base_x-dialog_max_w+dialog_in_gap_m2)
widget_gap_m2 = const(widget_gap*2)
disw_wgap = const(display_w+widget_gap)

base_ani_sleep = const(1000//base_ani_fps)  # ms

##########################################
