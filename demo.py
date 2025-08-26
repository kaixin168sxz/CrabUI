import DevCrabUI as ui
import oled
import gc
from machine import freq

freq(240000000)
print(freq())
print(gc.mem_alloc())

manager = ui.Manager(oled)
root = ui.ListMenu()

dis = manager.display
dis.contrast(255)

dia = ui.TextDialog('?')
ui.item(root, f'CrabUI v{ui.__version__}', link=lambda: dia.open('nothing'))

ui.item(root, '基于Micropython', link=lambda: dia.open('nothing'))
aa = ui.item(root, '点赞投币收藏', link=lambda: dia.open('还有关注'))
ui.CheckBox(aa)
ui.item(root, 'CrabUI是一个流畅丝滑的ui框架，基于micropython。', link=lambda: dia.open('nothing'))

ui.item(root, 'Copyright 版权声明 (c) 2025 kaixin168sxz(kaixin1106)')
b = ui.item(root, '修改显示器亮度')
light = [10, 50, 100, 200, 255]
ui.ListSelector(b, light, default_idx=4, loop=True, change_link=lambda v:dis.contrast(light[v]),
                link=lambda v:dia.open('已修改亮度'))
ui.item(root, 'Page2', link=lambda: manager.page(page2))
ui.item(root, '基于Micropython!', link=lambda: dia.open('nothing'))
ui.item(root, '最后一项', link=lambda: dia.open('nothing'))

page2 = ui.IconMenu()
ui.item(page2, 'files/a.pbm', '空')
ui.item(page2, 'files/b.pbm', '页面3', link=lambda: manager.page(page3))

page3 = ui.IconMenu()
ui.item(page3, 'files/b.pbm', '自定义页面', link=lambda: manager.page(page4))
ui.item(page3, 'files/b.pbm', '测试选项')
ui.item(page3, 'files/b.pbm', '选项3')
ui.item(page3, 'files/a.pbm')
ui.item(page3, 'files/a.pbm')
ui.item(page3, 'files/a.pbm')
ui.item(page3, 'files/b.pbm')
ui.item(page3, 'files/b.pbm', '最后一个')

n = False
def xxx():
    global n
    xx.pos.animation((0, {False:40, True:20}[n]), only_xy=True)
    nn.pos.animation(({False:80, True:40}[n], 0), only_xy=True)
    n = not n

page4 = ui.Page(yes=xxx)

xx = ui.Label(page4, '一个自定义的页面')
xx.pos.dy = 20
xx.pos.dx = 10

nn = ui.Label(page4, 'hello')
nn.pos.dx = 40

manager.page(root)
while True:
    manager.update()
#     gc.collect()
#     print(gc.mem_alloc())
