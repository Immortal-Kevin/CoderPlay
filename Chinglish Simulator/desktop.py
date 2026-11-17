import json
import logging
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

import app
import local_model


def style_label(value):
    for limit, label in [(20, 'Mostly English'), (40, 'Light Chinglish'),
                         (60, 'Natural Chinglish'), (80, 'Heavy Chinglish'),
                         (100, 'Brainrot Chinglish')]:
        if value <= limit:
            return label


class Desktop:
    def __init__(self, root):
        self.root = root
        self.pending = queue.SimpleQueue()
        self.busy = False
        self.current = None
        self.rating = ''
        root.title('Chinglish Simulator')
        root.geometry('980x730')
        root.minsize(800, 680)
        root.option_add('*Font', ('Segoe UI', 10))

        panel = ttk.Frame(root, padding=16)
        panel.pack(fill='both', expand=True)
        panel.columnconfigure((0, 1), weight=1, uniform='editor')
        panel.rowconfigure(2, weight=1)
        ttk.Label(panel, text='Chinglish Simulator', font=('Segoe UI', 23, 'bold')).grid(row=0, column=0, sticky='w')
        nav = ttk.Frame(panel)
        nav.grid(row=0, column=1, sticky='e')
        for label, command in [('历史', self.history), ('示例库', self.examples)]:
            ttk.Button(nav, text=label, command=lambda fn=command: self.safe(fn)).pack(side='left', padx=3)

        self.status = tk.StringVar(value='本地模型 · Qwen2.5 1.5B · Vulkan 核显'
                                   if local_model.installed() else '缺少本地模型，请运行 setup-local.cmd。')
        ttk.Label(panel, textvariable=self.status, wraplength=740).grid(row=1, columnspan=2, sticky='w', pady=(4, 10))
        self.source = self.editor(panel, '中文原文', 0)
        self.result = self.editor(panel, 'Chinglish', 1)
        self.result.configure(state='disabled')

        context_frame = ttk.Frame(panel)
        context_frame.grid(row=3, column=0, sticky='ew', padx=(0, 7), pady=8)
        ttk.Label(context_frame, text='上下文（可选）').pack(anchor='w')
        self.context = self.textbox(context_frame, height=2)
        self.context.pack(fill='x')
        self.tone = ''
        output_actions = ttk.Frame(panel)
        output_actions.grid(row=3, column=1, sticky='nw', pady=8)
        self.buttons(output_actions, [('Copy', self.copy), ('编辑译文', self.edit),
                                      ('语气分析', self.analysis)])
        feedback = ttk.Frame(panel)
        feedback.grid(row=4, column=1, sticky='nw')
        self.buttons(feedback, [('Like', lambda: self.rate('like')),
                                ('Dislike', lambda: self.rate('dislike')),
                                ('保存为示例', self.save_example)])

        preferences = app.prefs(app.read(app.DATA / 'preferences.json', {}))
        slider_panel = ttk.LabelFrame(panel, text='Chinglish Intensity', padding=8)
        slider_panel.grid(row=5, columnspan=2, sticky='ew', pady=(12, 6))
        caption = ttk.Frame(slider_panel)
        caption.pack(fill='x')
        ttk.Label(caption, text='Standard English').pack(side='left')
        ttk.Label(caption, text='Brainrot Chinglish').pack(side='right')
        self.intensity = tk.IntVar(value=preferences['intensity'])
        self.style = tk.StringVar()
        self.slider = tk.Scale(slider_panel, variable=self.intensity, from_=0, to=100,
                               resolution=1, orient='horizontal', showvalue=False,
                               sliderlength=22, width=14, troughcolor='#cfe0ff',
                               background='#2563eb', activebackground='#1d4ed8',
                               highlightthickness=1, takefocus=True)
        self.slider.pack(fill='x', pady=3)
        ttk.Label(slider_panel, textvariable=self.style).pack()
        self.intensity.trace_add('write', self.update_style)
        self.update_style()

        controls = ttk.Frame(panel)
        controls.grid(row=6, columnspan=2, sticky='ew')
        self.options = {}
        labels = dict(relationship='交流对象', emotion='情绪', chinese='汉字保留', length='输出长度')
        for col, (key, values) in enumerate(app.OPTIONS.items()):
            self.options[key] = self.choice(controls, col, labels[key], values, preferences[key])
        profanity = ['0 · None', '1 · Mild', '2 · Natural', '3 · Strong']
        self.profanity = self.choice(controls, len(labels), '粗口程度', profanity,
                                     profanity[preferences['profanity_level']])
        actions = ttk.Frame(panel)
        actions.grid(row=7, columnspan=2, sticky='w', pady=(12, 0))
        self.buttons(actions, [('Translate', lambda: self.translate(False)),
                               ('Regenerate', lambda: self.translate(True)),
                               ('Clear', self.clear), ('保存偏好', self.save_preferences)])
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(50, self.poll)

    def textbox(self, parent, height, **kwargs):
        return tk.Text(parent, height=height, wrap='word', background='#151923',
                       foreground='#edf2fa', insertbackground='white', padx=9, pady=7,
                       undo=True, **kwargs)

    def editor(self, panel, title, column):
        frame = ttk.LabelFrame(panel, text=title, padding=5)
        frame.grid(row=2, column=column, sticky='nsew', padx=(0, 7) if column == 0 else (7, 0))
        text = self.textbox(frame, height=8, width=25)
        bar = ttk.Scrollbar(frame, orient='vertical', command=text.yview)
        text.configure(yscrollcommand=bar.set)
        bar.pack(side='right', fill='y')
        text.pack(side='left', fill='both', expand=True)
        return text

    def choice(self, parent, col, label, values, value):
        frame = ttk.Frame(parent)
        frame.grid(row=0, column=col, sticky='ew', padx=(0, 7))
        parent.columnconfigure(col, weight=1)
        ttk.Label(frame, text=label).pack(anchor='w')
        menu = ttk.Combobox(frame, values=values, state='readonly', width=19 if col == 2 else 10)
        menu.set(value)
        menu.pack(fill='x')
        return menu

    def buttons(self, parent, actions):
        for label, command in actions:
            ttk.Button(parent, text=label, command=lambda fn=command: self.safe(fn)).pack(side='left', padx=(0, 6))

    def safe(self, action):
        try:
            action()
        except (ValueError, OSError, KeyError, TypeError, OverflowError, tk.TclError) as exc:
            self.error(exc)

    def error(self, exc):
        logging.info('Operation failed (%s)', type(exc).__name__)
        self.status.set(str(exc) if type(exc) is ValueError else '操作失败，请检查配置、输入和本地文件权限。')

    def update_style(self, *_):
        value = self.intensity.get()
        self.style.set(f'{value}% · {style_label(value)}')

    def preferences(self):
        return app.prefs(dict(intensity=self.intensity.get(),
                              profanity_level=self.profanity.current(),
                              **{key: menu.get() for key, menu in self.options.items()}))

    def save_preferences(self, announce=True):
        app.write(app.DATA / 'preferences.json', self.preferences())
        if announce:
            self.status.set('偏好已保存。')

    def close(self):
        if self.busy:
            self.status.set('正在完成本地推理，请稍等再关闭。')
            return
        try:
            self.save_preferences(announce=False)
        except (ValueError, OSError) as exc:
            self.error(exc)
            if not messagebox.askyesno('偏好保存失败', '仍要关闭程序吗？', parent=self.root):
                return
        self.root.destroy()

    def background(self, job, done):
        if self.busy:
            raise ValueError('已有模型请求正在处理。')
        self.busy = True

        def run():
            try:
                self.pending.put((done, job(), None))
            except Exception as exc:
                self.pending.put((done, None, exc))

        threading.Thread(target=run, daemon=True).start()

    def poll(self):
        try:
            callback, result, error = self.pending.get_nowait()
        except queue.Empty:
            pass
        else:
            self.busy = False
            if error is None:
                self.safe(lambda: callback(result))
            else:
                self.error(error)
        self.root.after(50, self.poll)

    def translate(self, regenerate):
        if self.busy:
            raise ValueError('已有模型请求正在处理。')
        options = self.preferences()
        source = self.source.get('1.0', 'end-1c')
        context = self.context.get('1.0', 'end-1c')
        payload = dict(text=source, context=context, regenerate=regenerate,
                       intensity=options['intensity'], relationship=options['relationship'].lower(),
                       emotion=options['emotion'].lower(), profanity_level=options['profanity_level'],
                       chinese=options['chinese'], output_length=options['length'].lower(),
                       preserve_chinese_memes=options['chinese'] == app.OPTIONS['chinese'][0])
        self.save_preferences(announce=False)
        self.status.set(f"正在翻译 · 强度 {options['intensity']}%")

        def done(result):
            self.current = dict(source=source, options=options)
            self.rating = ''
            self.tone = result['analysis']
            self.set_result(result['translation'])
            self.status.set(f"翻译完成 · 强度 {options['intensity']}%")

        self.background(lambda: app.translate(payload), done)

    def set_result(self, text):
        self.result.configure(state='normal')
        self.result.delete('1.0', 'end')
        self.result.insert('1.0', text)
        self.result.configure(state='disabled')

    def clear(self):
        if self.busy:
            raise ValueError('请等模型请求完成后再清空。')
        self.source.delete('1.0', 'end')
        self.context.delete('1.0', 'end')
        self.set_result('')
        self.current = None
        self.tone = ''
        self.status.set('已清空。')

    def require_output(self):
        if self.current is None:
            raise ValueError('还没有译文。')

    def copy(self):
        self.require_output()
        self.root.clipboard_clear()
        self.root.clipboard_append(self.result.get('1.0', 'end-1c'))
        self.status.set('已复制。')

    def edit(self):
        self.require_output()
        self.result.configure(state='normal')
        self.result.focus_set()

    def analysis(self):
        self.require_output()
        messagebox.showinfo('语气分析', self.tone or '模型未提供分析。', parent=self.root)

    def rate(self, rating):
        self.require_output()
        if self.rating:
            raise ValueError('这条译文已提交反馈。')
        app.record_rating(rating)
        self.rating = rating
        self.status.set('反馈已保存在本机。')

    def save_example(self):
        self.require_output()
        row = self.current | dict(translation=self.result.get('1.0', 'end-1c'), rating=self.rating)
        app.save_examples(dict(examples=[row], merge=True))
        self.status.set('已保存到本地示例库。')

    def dialog(self, title):
        window = tk.Toplevel(self.root)
        window.title(title)
        window.transient(self.root)
        window.grab_set()
        return window

    def history(self):
        win = self.dialog('最近翻译')
        view = self.textbox(win, height=22, width=78)
        view.pack(fill='both', expand=True, padx=8, pady=8)

        def render():
            rows = app.read(app.DATA / 'history.json', []) if app.history_enabled() else []
            view.configure(state='normal')
            view.delete('1.0', 'end')
            view.insert('1.0', '\n\n'.join(f"{row['source']}\n{row['translation']}" for row in rows)
                        or '暂无记录，或记录已关闭。')
            view.configure(state='disabled')

        def clear():
            if self.busy:
                raise ValueError('请等模型请求完成后再清空历史。')
            if messagebox.askyesno('清空历史', '删除全部翻译记录？', parent=win):
                app.write(app.DATA / 'history.json', [])
                render()

        enabled = tk.BooleanVar(value=app.history_enabled())

        def toggle():
            app.write(app.DATA / 'desktop_settings.json', {'history': enabled.get()})
            render()

        ttk.Checkbutton(win, text='保存最近 50 条原文和译文', variable=enabled,
                        command=lambda: self.safe(toggle)).pack(anchor='w', padx=8)
        ttk.Button(win, text='清空记录', command=lambda: self.safe(clear)).pack(pady=8)
        render()

    def examples(self):
        win = self.dialog('本地示例库')
        body = ttk.Frame(win, padding=10)
        body.pack(fill='both', expand=True)
        listing = tk.Listbox(body, width=65, height=8, exportselection=False)
        listing.pack(fill='both', expand=True)
        source = self.textbox(body, height=3, width=65)
        result = self.textbox(body, height=4, width=65)
        for title, box in [('示例原文', source), ('示例译文', result)]:
            ttk.Label(body, text=title).pack(anchor='w')
            box.pack(fill='x')
        rows = []
        hint = tk.StringVar()
        ttk.Label(body, textvariable=hint, wraplength=550).pack(anchor='w')

        def refresh():
            rows[:] = [app.example(row) for row in app.read(app.DATA / 'user_examples.json', [])]
            listing.delete(0, 'end')
            for row in rows:
                listing.insert('end', f"{row['options']['intensity']}% · {row['source'].splitlines()[0][:60]}")
            for box in (source, result):
                box.delete('1.0', 'end')

        def selected():
            selection = listing.curselection()
            return selection[0] if selection else None

        def show(_event):
            index = selected()
            if index is not None:
                for box, key in [(source, 'source'), (result, 'translation')]:
                    box.delete('1.0', 'end')
                    box.insert('1.0', rows[index][key])

        def update(remove=False):
            index = selected()
            if index is None:
                raise ValueError('请先选择一条示例。')
            updated = rows.copy()
            if remove:
                updated.pop(index)
            else:
                updated[index] = rows[index] | dict(source=source.get('1.0', 'end-1c'),
                                                     translation=result.get('1.0', 'end-1c'))
            app.save_examples(dict(examples=updated))
            refresh()
            hint.set('本地示例库已更新。')

        def import_file():
            name = filedialog.askopenfilename(parent=win, filetypes=[('JSON', '*.json')])
            if name:
                path = Path(name)
                if path.stat().st_size > 4 * 1024 * 1024:
                    raise ValueError('JSON 文件过大。')
                app.save_examples(dict(examples=json.loads(path.read_text(encoding='utf-8-sig')), merge=True))
                refresh()
                hint.set('导入完成。')

        def export_file():
            name = filedialog.asksaveasfilename(parent=win, defaultextension='.json',
                                                initialfile='chinglish-examples.json')
            if name:
                Path(name).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
                hint.set('导出完成。')

        def invoke(fn):
            try:
                fn()
            except (ValueError, OSError) as exc:
                hint.set(str(exc) if type(exc) is ValueError else '无法读取或保存文件。')

        listing.bind('<<ListboxSelect>>', show)
        actions = ttk.Frame(body)
        actions.pack(anchor='w', pady=8)
        self.buttons(actions, [(label, lambda fn=fn: invoke(fn)) for label, fn in
                               [('保存修改', update), ('删除', lambda: update(True)),
                                ('导入 JSON', import_file), ('导出 JSON', export_file)]])
        refresh()


def main():
    root = tk.Tk()
    try:
        app.DATA.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(filename=app.DATA / 'app.log', encoding='utf-8', level=logging.INFO,
                            format='%(asctime)s %(levelname)s %(message)s')
        Desktop(root)
    except (OSError, ValueError, TypeError):
        messagebox.showerror('启动失败', '无法读取本地设置或无法访问本地数据目录。', parent=root)
        root.destroy()
        return
    root.mainloop()


if __name__ == '__main__':
    main()
