"""Re-export shim for the config package.

Note: Python's import system prefers the config/ package over this module.
This file is present for historical compatibility but is never imported.
All code using ``from config import Settings`` resolves to config/__init__.py.
"""
