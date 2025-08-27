import DevCrabUI as ui
import oled

manager = ui.Manager(oled)
root = ui.ListMenu()
ui.item(root, 'HelloWorld')
manager.page(root)

while True:
    manager.update()