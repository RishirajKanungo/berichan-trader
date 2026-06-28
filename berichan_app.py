"""
Frozen-build entry point (used by PyInstaller / berichan.spec).

PyInstaller runs the entry script as ``__main__`` with no parent package, so it
must use an absolute import — unlike ``berichan/gui/__main__.py`` (used by
``python -m berichan.gui``), which can use a package-relative import.
"""

from berichan.gui.app import main

if __name__ == "__main__":
    main()
