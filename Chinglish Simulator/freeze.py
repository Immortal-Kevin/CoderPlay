"""Build the portable Windows desktop application with cx_Freeze."""
from cx_Freeze import Executable, setup


setup(
    name='Chinglish Simulator',
    version='1.0.0',
    options={
        'build_exe': {
            'include_files': [
                ('data/chinglish_rules.json', 'data/chinglish_rules.json'),
                ('data/intensity.json', 'data/intensity.json'),
                'LICENSE',
                'setup-local.cmd',
                'setup-local.ps1',
            ],
            'include_msvcr': True,
        },
    },
    executables=[Executable('desktop.py', base='gui', target_name='Chinglish Simulator.exe')],
)
