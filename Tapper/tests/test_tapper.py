# SPDX-License-Identifier: Apache-2.0
import time
import unittest
from tapper import Clicker, interval_seconds


class FakeMouse:
    def __init__(self):
        self.clicks = []

    def click(self, button):
        self.clicks.append(button)


class TapperTests(unittest.TestCase):
    def test_interval_bounds_and_units(self):
        self.assertEqual(interval_seconds('10', 'ms'), 0.01)
        self.assertEqual(interval_seconds('2', 'min'), 120)
        self.assertEqual(interval_seconds('0.5', 's'), 0.5)
        for value in ('0', '-1', 'nan', 'inf', 'abc', '120.1'):
            with self.assertRaises(ValueError):
                interval_seconds(value, 's')

    def test_click_and_stop(self):
        mouse = FakeMouse()
        engine = Clicker(mouse)
        engine.start(0.01, 'right')
        time.sleep(0.09)
        engine.stop()
        self.assertGreater(len(mouse.clicks), 0)
        self.assertEqual(set(mouse.clicks), {'right'})
        count = len(mouse.clicks)
        time.sleep(0.03)
        self.assertEqual(len(mouse.clicks), count)
        self.assertFalse(engine.running)

    def test_long_wait_cancels_promptly(self):
        engine = Clicker(FakeMouse())
        engine.start(120, 'left')
        start = time.perf_counter()
        engine.stop()
        self.assertLess(time.perf_counter() - start, 0.5)
        self.assertEqual(engine.count, 0)

    def test_input_failure_stops_worker(self):
        class BrokenMouse:
            def click(self, button):
                raise OSError('blocked')
        engine = Clicker(BrokenMouse())
        engine.start(0.01, 'left')
        engine.thread.join(1)
        self.assertFalse(engine.running)
        self.assertEqual(engine.error, 'blocked')


if __name__ == '__main__':
    unittest.main()
