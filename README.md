# 本项目已迁移至 [CrabUI-oled](https://github.com/kaixin1106/CrabUI-oled)

# 本项目已迁移至 [CrabUI-oled](https://github.com/kaixin1106/CrabUI-oled)

# 本项目已迁移至 [CrabUI-oled](https://github.com/kaixin1106/CrabUI-oled)

# CrabUI

> A smooth ui framework in micropython.

# [Wiki](https://github.com/kaixin168sxz/CrabUI/wiki)

# 注意事项
## 配置文件

*配置文件(`config.py`)中定义了`CrabUI`的行为*

**在使用前请修改配置文件：**
1. 将屏幕的宽高改为你屏幕的宽高（**单位：像素**）
2. 将`selector_fill`（填充选择器）设为`False`（这一点见 [wiki说明]()）
3. 如果使用的是较旧版本(2025.10.6之前的版本)，请在配置文件中按照自己的实际情况修改引脚配置

## 新版使用说明

**如果需要完整示例代码，见 [wiki的新版教程]()**

**如果使用较新的版本(*2025.10.6之后的版本*)，请在您的项目中手动指定显示器并手动绑定按钮事件，详见如下：**

*关于为什么要在新版中作出修改，见 [wiki的Q&A部分]()*

1. 在**您的项目**中导入并初始化屏幕的驱动程序，如（**此处仅为示例**）:

```python
import ssh1106
from machine import SPI, Pin

# 根据实际情况修改引脚内容
spi = SPI(1, mosi=Pin(13), miso=Pin(12), sck=Pin(14), baudrate=30_000_000)
display = ssh1106.SSH1106_SPI(128, 64, spi, Pin(16), Pin(17), Pin(18), 180)
```

2. 在初始化`ui.Manager`后，手动绑定按钮事件

```python
...

manager = ui.Manager()
btn_evnet = manager.btn_event
# 这里的数字是按钮的引脚号
btn_evnet.add(35, manager.up)    # 向上的按钮
btn_evnet.add(34, manager.down)  # 向下的按钮
btn_evnet.add(39, manager.yes)   # 确认的按钮
btn_evnet.add(36, manager.back)  # 返回的按钮
```
