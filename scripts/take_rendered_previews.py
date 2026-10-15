import subprocess
from pathlib import Path

EDGE_EXE = r"C:\Program Files (x86)\Microsoft\EdgeCore\154.0.4258.62\msedge.exe"
HTML_PATH = Path(r"c:\Users\DEV\Desktop\Dissertation\documentation docs\Chapter_3_Research_Methodology.html")
OUT_DIR = Path(r"c:\Users\DEV\Desktop\Dissertation\documentation docs")

offsets = [
    ("ch3_preview_rq_numbering.png", 400),
    ("ch3_preview_table_66_features.png", 7200),
    ("ch3_preview_solver_reconciliation.png", 12000),
    ("ch3_preview_metrics_and_limits.png", 16500),
]

for name, scroll_y in offsets:
    wrapper_html = OUT_DIR / f"wrap_{name}.html"
    wrapper_html.write_text(f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;overflow:hidden;">
        <iframe id="f" src="file:///{HTML_PATH}" style="width:1200px;height:22000px;border:none;margin-top:-{scroll_y}px;"></iframe>
    </body>
    </html>
    """, encoding="utf-8")
    
    cmd = [
        EDGE_EXE,
        "--headless=new",
        "--disable-gpu",
        "--window-size=1200,1600",
        f"--screenshot={OUT_DIR / name}",
        f"file:///{wrapper_html}"
    ]
    subprocess.run(cmd, capture_output=True)
    if wrapper_html.exists():
        wrapper_html.unlink()
    print(f"Generated {name}:", (OUT_DIR / name).exists())
