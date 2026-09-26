import os
import sys
from pathlib import Path

# Ensure TCL_LIBRARY and TK_LIBRARY are set for Windows environments
if sys.platform == "win32":
    tcl_candidates = [
        Path(sys.base_prefix) / "tcl" / "tcl8.6",
        Path("C:/Espressif/tools/python/tcl/tcl8.6"),
        Path(sys.prefix) / "tcl" / "tcl8.6",
    ]
    tk_candidates = [
        Path(sys.base_prefix) / "tcl" / "tk8.6",
        Path("C:/Espressif/tools/python/tcl/tk8.6"),
        Path(sys.prefix) / "tcl" / "tk8.6",
    ]
    for tcl_dir in tcl_candidates:
        if tcl_dir.exists():
            os.environ.setdefault("TCL_LIBRARY", str(tcl_dir))
            break
    for tk_dir in tk_candidates:
        if tk_dir.exists():
            os.environ.setdefault("TK_LIBRARY", str(tk_dir))
            break
