"""Real Tk/GDI integration tests. A Windows desktop is required; no mock renderer."""
import os
import struct
import time
import tkinter as tk
import pytest
from ui.main_window import MainWindow
from io_utils.png_export import export_canvases
from io_utils.csv_handler import export_csv

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows GUI/GDI integration")


@pytest.fixture(scope="module")
def window():
    root = tk.Tk()
    root.geometry("1366x768+0+0")
    ui = MainWindow(root)
    root.geometry("1366x768+0+0")
    deadline = time.monotonic()+15
    while not ui.result and time.monotonic()<deadline:
        root.update()
        time.sleep(.01)
    assert ui.result is not None
    yield ui
    if not ui.closed: ui.close()


@pytest.fixture
def app(window):
    window.defaults()
    deadline = time.monotonic()+15
    while window.busy and time.monotonic()<deadline:
        window.root.update()
        time.sleep(.01)
    window.root.update()
    assert not window.busy
    return window


def test_layout_and_png_gdi(app, tmp_path):
    root = app.root
    root.update()
    assert root.winfo_width() == 1366
    for plot in app.plots:
        assert plot.winfo_height() >= 120
        assert plot.winfo_width() > 800
    def check(widget):
        if widget.winfo_ismapped() and widget.winfo_class() == "TButton":
            assert widget.winfo_rooty()+widget.winfo_height() <= root.winfo_rooty()+root.winfo_height()
            assert widget.winfo_rootx()+widget.winfo_width() <= root.winfo_rootx()+root.winfo_width()
        for child in widget.winfo_children(): check(child)
    check(root)
    path = tmp_path / "charts.png"
    export_canvases(path, app.plots)
    assert struct.unpack(">II", path.read_bytes()[16:24]) == (max(p.winfo_width() for p in app.plots), sum(p.winfo_height() for p in app.plots))
    with pytest.raises(FileExistsError): export_canvases(path, app.plots)


def test_play_pause_stop_and_independent_views(app):
    before = [p.view for p in app.plots]
    app.start()
    app.root.update()
    assert app.playing
    assert app.plots[0].view != before[0]
    assert app.plots[1].view == before[1]
    app.pause()
    assert not app.playing
    app.stop()
    assert app.plots[0].view == before[0]


def test_parameter_update_changes_charts(app):
    app.vars["fs"].set("3000")
    app.vars["duration"].set("1.1")
    app.vars["rpm"].set("1200")
    app.vars["band_high"].set("1200")
    app.update()
    deadline=time.monotonic()+15
    while app.busy and time.monotonic()<deadline:
        app.root.update()
        time.sleep(.01)
    assert app.result.parameters.rpm == 1200
    assert len(app.plots[0].x) == 3300
    assert app.plots[1].x[1] == pytest.approx(3000/3300)
    assert "1200 RPM" in app.info.get()


def test_real_tk_mouse_and_button_events(app):
    root = app.root
    plot = app.plots[1]
    initial = plot.view
    plot.event_generate("<MouseWheel>", x=350, y=80, delta=120)
    root.update()
    assert plot.view[1]-plot.view[0] < initial[1]-initial[0]
    assert app.plots[0].view == app.plots[0].default_view

    zoomed = plot.view
    plot.event_generate("<ButtonPress-1>", x=350, y=80)
    plot.event_generate("<B1-Motion>", x=380, y=85)
    root.update()
    assert plot.view != zoomed
    plot.event_generate("<Motion>", x=400, y=90)
    root.update()
    assert "Amplitude:" in app.status.get()
    def descendants(widget):
        for child in widget.winfo_children():
            yield child
            yield from descendants(child)
    buttons = {w.cget("text"):w for w in descendants(root) if w.winfo_class()=="TButton"}
    buttons["重置视图"].invoke()
    assert plot.view == initial
    buttons["开始"].invoke()
    root.update()
    assert app.playing
    buttons["暂停"].invoke()
    assert not app.playing
    buttons["停止"].invoke()
    assert app.plots[0].view == app.plots[0].default_view

def test_invalid_ui_and_csv_import_preserves_input(app, tmp_path, monkeypatch):
    from ui import main_window
    errors=[]
    monkeypatch.setattr(main_window.messagebox,"showerror",lambda *args,**kwargs:errors.append(args))
    app.vars["band_high"].set("2048")
    original=app.result
    app.update()
    assert errors and not app.busy and app.result is original
    app.vars["band_high"].set("1600")
    path=tmp_path/"source.csv"
    export_csv(path,app.result)
    before=path.read_bytes()
    monkeypatch.setattr(main_window.filedialog,"askopenfilename",lambda **kwargs:str(path))
    app.load_csv()
    deadline=time.monotonic()+15
    while app.busy and time.monotonic()<deadline:
        app.root.update()
        time.sleep(.01)
    assert app.result.source=="imported"
    assert app.result.raw==original.raw
    assert path.read_bytes()==before
    app.vars["fs"].set("4000")
    app.update()
    assert len(errors)==2 and not app.busy
    assert path.read_bytes()==before


def test_1366_screen_workarea_with_all_parameter_tabs(app):
    root=app.root
    root.geometry("1320x680+0+0")
    root.update()

    def descendants(widget):
        for child in widget.winfo_children():
            yield child
            yield from descendants(child)
    notebook=next(w for w in descendants(root) if w.winfo_class()=="TNotebook")
    for tab in notebook.tabs():
        notebook.select(tab)
        root.update()
        for widget in descendants(root):
            if widget.winfo_ismapped() and widget.winfo_class() in ("TButton","TEntry","TCheckbutton"):
                assert widget.winfo_rooty()+widget.winfo_height() <= root.winfo_rooty()+root.winfo_height()
        for widget in descendants(root.nametowidget(tab)):
            if widget.winfo_class()=="TEntry":
                assert widget.winfo_rooty()+widget.winfo_height() <= notebook.winfo_rooty()+notebook.winfo_height()
    notebook.select(0)
    root.geometry("1366x768+0+0")
    root.update()


def test_normal_noise_preset_and_adjustable_floor(app):
    app.preset_name.set("正常运行（有底噪）")
    app.load_preset()
    def wait():
        deadline=time.monotonic()+15
        while app.busy and time.monotonic()<deadline:
            app.root.update()
            time.sleep(.01)
        assert not app.busy
    wait()
    assert float(app.vars["noise"].get())==0.15
    noisy=app.result
    app.vars["noise"].set("0")
    app.update()
    wait()
    clean=app.result
    assert clean.parameters.noise==0
    assert noisy.parameters.harmonics==clean.parameters.harmonics
    high_band=[i for i,f in enumerate(clean.frequency) if 200<=f<=500]
    assert sum(noisy.amplitude[i]**2 for i in high_band)>sum(clean.amplitude[i]**2 for i in high_band)+1e-4
