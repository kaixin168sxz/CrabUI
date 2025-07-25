'''
define apis
last edited: 2025.7.24
'''

# 默认使用Esp32Api
# 如果你使用Esp32或任何与Esp32 MicropythonApi相同的MCU，你不需要修改此文件
# 如需移植，仅需修改函数内容

from machine import I2C, Pin, Timer, SPI

# api接口映射
# CrabUI使用api名称 = mcu使用api名称
# CrabUI会传入Esp32Api所使用的参数规范，如需修改，请参阅GithubWiki的移植页面

I2C = I2C
Pin = Pin
Timer = Timer
SPI = SPI