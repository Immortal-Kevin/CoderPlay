import os
import re
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from uuid import uuid4

EXTENSIONS = {".zip", ".rar", ".mp4", ".mov"}


def natural_key(path):
    return [int(part) if index % 2 else part.casefold()
            for index, part in enumerate(re.split(r"([0-9]+)", path.name))]


def make_plan(files, folder, prefix, middle, width, suffix):
    if not re.fullmatch(r"[A-Za-z0-9]+", prefix):
        raise ValueError("前部请输入英文字母或数字。")
    if not re.fullmatch(r"[0-9]{1,18}", suffix):
        raise ValueError("后部起始编号请输入 1–18 位数字。")
    if not re.fullmatch(r"[0-9]{1,18}", middle):
        raise ValueError("中部固定编号请输入 1–18 位数字。")
    if not re.fullmatch(r"[0-9]{1,2}", width) or not 1 <= int(width) <= 18:
        raise ValueError("补零位数请输入 1–18。")
    return [
        (source, folder / f"{prefix}-{middle.zfill(int(width))}-{str(int(suffix) + offset).zfill(len(suffix))}{source.suffix}")
        for offset, source in enumerate(files)
    ]


def apply_plan(plan, copy_files):
    changes = [(source, target) for source, target in plan if str(source) != str(target)]
    sources = set() if copy_files else {source for source, _ in changes}
    for source, target in changes:
        if not source.is_file():
            raise ValueError(f"找不到源文件：{source.name}")
        if os.path.lexists(target) and target not in sources:
            raise ValueError(f"输出文件已存在：{target.name}")

    staged = []
    completed = []
    try:
        for source, target in changes:
            temporary = target.parent / f".name-changer-{uuid4().hex}.tmp"
            if copy_files:
                with source.open("rb") as original, temporary.open("xb") as output:
                    staged.append((source, temporary, target))
                    shutil.copyfileobj(original, output)
            else:
                source.rename(temporary)
                staged.append((source, temporary, target))
        for entry in staged:
            _, temporary, target = entry
            temporary.rename(target)
            completed.append(entry)
    except OSError as error:
        recovery_errors = []
        for _, temporary, target in reversed(completed):
            try:
                target.rename(temporary)
            except OSError as recovery_error:
                recovery_errors.append(str(recovery_error))
        for source, temporary, _ in reversed(staged):
            try:
                if temporary.exists():
                    if copy_files:
                        temporary.unlink()
                    else:
                        temporary.rename(source)
            except OSError as recovery_error:
                recovery_errors.append(str(recovery_error))
        if recovery_errors:
            raise OSError(f"{error}\n恢复时发生错误：\n" + "\n".join(recovery_errors)) from error
        raise


class NameChanger:
    def __init__(self, root):
        self.root = root
        self.files = []
        self.folder = None
        self.plan = []
        root.title("Name Changer · 批量改名")
        root.geometry("1020x480")
        root.minsize(800, 370)
        root.rowconfigure(0, weight=1)
        for column, weight in enumerate((1, 0, 1)):
            root.columnconfigure(column, weight=weight)

        left = self.panel("1. 导入文件", 0)
        ttk.Button(left, text="批量导入同类型文件…", command=self.import_files).pack(fill="x")
        ttk.Label(left, text="按原文件名自然排序，例如 2 排在 10 前。").pack(anchor="w", pady=8)
        self.inputs = self.file_list(left)

        middle = self.panel("2. 改名选项", 1)
        self.options = []
        for label, default in (("前部（英文字母 / 数字）", "A"),
                               ("中部固定编号", "1"),
                               ("中部补零位数", "3"),
                               ("后部起始编号", "0")):
            ttk.Label(middle, text=label).pack(anchor="w", pady=(0, 3))
            value = tk.StringVar(value=default)
            ttk.Entry(middle, textvariable=value, width=23).pack(fill="x", pady=(0, 10))
            value.trace_add("write", self.refresh)
            self.options.append(value)
        ttk.Label(middle, text="示例：A-001-0 → A-001-1").pack(anchor="w")

        right = self.panel("3. 输出文件", 2)
        ttk.Button(right, text="选择其他输出目录…", command=self.choose_folder).pack(fill="x")
        ttk.Button(right, text="恢复为导入目录", command=self.reset_folder).pack(fill="x", pady=(4, 0))
        self.location = ttk.Label(right, text="输出目录随导入设置", wraplength=300)
        self.location.pack(anchor="w", pady=8)
        self.outputs = self.file_list(right)
        self.submit = ttk.Button(right, text="应用改名", command=self.run, state="disabled")
        self.submit.pack(fill="x", pady=(8, 0))
        self.status = ttk.Label(root, text="支持 ZIP、RAR、MP4、MOV", padding=(12, 0, 12, 10),
                                wraplength=760)
        self.status.grid(row=1, column=0, columnspan=3, sticky="ew")

    def panel(self, title, column):
        panel = ttk.LabelFrame(self.root, text=title, padding=12)
        panel.grid(row=0, column=column, sticky="nsew", padx=7, pady=10)
        return panel

    def file_list(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        box = tk.Listbox(frame, width=30, exportselection=False)
        vertical = ttk.Scrollbar(frame, command=box.yview)
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=box.xview)
        box.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        box.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        return box

    def import_files(self):
        selected = filedialog.askopenfilenames(
            parent=self.root, title="选择同一目录下的同类型文件",
            filetypes=[("支持的文件", "*.zip *.rar *.mp4 *.mov"),
                       ("ZIP", "*.zip"), ("RAR", "*.rar"), ("MP4", "*.mp4"), ("MOV", "*.mov")])
        if not selected:
            return
        files = sorted({Path(name).resolve() for name in selected},
                       key=lambda path: (natural_key(path), path.name.casefold(), path.name))
        extensions = {path.suffix.lower() for path in files}
        if len(extensions) != 1 or not extensions <= EXTENSIONS or len({p.parent for p in files}) != 1:
            messagebox.showerror("无法导入", "请选择同一目录下、扩展名相同的受支持文件。")
            return
        self.files = files
        self.reset_folder()

    def reset_folder(self):
        if self.files:
            self.folder = self.files[0].parent
            self.refresh()

    def choose_folder(self):
        folder = filedialog.askdirectory(parent=self.root, initialdir=self.folder, mustexist=True)
        if folder and self.files:
            self.folder = Path(folder).resolve()
            self.refresh()

    def refresh(self, *_):
        if not self.files:
            return
        self.inputs.delete(0, tk.END)
        self.inputs.insert(tk.END, *(path.name for path in self.files))
        self.outputs.delete(0, tk.END)
        self.location.configure(text=str(self.folder))
        copy_files = self.folder != self.files[0].parent
        self.submit.configure(text="复制到输出目录" if copy_files else "应用改名", state="disabled")
        try:
            self.plan = make_plan(self.files, self.folder, *(value.get() for value in self.options))
        except ValueError as error:
            self.status.configure(text=str(error))
            return
        self.outputs.insert(tk.END, *(target.name for _, target in self.plan))
        self.submit.configure(state="normal")
        action = "复制到输出目录并保留源文件" if copy_files else "在原目录改名"
        self.status.configure(text=f"共 {len(self.plan)} 个文件 · {action}")

    def run(self):
        copy_files = self.folder != self.files[0].parent
        try:
            apply_plan(self.plan, copy_files)
        except (OSError, ValueError) as error:
            messagebox.showerror("操作失败", str(error))
            return
        if not copy_files:
            self.files = [target for _, target in self.plan]
            self.refresh()
        self.status.configure(text=f"已完成，共处理 {len(self.plan)} 个文件。")
        self.submit.configure(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    NameChanger(root)
    root.mainloop()



