# SPDX-License-Identifier: Apache-2.0
"""Tapper — a dependency-free Windows mouse auto clicker."""
import ctypes
from ctypes import wintypes
import math
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont


def interval_seconds(value, unit):
    value = float(value)
    seconds = value / 1000 if unit == 'ms' else value if unit == 's' else value * 60
    if not math.isfinite(seconds) or not 0.01 <= seconds <= 120:
        raise ValueError('Interval must be between 10 ms and 120 seconds')
    return seconds


class MouseInput(ctypes.Structure):
    _fields_ = [('dx', wintypes.LONG), ('dy', wintypes.LONG),
                ('mouseData', wintypes.DWORD), ('dwFlags', wintypes.DWORD),
                ('time', wintypes.DWORD), ('dwExtraInfo', ctypes.c_size_t)]


class InputUnion(ctypes.Union):
    _fields_ = [('mi', MouseInput), ('padding', ctypes.c_byte * (32 if ctypes.sizeof(ctypes.c_void_p) == 8 else 24))]


class Input(ctypes.Structure):
    _anonymous_ = ('data',)
    _fields_ = [('type', wintypes.DWORD), ('data', InputUnion)]


class WindowsMouse:
    def __init__(self):
        self.hold_seconds = 0.15
        self.api = ctypes.WinDLL('user32', use_last_error=True)
        self.api.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int]
        self.api.SendInput.restype = wintypes.UINT
        self.api.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self.api.GetAsyncKeyState.restype = ctypes.c_short

    def click(self, button):
        down, up = {'left': (2, 4), 'right': (8, 16), 'middle': (32, 64)}[button]
        if self.hold_seconds == 0:
            events = (Input * 2)(Input(type=0, mi=MouseInput(dwFlags=down)),
                                 Input(type=0, mi=MouseInput(dwFlags=up)))
            if self.api.SendInput(2, events, ctypes.sizeof(Input)) != 2:
                release = Input(type=0, mi=MouseInput(dwFlags=up))
                self.api.SendInput(1, ctypes.byref(release), ctypes.sizeof(Input))
                raise OSError('Windows blocked simulated input')
            return
        press = Input(type=0, mi=MouseInput(dwFlags=down))
        release = Input(type=0, mi=MouseInput(dwFlags=up))
        try:
            if self.api.SendInput(1, ctypes.byref(press), ctypes.sizeof(Input)) != 1:
                raise OSError('Windows blocked simulated input')
            time.sleep(self.hold_seconds)
        finally:
            if self.api.SendInput(1, ctypes.byref(release), ctypes.sizeof(Input)) != 1:
                # Retry release once before reporting failure.
                self.api.SendInput(1, ctypes.byref(release), ctypes.sizeof(Input))
                raise OSError('Windows blocked mouse release')

    def pressed(self, key):
        return bool(self.api.GetAsyncKeyState(key) & 0x8000)


class Clicker:
    def __init__(self, mouse):
        self.mouse = mouse
        self.stop_event = threading.Event()
        self.thread = None
        self.count = 0
        self.error = None

    @property
    def running(self):
        return self.thread is not None and self.thread.is_alive()

    def start(self, interval, button, immediate=False):
        if self.running:
            return
        interval = max(interval, 2 * getattr(self.mouse, 'hold_seconds', 0))
        self.stop_event.clear()
        self.count = 0
        self.error = None
        self.thread = threading.Thread(target=self._run, args=(interval, button, immediate), daemon=True)
        self.thread.start()

    def _run(self, interval, button, immediate):
        deadline = time.perf_counter() + (0 if immediate else interval)
        try:
            while not self.stop_event.wait(max(0, deadline - time.perf_counter())):
                self.mouse.click(button)
                self.count += 1
                # Skip missed slots; never send catch-up bursts.
                deadline = max(deadline + interval, time.perf_counter() + getattr(self.mouse, 'hold_seconds', 0))
        except Exception as exc:
            self.error = str(exc)

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1)


TEXT = {
    'zh': dict(sub='简单、精准，按你的节奏点击。', settings='点击设置', interval='点击间隔',
               range='支持 10 毫秒 – 120 秒 · 最高每秒 100 次', button='鼠标按键',
               left='左键', right='右键', middle='中键', start='按下后3秒开始', stop='停止连点', countdown='取消倒计时（{seconds}）',
               waiting='{seconds} 秒后开始',
               ready='准备就绪', running='正在连点', count='本次点击',
               hint='按任意键停止 · 倒计时期间也可取消',
               tip='点击跟随当前鼠标位置。请在 3 秒倒计时内移到目标区域。',
               footer='Apache 2.0  ·  Windows  ·  F11 全屏 / Esc 退出全屏',
               invalid='请输入 10 毫秒至 120 秒之间的有效数字。',
               failed='点击失败：Windows 可能阻止向高权限窗口发送输入。',rate='每秒约 {rate:g} 次 · 每 {seconds:g} 秒一次'),
    'en': dict(sub='Simple clicks. Your pace.', settings='Click settings', interval='Click interval',
               range='10 milliseconds – 120 seconds · Up to 100 clicks/sec', button='Mouse button',
               left='Left', right='Right', middle='Middle', start='Start after 3 seconds', stop='Stop clicking', countdown='Cancel countdown ({seconds})',
               waiting='Starting in {seconds} sec',
               ready='Ready', running='Clicking', count='Clicks this session',
               hint='Press any key to stop · Also cancels the countdown',
               tip='Clicks follow your cursor. Move to the target during the 3-second countdown.',
               footer='Apache 2.0  ·  Windows  ·  F11 Fullscreen / Esc Exit',
               invalid='Enter a valid interval between 10 ms and 120 seconds.',
               failed='Click failed: Windows may block input to elevated windows.',rate='About {rate:g} clicks/sec · Every {seconds:g} sec')
}


class App:
    def __init__(self, root):
        self.root = root
        self.engine = Clicker(WindowsMouse())
        self.lang = 'zh'
        self.start_at = None
        self.pending_settings = None
        self.poll_id = None
        self.fonts = []
        self.display_scale = max(1.0, float(root.tk.call('tk', 'scaling')) / (96 / 72))
        root.option_add('*Font', self.font(11))
        root.title('Tapper')
        width = min(round(720 * self.display_scale), root.winfo_screenwidth() - 80)
        height = min(round(720 * self.display_scale), root.winfo_screenheight() - 120)
        root.geometry(f'{max(640, width)}x{max(640, height)}')
        root.minsize(640, 640)
        root.configure(bg='#edf4ff')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TCombobox', padding=7, font=self.font(11))
        self.bindings = []
        outer = tk.Frame(root, bg='#edf4ff')
        outer.pack(fill='both', expand=True, padx=24, pady=16)
        header = tk.Frame(outer, bg='#edf4ff')
        header.pack(fill='x')
        tk.Label(header, text='Tapper', font=self.font(26, bold=True), fg='#185adb', bg='#edf4ff').pack(side='left')
        tk.Button(header, text='中文 / EN', command=self.switch_language, bg='white', fg='#185adb', relief='flat', padx=14, pady=8).pack(side='right')
        self.label(outer, 'sub', bg='#edf4ff').pack(anchor='w', pady=(0, 10))
        controls = tk.Frame(outer, bg='white', padx=20, pady=12)
        controls.pack(side='bottom', fill='x', pady=(12, 0))
        card = tk.Frame(outer, bg='white', padx=20, pady=14)
        card.pack(fill='both', expand=True)
        self.label(card, 'settings', font=self.font(17, bold=True)).pack(anchor='w')
        self.label(card, 'interval').pack(anchor='w', pady=(10, 5))
        row = tk.Frame(card, bg='white')
        row.pack(fill='x')
        self.value = tk.StringVar(value='100')
        self.unit = tk.StringVar(value='ms')
        self.entry = ttk.Entry(row, textvariable=self.value, font=self.font(20))
        self.entry.pack(side='left', fill='x', expand=True)
        self.units = ttk.Combobox(row, textvariable=self.unit, values=['ms', 's', 'min'], state='readonly', width=6)
        self.units.pack(side='left', padx=(12, 0))
        self.compatible = tk.BooleanVar(value=True)
        tk.Checkbutton(card, text='BongoCat: 150 ms 按住 / hold (≤ 3.33 clicks/s)', variable=self.compatible, bg='white', command=self.update_rate).pack(anchor='w')
        self.label(card, 'range', fg='#6c7b92', font=self.font(10)).pack(anchor='w', pady=(7, 0))
        self.rate = tk.Label(card, bg='white', fg='#185adb', anchor='w')
        self.rate.pack(fill='x', pady=(6, 0))
        self.label(card, 'button').pack(anchor='w', pady=(10, 5))
        buttons = tk.Frame(card, bg='white')
        buttons.pack(fill='x')
        self.button = tk.StringVar(value='left')
        self.radios = []
        for key in ('left', 'right', 'middle'):
            radio = tk.Radiobutton(buttons, variable=self.button, value=key, bg='white', fg='#243956', selectcolor='#e1edff', font=self.font(12))
            self.bindings.append((radio, key))
            self.radios.append(radio)
            radio.pack(side='left', expand=True)
        self.action = tk.Button(controls, command=self.toggle, bg='#185adb', fg='white', activebackground='#1246aa', activeforeground='white', relief='flat', font=self.font(14, bold=True), pady=8, cursor='hand2')
        self.action.pack(fill='x', pady=(12, 6))
        self.label(controls, 'hint', fg='#185adb', font=self.font(11)).pack()
        self.status = tk.Label(controls, bg='white', fg='#536985', font=self.font(11))
        self.status.pack(pady=(7, 0))
        self.message = tk.Label(controls, bg='white', fg='#bd334d', wraplength=500)
        self.message.pack(fill='x', pady=(5, 0))
        self.label(controls, 'tip', bg='white', font=self.font(10), wraplength=560).pack(pady=(10, 5))
        self.label(controls, 'footer', bg='white', font=self.font(9), fg='#6c7b92').pack()
        self.value.trace_add('write', lambda *_: self.update_rate())
        self.unit.trace_add('write', lambda *_: self.update_rate())
        root.bind('<F11>', lambda _: root.attributes('-fullscreen', not root.attributes('-fullscreen')))
        root.bind('<Escape>', lambda _: root.attributes('-fullscreen', False))
        root.bind_all('<KeyPress>', self.on_key, add='+')
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.bind('<Configure>', self.resize_fonts, add='+')
        self.translate()
        self.poll()

    def font(self, points, bold=False):
        # Negative Tk font sizes are pixels, independent of Windows DPI.
        pixels = round(points * 96 / 72)
        font = tkfont.Font(root=self.root, family='Segoe UI', size=-pixels,
                           weight='bold' if bold else 'normal')
        self.fonts.append((font, pixels))
        return font

    def resize_fonts(self, event):
        if event.widget != self.root:
            return
        scale = max(1.0, min(self.display_scale, event.width / 720, event.height / 720))
        for font, pixels in self.fonts:
            size = -round(pixels * scale)
            if font.cget('size') != size:
                font.configure(size=size)

    def label(self, parent, key, **kwargs):
        options = dict(bg='white', fg='#243956', font=self.font(12))
        options.update(kwargs)
        widget = tk.Label(parent, **options)
        self.bindings.append((widget, key))
        return widget

    def switch_language(self):
        self.lang = 'en' if self.lang == 'zh' else 'zh'
        self.message.config(text='')
        self.translate()

    def translate(self):
        for widget, key in self.bindings:
            widget.config(text=TEXT[self.lang][key])
        self.update_rate()
        self.update_status()

    def update_rate(self):
        try:
            seconds = interval_seconds(self.value.get(), self.unit.get())
            if self.compatible.get():
                seconds = max(seconds, 0.30)
            self.rate.config(text=TEXT[self.lang]['rate'].format(rate=1 / seconds, seconds=seconds))
        except ValueError:
            self.rate.config(text='—')

    def toggle(self):
        if self.engine.running or self.start_at is not None:
            self.stop()
        else:
            try:
                interval = interval_seconds(self.value.get(), self.unit.get())
            except ValueError:
                self.message.config(text=TEXT[self.lang]['invalid'])
                return
            self.message.config(text='')
            self.engine.error = None
            self.engine.count = 0
            self.engine.mouse.hold_seconds = 0.15 if self.compatible.get() else 0
            self.pending_settings = (interval, self.button.get())
            self.start_at = time.perf_counter() + 3
            # Remove focus from the button: Space/Enter must only stop.
            self.root.focus_set()
        self.update_status()

    def stop(self):
        self.start_at = None
        self.pending_settings = None
        self.engine.stop()

    def on_key(self, event):
        if self.start_at is not None or self.engine.running:
            self.stop()
            self.update_status()
            return 'break'

    def update_status(self):
        running = self.engine.running
        waiting = self.start_at is not None
        active = running or waiting
        t = TEXT[self.lang]
        seconds = max(1, math.ceil(self.start_at - time.perf_counter())) if waiting else 0
        self.action.config(text=t['countdown'].format(seconds=seconds) if waiting else t['stop' if running else 'start'])
        state = t['waiting'].format(seconds=seconds) if waiting else t['running' if running else 'ready']
        self.status.config(text=f"● {state}    ·    {t['count']}: {self.engine.count:,}")
        self.entry.config(state='disabled' if active else 'normal')
        self.units.config(state='disabled' if active else 'readonly')
        for radio in self.radios:
            radio.config(state='disabled' if active else 'normal')

    def poll(self):
        if self.poll_id is not None:
            self.root.after_cancel(self.poll_id)
            self.poll_id = None
        # VK 1–6 are mouse buttons; keyboard keys begin at VK_BACK (8).
        # Check globally, including when another application's window has focus.
        if self.start_at is not None or self.engine.running:
            if any(self.engine.mouse.pressed(key) for key in range(8, 255)):
                self.stop()
            elif self.start_at is not None and time.perf_counter() >= self.start_at:
                interval, button = self.pending_settings
                self.start_at = None
                self.pending_settings = None
                self.engine.start(interval, button, immediate=True)
        if self.engine.error:
            self.message.config(text=TEXT[self.lang]['failed'])
        self.update_status()
        self.poll_id = self.root.after(10, self.poll)

    def close(self):
        self.stop()
        if self.poll_id is not None:
            self.root.after_cancel(self.poll_id)
            self.poll_id = None
        self.root.update_idletasks()
        self.root.destroy()


def main():
    if sys.platform != 'win32':
        raise SystemExit('Tapper currently supports Windows only.')
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (OSError, AttributeError):
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
