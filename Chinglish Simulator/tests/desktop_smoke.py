"""Windows desktop smoke test; no model calls or persistent user data."""
import tempfile
import time
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

import app
from desktop import Desktop, style_label


def main():
    with tempfile.TemporaryDirectory() as tmp, patch.object(app, 'DATA', Path(tmp)):
        root = tk.Tk()
        try:
            desktop = Desktop(root)
            root.update()
            assert root.winfo_ismapped()
            assert desktop.intensity.get() == 60
            requests = []

            def model(request):
                requests.append(request)
                return dict(translation='Mock translation.', analysis='Mock analysis.')

            with patch.object(app, 'translate', side_effect=model):
                for value in range(101):
                    desktop.slider.set(value)
                    root.update_idletasks()
                    assert desktop.intensity.get() == value
                    assert desktop.style.get() == f'{value}% · {style_label(value)}'
                assert not requests
                desktop.source.insert('1.0', '你牛逼，我不说了。')
                desktop.profanity.current(0)
                for value, regenerate in [(0, False), (100, True)]:
                    desktop.slider.set(value)
                    desktop.translate(regenerate)
                    deadline = time.monotonic() + 3
                    while desktop.busy and time.monotonic() < deadline:
                        root.update()
                        time.sleep(.01)
                    assert not desktop.busy
                    assert requests[-1]['intensity'] == value
                    assert requests[-1]['regenerate'] is regenerate
                    assert requests[-1]['profanity_level'] == 0
                    assert desktop.result.get('1.0', 'end-1c') == 'Mock translation.'
                assert len(requests) == 2
            desktop.slider.set(37)
            desktop.close()
            root = tk.Tk()
            restarted = Desktop(root)
            assert restarted.intensity.get() == 37
            assert restarted.profanity.current() == 0
        finally:
            root.destroy()
    print('Desktop PASS: 101 slider values, no requests while sliding, Translate and Regenerate, restart persistence.')


if __name__ == '__main__':
    main()
