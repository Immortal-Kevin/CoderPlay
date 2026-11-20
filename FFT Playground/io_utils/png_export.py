"""Render original Tk canvas primitives through Windows GDI; encode PNG with zlib.

No screenshot API, external executable, font file, or third-party encoder is used.
System fonts are rasterized through the operating system and are not redistributed.
"""
import ctypes as C
from ctypes import wintypes as W
import struct
import zlib
from pathlib import Path
import tkinter.font as tkfont


def write_png(path, width, height, rgb):
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    rows = b"".join(b"\0" + rgb[y * width * 3:(y + 1) * width * 3] for y in range(height))
    payload = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
               + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))
    with Path(path).open("xb") as stream:
        stream.write(payload)


def export_canvases(path, canvases):
    if not hasattr(C, "WinDLL"):
        raise OSError("PNG 图表导出需要 Windows GDI")
    g = C.WinDLL("gdi32", use_last_error=True)
    signatures = {
        "CreateCompatibleDC": ([W.HDC], W.HDC),
        "CreateDIBSection": ([W.HDC, C.c_void_p, W.UINT, C.POINTER(C.c_void_p), W.HANDLE, W.DWORD], W.HBITMAP),
        "SelectObject": ([W.HDC, W.HANDLE], W.HANDLE),
        "DeleteObject": ([W.HANDLE], W.BOOL), "DeleteDC": ([W.HDC], W.BOOL),
        "CreatePen": ([C.c_int, C.c_int, W.COLORREF], W.HANDLE),
        "CreateSolidBrush": ([W.COLORREF], W.HANDLE),
        "MoveToEx": ([W.HDC, C.c_int, C.c_int, C.c_void_p], W.BOOL),
        "LineTo": ([W.HDC, C.c_int, C.c_int], W.BOOL),
        "SetTextColor": ([W.HDC, W.COLORREF], W.COLORREF),
        "SetBkMode": ([W.HDC, C.c_int], C.c_int),
        "TextOutW": ([W.HDC, C.c_int, C.c_int, W.LPCWSTR, C.c_int], W.BOOL),
        "GetTextExtentPoint32W": ([W.HDC, W.LPCWSTR, C.c_int, C.c_void_p], W.BOOL),
        "CreateFontW": ([C.c_int] * 5 + [W.DWORD] * 8 + [W.LPCWSTR], W.HANDLE),
    }
    for name, (args, result) in signatures.items():
        getattr(g, name).argtypes, getattr(g, name).restype = args, result
    u = C.WinDLL("user32")
    u.FillRect.argtypes = [W.HDC, C.POINTER(W.RECT), W.HANDLE]
    width = max(c.winfo_width() for c in canvases)
    height = sum(c.winfo_height() for c in canvases)
    stride = (width * 3 + 3) & ~3
    header = struct.pack("<IiiHHIIiiII", 40, width, -height, 1, 24, 0, stride * height, 0, 0, 0, 0)
    info = C.create_string_buffer(header)
    bits = C.c_void_p()
    dc = g.CreateCompatibleDC(None)
    bitmap = g.CreateDIBSection(dc, info, 0, C.byref(bits), None, 0)
    if not dc or not bitmap or not bits.value:
        if bitmap: g.DeleteObject(bitmap)
        if dc: g.DeleteDC(dc)
        raise OSError("无法创建 PNG 渲染缓冲区")
    old_bitmap = g.SelectObject(dc, bitmap)
    font = g.CreateFontW(-12, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 0, 0, "Microsoft YaHei")
    old_font = g.SelectObject(dc, font)
    fonts = {}
    g.SetBkMode(dc, 1)
    def color(canvas, value):
        r, green, b = (v // 257 for v in canvas.winfo_rgb(value))
        return r | green << 8 | b << 16
    def fill(canvas, coords, value):
        brush = g.CreateSolidBrush(color(canvas, value))
        rect = W.RECT(*map(round, coords))
        u.FillRect(dc, C.byref(rect), brush)
        g.DeleteObject(brush)
    try:
        offset = 0
        for canvas in canvases:
            fill(canvas, (0, offset, width, offset + canvas.winfo_height()), canvas.cget("background"))
            for item in canvas.find_all():
                kind, coords = canvas.type(item), canvas.coords(item)
                value = canvas.itemcget(item, "fill")
                if not value:
                    continue
                if kind == "line":
                    pen = g.CreatePen(0, max(1, round(float(canvas.itemcget(item, "width")))), color(canvas, value))
                    old_pen = g.SelectObject(dc, pen)
                    g.MoveToEx(dc, round(coords[0]), round(coords[1] + offset), None)
                    for i in range(2, len(coords), 2):
                        g.LineTo(dc, round(coords[i]), round(coords[i + 1] + offset))
                    g.SelectObject(dc, old_pen)
                    g.DeleteObject(pen)
                elif kind == "text":
                    spec = canvas.itemcget(item, "font")
                    if spec not in fonts:
                        actual = tkfont.Font(root=canvas, font=spec).actual()
                        size = actual["size"]
                        pixels = round(size * canvas.winfo_fpixels("1i") / 72) if size > 0 else -size
                        fonts[spec] = g.CreateFontW(-pixels, 0, 0, 0, 700 if actual["weight"] == "bold" else 400,
                                                   0, 0, 0, 1, 0, 0, 0, 0, actual["family"])
                    g.SelectObject(dc, fonts[spec])
                    text = canvas.itemcget(item, "text")
                    anchor = canvas.itemcget(item, "anchor")
                    extent = W.SIZE()
                    g.GetTextExtentPoint32W(dc, text, len(text), C.byref(extent))
                    x, y = coords[0], coords[1] + offset
                    if anchor in ("e", "ne", "se"):
                        x -= extent.cx
                    elif anchor in ("center", "n", "s"):
                        x -= extent.cx / 2
                    if anchor in ("s", "se", "sw"):
                        y -= extent.cy
                    elif anchor in ("center", "e", "w"):
                        y -= extent.cy / 2
                    g.SetTextColor(dc, color(canvas, value))
                    g.TextOutW(dc, round(x), round(y), text, len(text))
                elif kind == "rectangle":
                    fill(canvas, (coords[0], coords[1] + offset, coords[2], coords[3] + offset), value)
            offset += canvas.winfo_height()
        bgr = C.string_at(bits, stride * height)
        rgb = bytearray(width * height * 3)
        for y in range(height):
            row = bgr[y * stride:y * stride + width * 3]
            start = y * width * 3
            rgb[start:start + width * 3:3] = row[2::3]
            rgb[start + 1:start + width * 3:3] = row[1::3]
            rgb[start + 2:start + width * 3:3] = row[0::3]
        write_png(path, width, height, rgb)
    finally:
        g.SelectObject(dc, old_font)
        for handle in fonts.values():
            g.DeleteObject(handle)
        g.SelectObject(dc, old_bitmap)
        g.DeleteObject(font)
        g.DeleteObject(bitmap)
        g.DeleteDC(dc)
