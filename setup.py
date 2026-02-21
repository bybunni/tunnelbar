"""py2app build configuration for Tunnelbar.

Run with: .venv/bin/python setup.py py2app
"""

from setuptools import setup

# py2app 0.28+ rejects install_requires, but setuptools 82+ populates it
# from pyproject.toml [project.dependencies].  Clear it before py2app sees it.
import sys

if "py2app" in sys.argv:
    import py2app.build_app

    _orig_finalize = py2app.build_app.py2app.finalize_options

    def _patched_finalize(self):
        self.distribution.install_requires = []
        _orig_finalize(self)

    py2app.build_app.py2app.finalize_options = _patched_finalize

APP = ["run_tunnelbar.py"]
DATA_FILES = ["config.example.yaml"]
OPTIONS = {
    "argv_emulation": False,
    "emulate_shell_environment": True,
    "iconfile": "tunnelbar/resources/Tunnelbar.icns",
    "packages": ["tunnelbar", "rumps"],
    "plist": {
        "CFBundleName": "Tunnelbar",
        "CFBundleDisplayName": "Tunnelbar",
        "CFBundleIdentifier": "com.tunnelbar.app",
        "CFBundleVersion": "0.1.0",
        "CFBundleShortVersionString": "0.1.0",
        "LSUIElement": True,
        "NSHumanReadableCopyright": "MIT License",
        "LSEnvironment": {
            "LANG": "en_US.UTF-8",
            "LC_ALL": "en_US.UTF-8",
        },
    },
}

setup(
    app=APP,
    name="Tunnelbar",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
)
