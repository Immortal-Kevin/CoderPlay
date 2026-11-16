# SPDX-License-Identifier: Apache-2.0
"""Windows VK typing companion; the original browser draft remains unchanged."""
import ctypes as c
from ctypes import wintypes as w
import random,time,os,tkinter as tk
from tkinter import ttk
class KeyboardInput(c.Structure):
 _fields_=[('wVk',w.WORD),('wScan',w.WORD),('dwFlags',w.DWORD),('time',w.DWORD),('dwExtraInfo',c.c_size_t)]
class Data(c.Union):
 _fields_=[('ki',KeyboardInput),('padding',c.c_byte*(32 if c.sizeof(c.c_void_p)==8 else 24))]
class Input(c.Structure):
 _anonymous_=('data',)
 _fields_=[('type',w.DWORD),('data',Data)]
class WindowsKeyboard:
 def __init__(self):
  self.api=c.WinDLL('user32',use_last_error=True)
  self.api.SendInput.argtypes=[w.UINT,c.POINTER(Input),c.c_int];self.api.SendInput.restype=w.UINT
  self.api.GetAsyncKeyState.argtypes=[c.c_int];self.api.GetAsyncKeyState.restype=c.c_short
  self.owned=set()
 def send(self,vk,up=False):
  event=Input(type=1,ki=KeyboardInput(wVk=vk,dwFlags=2 if up else 0))
  if self.api.SendInput(1,c.byref(event),c.sizeof(Input))!=1:raise OSError('Windows blocked keyboard input (check target integrity level)')
  if up:self.owned.discard(vk)
  else:self.owned.add(vk)
 def release(self):
  for vk in tuple(self.owned):
   try:self.send(vk,True)
   except OSError:self.send(vk,True)
 def pressed(self,vk):return bool(self.api.GetAsyncKeyState(vk)&0x8000)
class App:
 def __init__(self,root):
  self.root=root;self.keyboard=WindowsKeyboard();self.active=False;self.timer=None;self.poll=None;self.count=0
  root.title('Typper — Windows 输入模式');root.geometry('800x650');root.configure(bg='#edf4ff')
  outer=tk.Frame(root,bg='#edf4ff',padx=24,pady=20);outer.pack(fill='both',expand=True)
  tk.Label(outer,text='Typper',font=('Segoe UI',26,'bold'),fg='#185adb',bg='#edf4ff').pack(anchor='w')
  tk.Label(outer,text='Windows 系统键入 · 随机 a–z / 0–9 · F12 全局紧急停止',bg='#edf4ff').pack(anchor='w',pady=12)
  self.low=tk.StringVar(value='0.3');self.high=tk.StringVar(value='1')
  for text,var in [('最小间隔（秒）',self.low),('最大间隔（秒）',self.high)]:
   tk.Label(outer,text=text,bg='#edf4ff').pack(anchor='w');ttk.Entry(outer,textvariable=var).pack(fill='x',pady=5)
  self.external=tk.BooleanVar(value=False)
  tk.Checkbutton(outer,text='向倒计时后有焦点的其他应用键入（默认输入下方草稿）',variable=self.external,bg='#edf4ff').pack(anchor='w',pady=8)
  self.button=tk.Button(outer,text='三秒后开始 / Start',command=self.toggle,bg='#185adb',fg='white');self.button.pack(fill='x')
  self.message=tk.StringVar(value='BongoCat 模式：按住 150 ms，释放至少 150 ms；最快 3.33 次/秒。')
  tk.Label(outer,textvariable=self.message,bg='#edf4ff',wraplength=700).pack(pady=12)
  self.draft=tk.Text(outer,font=('Consolas',14),undo=True);self.draft.pack(fill='both',expand=True)
  root.protocol('WM_DELETE_WINDOW',self.close);self.check_stop()
 def toggle(self):
  if self.active:self.stop();return
  try:
   low,high=float(self.low.get()),float(self.high.get())
   if not 1/30<=low<=high<=300:raise ValueError()
  except ValueError:self.message.set('请输入 1/30–300 秒且最小值 ≤ 最大值。');return
  self.bounds=(max(.30,low),max(.30,high));self.target_external=self.external.get();self.active=True;self.count=0
  self.message.set('3 秒后开始；F12 全局停止。');self.button.configure(text='停止 / Stop')
  self.timer=self.root.after(3000,self.begin)
 def begin(self):
  if not self.active:return
  if not self.target_external:
   self.root.lift()
   api=self.keyboard.api
   api.GetAncestor.argtypes=[w.HWND,w.UINT];api.GetAncestor.restype=w.HWND
   api.SetForegroundWindow.argtypes=[w.HWND]
   hwnd=api.GetAncestor(self.root.winfo_id(),2)
   api.ShowWindow.argtypes=[w.HWND,c.c_int];api.ShowWindow(hwnd,9)
   api.SetForegroundWindow(hwnd)
   self.draft.focus_force()
   # Disable IME only for this application's draft control, not other apps.
   imm=c.WinDLL('imm32',use_last_error=True)
   imm.ImmAssociateContextEx.argtypes=[w.HWND,w.HANDLE,w.DWORD]
   imm.ImmAssociateContextEx(hwnd,None,1)
   api.GetForegroundWindow.restype=w.HWND
   api.GetWindowThreadProcessId.argtypes=[w.HWND,c.POINTER(w.DWORD)]
   pid=w.DWORD();api.GetWindowThreadProcessId(api.GetForegroundWindow(),c.byref(pid))
   if pid.value != os.getpid():
    self.stop();self.message.set('无法聚焦草稿，请点击草稿后再开始。');return
  self.tick()
 def tick(self):
  if not self.active:return
  if not self.target_external and self.root.focus_get() is not self.draft:
   self.stop();self.message.set('草稿失去焦点，已停止。');return
  # Avoid shortcuts or releasing keys currently held by the user.
  if any(self.keyboard.pressed(v) for v in (16,17,18,91,92)):
   self.stop();self.message.set('检测到修饰键，已停止。');return
  vk=random.choice(list(range(65,91))+list(range(48,58)))
  if self.keyboard.pressed(vk):self.timer=self.root.after(100,self.tick);return
  try:self.keyboard.send(vk)
  except OSError as e:self.stop();self.message.set(str(e));return
  interval=random.uniform(*self.bounds)
  def release():
   try:self.keyboard.release()
   except OSError as e:self.stop();self.message.set(str(e));return
   self.count+=1;self.message.set(f'已发送 {self.count} 次；F12 全局停止。')
   if self.active:self.timer=self.root.after(max(150,round((interval-.15)*1000)),self.tick)
  self.timer=self.root.after(150,release)
 def stop(self):
  self.active=False
  if self.timer is not None:self.root.after_cancel(self.timer);self.timer=None
  self.keyboard.release();self.button.configure(text='三秒后开始 / Start');self.message.set(f'已停止；发送 {self.count} 次。')
 def check_stop(self):
  if self.keyboard.pressed(123) and self.active:self.stop()
  self.poll=self.root.after(10,self.check_stop)
 def close(self):
  self.stop()
  if self.poll:self.root.after_cancel(self.poll)
  self.root.destroy()
if __name__=='__main__':
 root=tk.Tk();App(root);root.mainloop()
