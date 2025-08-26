import CrabUI as ui
from machine import I2S, Pin, Timer
import urequests
import network
import time
import re
import gc
import struct
import random
import oled
from machine import freq
import esp32

freq(240000000)
print(freq())
print(gc.mem_alloc())

print(gc.mem_alloc())

sck_pin = Pin(33)  # BCLK
ws_pin  = Pin(32)  # LRC
sd_pin  = Pin(25)   # DIN

def init_audio(rate, bits):
    global music_bits
    music_bits = bits
    return I2S(0, sck=sck_pin, ws=ws_pin, sd=sd_pin, 
              mode=I2S.TX, bits=bits, format=I2S.MONO, 
              rate=rate, ibuf=20000)

audio_out = init_audio(48000, 32)
 
def do_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect('TP-LINK_9DE0_2G', 'sxz588*KXsj068S$s')  # WIFI名字密码
        i = 1
        while not wlan.isconnected():
            print("正在连接中...{}".format(i))
            i += 1
            time.sleep(1)
    print('network config:', wlan.ifconfig())
do_connect()

def findall(pattern, string):
    while True:
        match = re.search(pattern, string)
        if not match:
            break
        res = match.group(0)
        yield res
        string = string[string.find(res)+len(res):]
def get_music_list():
    response = urequests.get('http://192.168.0.108:666/EspMusic/')
    res = findall(r'</td><td><a href=".*?">(.*?)\.wav</a></td>', response.text)
    response.close()
    return {'.wav'.join(i.split('.wav')[1:-1])[2:]:i.split('</td><td>')[-1].split('<a href="')[1].split('">')[0] for i in res}

music_list = get_music_list()
response = None
play = True
shift = 7
music_bits = 16
playing = None
mode = 0

def change_music(name, display_dia=True):
    global response, audio_out, playing, play
    if display_dia: dia.open('播放中')
    playing = name
    if response:
        response.close()
        response = None
    
    response = urequests.get(f"http://192.168.0.108:666/EspMusic/{music_list[name]}", stream=True)
    header = response.raw.read(44)
    # 读取头文件
    if len(header) < 44:
        raise ValueError("Received less than 44 bytes from the WAV file")

    # Continue with unpacking the header as before
    riff, size, fformat = struct.unpack('<4sI4s', header[:12])
    fmt, length, format_type, channels, rate, byte_rate, block_align, bits = struct.unpack('<4sIHHIIHH', header[12:36])
    list_id, list_size = struct.unpack('<4sI', header[36:44])
    # 打印出来
    print('Now playing:', name)
    print('rate: ', rate)
    print('bits: ', bits)
    print('-'*15)
    music_title.set_text(name)
    audio_out.deinit()
    audio_out = init_audio(rate, bits)
    play = True

def toggle():
    global play
    if not response:
        dia.open('未播放音乐')
        return 
    play = not play
    dia.open({False: '已暂停', True: '正在播放'}[play])
    toggle_label.set_text({False: '继续播放', True: '暂停播放'}[play])

def set_shift(v):
    global shift
    shift = v

def change_mode(v):
    global mode
    mode = v
    dia.open('已修改模式')

manager = ui.Manager(oled)
root = ui.ListMenu()
dia = ui.TextDialog()
music_title = ui.Item(root, '无音乐', link=lambda: manager.page(music_menu))
# ui.Item(root, '音乐列表', link=lambda: manager.page(music_menu))
toggle_label = ui.Item(root, '暂停播放', link=toggle)
shift_label = ui.Item(root, '播放音量')
ui.NumberSelector(shift_label, 7, 0, 10, 1, True, change_link=set_shift, link=lambda n: dia.open('已修改音量'))

mode_label = ui.Item(root, '模式')
ui.ListSelector(mode_label, ['播完暂停', '单曲循环', '随机播放'], 0, True, link=change_mode)

music_menu = ui.ListMenu()
for i in music_list.keys():
    ui.Item(music_menu, i, link=lambda n=i: change_music(n))

manager.page(root)
Timer(1, period=35, callback=manager.update)

buffer_view = memoryview(bytearray(3072))
while True:
#     print(esp32.hall_sensor())     # 读取内部霍尔传感器
#     print(esp32.raw_temperature()) # 读取内部温度传感器，在MCU上, 单位：华氏度F
    if not response and play and playing:
        if not mode:
            play = False
            time.sleep(0.5)
            continue
        if mode == 1: change_music(playing, False)
        else:
            _playing = playing
            while playing == _playing:
                playing = random.choice(list(music_list.keys()))
            change_music(playing, False)
        play = True
    elif not (play and response):
        time.sleep(0.5)
        gc.collect()
        continue

    while True:
        if not play: break
        bytes_read = response.raw.readinto(buffer_view)
        if not bytes_read:
            if response: response.close()
            response = None
            gc.collect()  # 回收内存
            break
#         print(esp32.hall_sensor())     # 读取内部霍尔传感器
#         print(esp32.raw_temperature()) # 读取内部温度传感器，在MCU上, 单位：华氏度F
        data_view = buffer_view[:bytes_read]
        audio_out.shift(buf=data_view, bits=music_bits, shift=shift-10)
        audio_out.write(data_view)