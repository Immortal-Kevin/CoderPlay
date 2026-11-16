# SPDX-License-Identifier: Apache-2.0
import tkinter as tk
import unittest
from unittest.mock import patch

from tapper import App


class FakeMouse:
    def __init__(self):
        self.keys = set()
        self.clicks = []

    def pressed(self, key):
        return key in self.keys

    def click(self, button):
        self.clicks.append(button)


class InteractionTests(unittest.TestCase):
    def setUp(self):
        self.mouse = FakeMouse()
        self.root = tk.Tk()
        self.root.withdraw()
        with patch('tapper.WindowsMouse', return_value=self.mouse):
            self.app = App(self.root)

    def tearDown(self):
        self.app.close()

    def test_countdown_starts_only_after_three_seconds(self):
        with patch('tapper.time.perf_counter', return_value=100):
            self.app.toggle()
            self.assertEqual(self.app.start_at, 103)
            self.assertFalse(self.app.engine.running)
        with patch('tapper.time.perf_counter', return_value=102.9), patch.object(self.app.engine, 'start') as start:
            self.app.poll()
            start.assert_not_called()
        with patch('tapper.time.perf_counter', return_value=103), patch.object(self.app.engine, 'start') as start:
            self.app.poll()
            start.assert_called_once_with(0.1, 'left', immediate=True)
            self.assertIsNone(self.app.start_at)

    def test_global_keyboard_key_cancels_countdown(self):
        for key in (0x41, 0x20, 0x75, 0x77, 0x10):
            self.mouse.keys.clear()
            self.app.toggle()
            self.mouse.keys.add(key)
            self.app.poll()
            self.assertIsNone(self.app.start_at)
            self.assertFalse(self.app.engine.running)

    def test_global_keyboard_key_stops_active_worker(self):
        self.app.engine.start(120, 'left')
        self.mouse.keys.add(0x42)
        self.app.poll()
        self.assertFalse(self.app.engine.running)
        self.assertEqual(self.mouse.clicks, [])

    def test_mouse_buttons_do_not_cancel_and_idle_keys_never_start(self):
        self.app.toggle()
        self.mouse.keys.add(1)
        self.app.poll()
        self.assertIsNotNone(self.app.start_at)
        self.app.stop()
        self.mouse.keys = {0x75, 0x77}
        self.app.poll()
        self.assertIsNone(self.app.start_at)
        self.assertFalse(self.app.engine.running)

    def test_window_key_event_and_button_cancel(self):
        self.app.toggle()
        self.assertEqual(self.app.on_key(None), 'break')
        self.assertIsNone(self.app.start_at)
        self.app.toggle()
        self.app.toggle()
        self.assertIsNone(self.app.start_at)

    def test_start_button_visible_at_high_dpi_and_minimum_size(self):
        self.app.close()
        self.root = tk.Tk()
        original_scale = self.root.tk.call('tk', 'scaling')
        try:
            self.root.tk.call('tk', 'scaling', 240 / 72)
            with patch('tapper.WindowsMouse', return_value=self.mouse):
                self.app = App(self.root)
            self.root.geometry('640x640')
            for lang in ('zh', 'en'):
                self.app.lang = lang
                self.app.translate()
                self.root.update()
                button = self.app.action
                self.assertTrue(button.winfo_ismapped())
                self.assertGreater(button.winfo_height(), 40)
                self.assertLessEqual(button.winfo_rooty() + button.winfo_height(),
                                     self.root.winfo_rooty() + self.root.winfo_height())
                button.invoke()
                self.assertIsNotNone(self.app.start_at)
                self.app.stop()
        finally:
            self.root.tk.call('tk', 'scaling', original_scale)


if __name__ == '__main__':
    unittest.main()
