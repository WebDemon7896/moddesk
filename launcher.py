"""ModDesk launcher - tiny, and never needs rebuilding.

ModDesk.exe only starts the program in  app\\moddesk.py  (next to the exe). To update ModDesk you replace that one
file (or use Settings > Install update from file) - the exe, your pinned taskbar icon, and your data stay put.
"""
import os
import sys
import traceback


def _bundle():
    # Never called. It is here only so PyInstaller packs these standard modules for moddesk.py.
    import base64, ctypes, datetime, json, queue, re, shutil, struct, subprocess, threading, time  # noqa
    import urllib.error, urllib.parse, urllib.request, uuid, webbrowser, zlib, zipfile  # noqa
    import tkinter, tkinter.ttk, tkinter.messagebox, tkinter.filedialog, tkinter.colorchooser  # noqa
    import tkinter.simpledialog, tkinter.font  # noqa


HERE = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "app", "moddesk.py")
BACKUPS = os.path.join(HERE, "app", "backups")


def box(kind, title, text):
    try:
        import tkinter
        from tkinter import messagebox
        r = tkinter.Tk()
        r.withdraw()
        try:
            if kind == "ask":
                return messagebox.askyesno(title, text)
            messagebox.showerror(title, text)
        finally:
            r.destroy()
    except Exception:  # noqa
        pass
    return False


def newest_backup():
    try:
        files = sorted(f for f in os.listdir(BACKUPS) if f.startswith("moddesk-") and f.endswith(".py"))
        return os.path.join(BACKUPS, files[-1]) if files else None
    except OSError:
        return None


def main():
    if not os.path.exists(APP):
        box("err", "ModDesk", "Cannot find app\\moddesk.py next to ModDesk.exe.\nRun build.bat again, or copy "
                              "moddesk.py into the app folder.")
        return
    import runpy
    try:
        runpy.run_path(APP, run_name="__main__")
    except SystemExit:
        raise
    except BaseException:  # noqa
        err = traceback.format_exc()
        try:
            with open(os.path.join(HERE, "crash.log"), "a", encoding="utf-8") as f:
                f.write("--- launcher ---\n" + err + "\n")
        except OSError:
            pass
        back = newest_backup()
        if back and box("ask", "ModDesk crashed",
                        "ModDesk crashed (details are in crash.log).\n\nRestore the previous version?"):
            import shutil
            import subprocess
            shutil.copy(back, APP)
            subprocess.Popen([sys.executable], cwd=HERE)
        elif not back:
            box("err", "ModDesk crashed", "ModDesk crashed. Details were saved in crash.log next to ModDesk.exe.")


if __name__ == "__main__":
    main()
