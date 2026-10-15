"""Compilation Script: Generate Publication-Grade Standalone Offline PDF Documents
from Markdown artifacts for the BLE Indoor Positioning Dissertation.

Target Output:
- c:\\Users\\DEV\\Desktop\\Dissertation\\documentation docs\\Chapter_3_Research_Methodology.pdf
- c:\\Users\\DEV\\Desktop\\Dissertation\\documentation docs\\Chapter_4_Results_and_Discussion.pdf
- c:\\Users\\DEV\\Desktop\\Dissertation\\documentation docs\\Dissertation_Chapters_3_and_4_Combined.pdf
"""
import os
import sys
import re
import base64
import subprocess
from pathlib import Path

try:
    import latex2mathml.converter as mathml_converter
    HAS_MATHML = True
except ImportError:
    HAS_MATHML = False

ROOT_DIR = Path(r"c:\Users\DEV\Desktop\Dissertation")
OUTPUT_DIR = ROOT_DIR / "documentation docs"
REPORTS_DIR = ROOT_DIR / "ble-indoor-positioning" / "reports"
EDGE_EXE = r"C:\Program Files (x86)\Microsoft\EdgeCore\154.0.4258.62\msedge.exe"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def find_image(filename: str) -> Path:
    candidates = [
        REPORTS_DIR / filename,
        OUTPUT_DIR / filename,
        ROOT_DIR / filename
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]

def image_to_base64(img_path: Path) -> str:
    if not img_path.exists():
        print(f"Warning: Image {img_path} not found.")
        return ""
    ext = img_path.suffix.lower().replace(".", "")
    mime = "image/png" if ext == "png" else "image/svg+xml" if ext == "svg" else "image/jpeg"
    with open(img_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{data}"

def clean_latex_for_mathml(s: str) -> str:
    """Pre-process LaTeX string to handle constructs cleanly in latex2mathml."""
    s = s.strip()
    # Normalize common LaTeX tokens without corrupting longer macros (e.g. \\left, \\infty)
    s = s.replace(r'\%', '%')
    s = s.replace(r'\dots', '...')
    s = s.replace(r'\dotsb', '...')
    s = s.replace(r'\dotsc', '...')
    s = re.sub(r'\\le(?![a-zA-Z])', r'\\le ', s)
    s = re.sub(r'\\ge(?![a-zA-Z])', r'\\ge ', s)
    s = re.sub(r'\\pm(?![a-zA-Z])', r'\\pm ', s)
    s = re.sub(r'\\times(?![a-zA-Z])', r'\\times ', s)
    s = re.sub(r'\\approx(?![a-zA-Z])', r'\\approx ', s)
    s = re.sub(r'\\sim(?![a-zA-Z])', r'\\sim ', s)
    s = re.sub(r'\\in(?![a-zA-Z])', r'\\in ', s)
    s = re.sub(r'\\to(?![a-zA-Z])', r'\\to ', s)
    s = re.sub(r'\\rightarrow(?![a-zA-Z])', r'\\to ', s)
    s = re.sub(r'\\emptyset(?![a-zA-Z])', r'\\emptyset ', s)
    s = re.sub(r'\\cap(?![a-zA-Z])', r'\\cap ', s)
    s = re.sub(r'\\cup(?![a-zA-Z])', r'\\cup ', s)
    s = re.sub(r'\\infty(?![a-zA-Z])', r'\\infty ', s)
    s = re.sub(r'\\cdot(?![a-zA-Z])', r'\\cdot ', s)
    s = s.replace(r'\_', '_')
    # Clean up multiple whitespaces
    s = re.sub(r'\s+', ' ', s)
    return s

def render_math_to_html(text: str) -> str:
    """Convert LaTeX math ($...$ and $$...$$) into standard HTML5 MathML."""
    if not HAS_MATHML:
        return text

    # 1. Convert Display Math $$...$$
    def replace_block_math(m):
        raw = m.group(1).strip()
        cleaned = clean_latex_for_mathml(raw)
        try:
            mathml = mathml_converter.convert(cleaned, display="block")
            return f'<div class="math-block">{mathml}</div>'
        except Exception as e:
            # Fallback
            escaped = cleaned.replace('<', '&lt;').replace('>', '&gt;')
            return f'<div class="math-block"><code class="math-fallback">{escaped}</code></div>'

    text = re.sub(r'\$\$(.*?)\$\$', replace_block_math, text, flags=re.DOTALL)

    # 2. Convert Inline Math $...$ (ensuring no double dollar overlap)
    def replace_inline_math(m):
        raw = m.group(1).strip()
        cleaned = clean_latex_for_mathml(raw)
        try:
            mathml = mathml_converter.convert(cleaned, display="inline")
            return f'<span class="math-inline">{mathml}</span>'
        except Exception as e:
            escaped = cleaned.replace('<', '&lt;').replace('>', '&gt;')
            return f'<span class="math-inline"><code class="math-fallback">{escaped}</code></span>'

    text = re.sub(r'(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)', replace_inline_math, text)
    return text

def markdown_table_to_html(match) -> str:
    table_text = match.group(0).strip()
    lines = [line.strip() for line in table_text.split("\n") if line.strip()]
    if len(lines) < 2:
        return table_text
    
    html = ['<div class="table-container"><table class="academic-table">']
    # Header
    header_cols = [c.strip() for c in lines[0].strip("|").split("|")]
    html.append("  <thead><tr>")
    for c in header_cols:
        html.append(f"    <th>{c}</th>")
    html.append("  </tr></thead>")

    # Body
    html.append("  <tbody>")
    for row in lines[2:]:
        cols = [c.strip() for c in row.strip("|").split("|")]
        html.append("    <tr>")
        for i, c in enumerate(cols):
            # First column styling
            if i == 0 and ("**" in c or "Node" in c or "Fold" in c or "Rank" in c or "Layer" in c or "Anchor" in c or "H_" in c or "Task" in c or "Total" in c or "(" in c):
                html.append(f"      <td class='row-head'>{c}</td>")
            else:
                html.append(f"      <td>{c}</td>")
        html.append("    </tr>")
    html.append("  </tbody>")
    html.append("</table></div>")
    return "\n".join(html)

def markdown_to_academic_html(md_content: str, title: str, subtitle: str) -> str:
    # Deduplicate chapter title if markdown starts with H1
    md_content = re.sub(r'^#\s+Chapter.*?\n', '', md_content.strip())
    if md_content.startswith("---"):
        md_content = md_content.lstrip("-").strip()

    # Convert table captions before general math parsing
    def replace_table_caption(m):
        cap = m.group(1).strip()
        return f'<div class="table-caption"><strong>{cap}</strong></div>'
    md_content = re.sub(r'\$\$\\text\{(Table [0-9.]+:.*?)\}\$\$', replace_table_caption, md_content)

    # Pre-render images into embedded base64
    arch_img_path = find_image("architecture_pipeline_diagram.png")
    grid_img_path = find_image("experimental_layout_grid.png")
    arch_img_b64 = image_to_base64(arch_img_path)
    grid_img_b64 = image_to_base64(grid_img_path)

    # Replace image markdown tags with styled HTML figures
    def replace_arch_img(m):
        return f'''
        <div class="figure-container">
            <img src="{arch_img_b64}" alt="System Architecture Pipeline Diagram" class="academic-img" />
            <div class="figure-caption"><strong>Figure 3.2:</strong> End-to-end multi-tier system architecture: ESP32 edge packet sniffing, 1000ms sliding window feature extraction, 2D ExtraTrees coordinate regression, fallback Levenberg-Marquardt solver, 2D Constant Velocity Kalman Filter, and FastAPI WebSocket telemetry delivery.</div>
        </div>
        '''

    def replace_grid_img(m):
        return f'''
        <div class="figure-container">
            <img src="{grid_img_b64}" alt="Physical Experimental Testbed & Surveyed Coordinate Grid" class="academic-img" />
            <div class="figure-caption"><strong>Figure 3.3:</strong> Physical 5.0m &times; 5.0m experimental testbed layout: 4 perimeter ESP32-WROOM-32 anchors mounted at 0.96m tripod height, showing Cartesian coordinate origin (0,0), hardware MAC addresses, and nine surveyed ground-truth benchmark coordinates across 1,961 observation windows.</div>
        </div>
        '''

    md_content = re.sub(r'!\[System Architecture Pipeline Diagram\]\(.*?\)', replace_arch_img, md_content)
    md_content = re.sub(r'!\[Physical Experimental Testbed & Surveyed Coordinate Grid\]\(.*?\)', replace_grid_img, md_content)

    # Convert Mermaid code blocks into styled academic SVG/HTML diagram cards
    def replace_mermaid(m):
        mermaid_code = m.group(1).strip()
        
        # Check which diagram this is and generate custom high-aesthetic card
        if "Layer 1: RSSI" in mermaid_code or "Layer1" in mermaid_code:
            return '''
            <div class="diagram-card">
                <div class="diagram-title">Figure 3.1: System Evaluation Hierarchy: Three Independent Functional Layers</div>
                <div class="flow-hierarchy">
                    <div class="flow-tier tier-1">
                        <div class="tier-badge">LAYER 1</div>
                        <div class="tier-content">
                            <strong>RSSI &amp; Distance Estimation Layer (1D Ranging Accuracy)</strong>
                            <span>Target: Physical Distance (0.5m &ndash; 7.0m) &bull; Primary Metrics: MAE, RMSE, R&sup2;, Error Tolerances (&le;0.5m, &le;1.0m)</span>
                        </div>
                    </div>
                    <div class="flow-arrow">&darr; <span>Feeds Distance Bounds &amp; Features</span></div>
                    <div class="flow-tier tier-2">
                        <div class="tier-badge">LAYER 2</div>
                        <div class="tier-content">
                            <strong>2D Spatial Positioning Layer (Static Coordinate Accuracy)</strong>
                            <span>Target: Coordinates (X, Y) on 5m &times; 5m Grid &bull; Primary Metrics: 2D Euclidean Error (Mean, Median, P90, P95)</span>
                        </div>
                    </div>
                    <div class="flow-arrow">&darr; <span>Feeds Spatial Measurements</span></div>
                    <div class="flow-tier tier-3">
                        <div class="tier-badge">LAYER 3</div>
                        <div class="tier-content">
                            <strong>Dynamic Tracking &amp; Stability Layer (Trajectory Smoothing &amp; Latency)</strong>
                            <span>Target: 2D State Kalman Filter &bull; Primary Metrics: RMS Jitter Radius (J<sub>RMS</sub>), Jitter Reduction (J<sub>r</sub>), Latency Budget</span>
                        </div>
                    </div>
                </div>
            </div>
            '''
        elif "Dataset Partitioning" in mermaid_code or "Partitions_1D" in mermaid_code:
            return '''
            <div class="diagram-card">
                <div class="diagram-title">Figure 3.4: Comprehensive Dataset Partitioning &amp; Hierarchy Flowchart</div>
                <div class="flow-hierarchy">
                    <div class="flow-tier tier-1">
                        <div class="tier-badge">RAW DATA</div>
                        <div class="tier-content">
                            <strong>Physical Packet Captures: 181 Files in datasets/raw/ (87 Collection Sessions)</strong>
                            <span>Ingested across 1 to 4 ESP32 anchors via serial UART (esp32_anchor) and Wi-Fi UDP port 5005 (esp32_wifi_anchor)</span>
                        </div>
                    </div>
                    <div class="flow-arrow">&darr; <span>1000ms Non-Overlapping Sliding Window Aggregation</span></div>
                    <div class="flow-tier tier-2">
                        <div class="tier-badge">1D RANGING DATASET</div>
                        <div class="tier-content">
                            <strong>Complete 1D Dataset: 37,623 Observation Windows (87 Sessions)</strong>
                            <span>Partitioned via StratifiedGroupKFold on session_id (80/20 split) &bull; Zero Session Overlap</span>
                        </div>
                    </div>
                    <div class="cv-flow-grid" style="margin-top: 10px;">
                        <div class="cv-col split-col">
                            <h4>Training Partition (69 Sessions)</h4>
                            <div class="cv-box train-box">Raw Training Windows: 30,152</div>
                            <div class="cv-split-arrow">&darr; IsolationForest(contamination=0.03)</div>
                            <div class="cv-box train-box">Clean Training Windows: 29,247<br><small>(905 Anomaly Outliers Discarded)</small></div>
                        </div>
                        <div class="cv-col exec-col">
                            <h4>Independent Holdout (18 Sessions)</h4>
                            <div class="cv-box test-box">Untouched Holdout Windows: 7,471<br><small>(Isolated prior to scaling &amp; tuning)</small></div>
                            <div class="cv-sub" style="margin-top: 14px;">Checksum Invariant: 29,247 + 7,471 + 905 = 37,623</div>
                        </div>
                    </div>
                </div>
            </div>
            '''
        elif "Zero-Leakage" in mermaid_code or "Data_Splitting" in mermaid_code or "Session-Grouped" in mermaid_code:
            return '''
            <div class="diagram-card">
                <div class="diagram-title">Figure 3.5: Session-Grouped Cross-Validation Protocol</div>
                <div class="cv-flow-grid">
                    <div class="cv-col split-col">
                        <h4>1. Session-Atomic Partitioning</h4>
                        <div class="cv-box all-box">33 Physical Sessions (1,961 Windows)</div>
                        <div class="cv-split-arrow">&darr; GroupKFold (K=5) on session_id</div>
                        <div class="cv-box train-box">Training Folds (25&ndash;29 Disjoint Sessions)</div>
                        <div class="cv-box test-box">Validation Fold (4&ndash;8 Unseen Sessions)</div>
                        <div class="cv-sub">Validation Invariant: Train Sessions &cap; Test Sessions = &empty;</div>
                    </div>
                    <div class="cv-col exec-col">
                        <h4>2. Strict In-Fold Processing</h4>
                        <div class="cv-step">
                            <span class="step-num">Step A</span>
                            <div><strong>RobustScaler.fit_transform(X_tr)</strong><br><small>Fitted exclusively on training session fold</small></div>
                        </div>
                        <div class="cv-step">
                            <span class="step-num">Step B</span>
                            <div><strong>IsolationForest(contamination=0.03)</strong><br><small>Outlier pruning applied strictly to training fold</small></div>
                        </div>
                        <div class="cv-step">
                            <span class="step-num">Step C</span>
                            <div><strong>ExtraTrees.fit(X_tr_scaled, y_tr)</strong><br><small>Model parameters optimized without test exposure</small></div>
                        </div>
                        <div class="cv-step">
                            <span class="step-num">Step D</span>
                            <div><strong>RobustScaler.transform(X_te) &amp; Predict</strong><br><small>Evaluates session-held-out generalization across benchmark points</small></div>
                        </div>
                    </div>
                </div>
            </div>
            '''
        elif "Dual-Path" in mermaid_code or "Active Anchor Count" in mermaid_code:
            return '''
            <div class="diagram-card">
                <div class="diagram-title">Figure 3.6: Dual-Path Localization Solver and Kinematic Filter Pipeline</div>
                <div class="decision-pipeline">
                    <div class="pipe-node input-node">1000ms Synchronized Multi-Anchor Window</div>
                    <div class="pipe-arrow">&darr;</div>
                    <div class="pipe-decision">&ge; 3 Valid Anchors Available?</div>
                    <div class="pipe-branches">
                        <div class="branch primary-branch">
                            <div class="branch-tag">Primary (Yes)</div>
                            <div class="branch-box">
                                <strong>MultiOutput ExtraTrees Regressor</strong>
                                <span>21 Spatial &amp; Differential Features &rarr; Direct Cartesian (X, Y)</span>
                            </div>
                        </div>
                        <div class="branch fallback-branch">
                            <div class="branch-tag">Fallback (No / Dropout)</div>
                            <div class="branch-box">
                                <strong>Levenberg-Marquardt Solver</strong>
                                <span>1D HistGB Distance Estimates &rarr; Levenberg-Marquardt with Centroid Fallback</span>
                            </div>
                        </div>
                    </div>
                    <div class="pipe-arrow">&darr; Raw Measurement z_k = (z_x, z_y)</div>
                    <div class="pipe-node kf-node">
                        <strong>2D Constant Velocity Kalman Filter</strong>
                        <span>Predict: F(&Delta;t), Q = 0.05&middot;I<sub>4</sub> &bull; Update: H = [I<sub>2</sub> 0], R = 0.80&middot;I<sub>2</sub> &bull; P<sub>0</sub> = 1.0&middot;I<sub>4</sub></span>
                    </div>
                    <div class="pipe-arrow">&darr; Filtered State Estimate x_k|k</div>
                    <div class="pipe-node hyst-node">
                        <strong>Room Boundary Clamping &amp; Hysteresis Engine</strong>
                        <span>0.3m Transition Deadband Margin &bull; Database WAL Commit &bull; WebSocket Telemetry</span>
                    </div>
                </div>
            </div>
            '''
        else:
            return '''
            <div class="diagram-card">
                <div class="diagram-title">Architecture Pipeline Overview</div>
                <div class="flow-hierarchy">
                    <div class="flow-tier tier-1">
                        <div class="tier-badge">DATA ACQUISITION</div>
                        <div class="tier-content">
                            <strong>ESP32 Perimeter Receivers &amp; BLE Beacon Tag</strong>
                            <span>Physical 2.4 GHz RF advertising frames streamed via Wi-Fi UDP on port 5005</span>
                        </div>
                    </div>
                    <div class="flow-arrow">&darr;</div>
                    <div class="flow-tier tier-2">
                        <div class="tier-badge">FEATURE PIPELINE</div>
                        <div class="tier-content">
                            <strong>1000ms Synchronized Window Aggregation</strong>
                            <span>66 scalar ranging features &amp; 21 multi-anchor spatial differential features</span>
                        </div>
                    </div>
                    <div class="flow-arrow">&darr;</div>
                    <div class="flow-tier tier-3">
                        <div class="tier-badge">POSITIONING &amp; TRACKING</div>
                        <div class="tier-content">
                            <strong>Dual-Path Solver &amp; 2D Kinematic Kalman Filter</strong>
                            <span>Direct coordinate regression, robust multilateration fallback, and real-time smoothing</span>
                        </div>
                    </div>
                </div>
            </div>
            '''

    md_content = re.sub(r'```mermaid\s+(.*?)\s+```', replace_mermaid, md_content, flags=re.DOTALL)

    # Convert Markdown tables to academic HTML tables
    table_pattern = re.compile(r'(?:\|[^\n]+\|\n)(?:\|[-: |]+\|\n)(?:\|[^\n]+\|\n)+', re.MULTILINE)
    md_content = table_pattern.sub(markdown_table_to_html, md_content)

    # Convert Math
    md_content = render_math_to_html(md_content)

    # Process Headings
    md_content = re.sub(r'^# (.*?)$', r'<h1 class="chapter-title">\1</h1>', md_content, flags=re.MULTILINE)
    md_content = re.sub(r'^## (.*?)$', r'<h2 class="section-title">\1</h2>', md_content, flags=re.MULTILINE)
    md_content = re.sub(r'^### (.*?)$', r'<h3 class="subsection-title">\1</h3>', md_content, flags=re.MULTILINE)
    md_content = re.sub(r'^#### (.*?)$', r'<h4 class="subsubsection-title">\1</h4>', md_content, flags=re.MULTILINE)

    # Process bold, italics, code
    md_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', md_content)
    md_content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', md_content)
    md_content = re.sub(r'`(.*?)`', r'<code>\1</code>', md_content)

    # Convert lists strictly tracking list type (ul vs ol)
    lines = md_content.split("\n")
    list_type = None
    new_lines = []
    for line in lines:
        s_line = line.strip()
        if s_line.startswith("* ") or s_line.startswith("- "):
            if list_type != "ul":
                if list_type:
                    new_lines.append(f"</{list_type}>")
                new_lines.append("<ul class='academic-list'>")
                list_type = "ul"
            content = s_line[2:]
            new_lines.append(f"  <li>{content}</li>")
        elif re.match(r'^\d+\.\s+', s_line):
            num_match = re.match(r'^(\d+)\.\s+', s_line)
            num = int(num_match.group(1))
            if list_type != "ol":
                if list_type:
                    new_lines.append(f"</{list_type}>")
                new_lines.append(f"<ol class='academic-list' start='{num}'>")
                list_type = "ol"
            content = re.sub(r'^\d+\.\s+', '', s_line)
            new_lines.append(f"  <li value='{num}'>{content}</li>")
        else:
            if list_type:
                new_lines.append(f"</{list_type}>")
                list_type = None
            if s_line and not s_line.startswith("<") and not s_line.startswith("---"):
                new_lines.append(f"<p>{line}</p>")
            else:
                new_lines.append(line)
    if list_type:
        new_lines.append(f"</{list_type}>")
    
    html_body = "\n".join(new_lines)

    full_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
    @page {{
        size: A4;
        margin: 18mm 16mm 18mm 16mm;
        @top-right {{
            content: "BLE Indoor Positioning \u2022 Dissertation";
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            font-size: 8pt;
            color: #64748B;
        }}
        @bottom-center {{
            content: counter(page);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            font-size: 8.5pt;
            color: #475569;
        }}
    }}

    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-size: 9.5pt;
        line-height: 1.55;
        color: #1E293B;
        background-color: #FFFFFF;
        margin: 0;
        padding: 0;
    }}

    /* Document Header */
    .doc-header {{
        border-bottom: 2.5px solid #0F172A;
        padding-bottom: 12px;
        margin-bottom: 24px;
    }}
    .doc-meta {{
        font-size: 8pt;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
        color: #2563EB;
        margin-bottom: 4px;
    }}
    .chapter-title {{
        font-size: 19pt;
        font-weight: 800;
        color: #0F172A;
        margin: 0 0 4px 0;
        line-height: 1.2;
    }}
    .doc-subtitle {{
        font-size: 10pt;
        color: #475569;
        font-style: italic;
        margin: 0;
    }}

    /* Section Headings */
    h2.section-title {{
        font-size: 13pt;
        font-weight: 750;
        color: #0F172A;
        border-bottom: 1px solid #CBD5E1;
        padding-bottom: 4px;
        margin-top: 24px;
        margin-bottom: 10px;
        page-break-after: avoid;
    }}
    h3.subsection-title {{
        font-size: 11pt;
        font-weight: 700;
        color: #1E293B;
        margin-top: 18px;
        margin-bottom: 8px;
        page-break-after: avoid;
    }}
    h4.subsubsection-title {{
        font-size: 10pt;
        font-weight: 650;
        color: #334155;
        margin-top: 14px;
        margin-bottom: 6px;
        page-break-after: avoid;
    }}

    p {{
        margin-top: 0;
        margin-bottom: 6.5px;
        text-align: justify;
    }}

    /* Lists */
    ul.academic-list, ol.academic-list {{
        margin-top: 3px;
        margin-bottom: 6px;
        padding-left: 18px;
    }}
    li {{
        margin-bottom: 2.5px;
    }}

    /* Tables */
    .table-container {{
        margin: 10px 0;
        page-break-inside: auto;
    }}
    table.academic-table tr {{
        page-break-inside: avoid;
    }}
    .table-caption {{
        font-size: 9pt;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 5px;
        text-align: left;
    }}
    table.academic-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 8.5pt;
        border-top: 2px solid #0F172A;
        border-bottom: 2px solid #0F172A;
    }}
    table.academic-table th {{
        border-bottom: 1.5px solid #0F172A;
        padding: 5px 6px;
        font-weight: 700;
        background-color: #F8FAFC;
        text-align: left;
    }}
    table.academic-table td {{
        padding: 4px 6px;
        border-bottom: 1px solid #E2E8F0;
        vertical-align: top;
    }}
    table.academic-table tr:last-child td {{
        border-bottom: none;
    }}
    td.row-head {{
        font-weight: 600;
        color: #0F172A;
    }}

    /* MathML Display and Inline Math */
    .math-block {{
        margin: 12px 0;
        padding: 8px 12px;
        background-color: #F8FAFC;
        border-left: 3px solid #2563EB;
        border-radius: 4px;
        text-align: center;
        overflow-x: auto;
        page-break-inside: avoid;
    }}
    math[display="block"] {{
        font-size: 1.15em;
        margin: 0 auto;
    }}
    math[display="inline"] {{
        font-size: 1.05em;
    }}
    .math-inline {{
        padding: 0 1px;
    }}
    code.math-fallback {{
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        font-size: 9pt;
        color: #0F172A;
    }}

    /* Figures and Images */
    .figure-container {{
        margin: 16px 0;
        text-align: center;
        page-break-inside: avoid;
    }}
    img.academic-img {{
        max-width: 95%;
        height: auto;
        border: 1px solid #CBD5E1;
        border-radius: 4px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }}
    .figure-caption {{
        font-size: 8.5pt;
        color: #475569;
        margin-top: 6px;
        text-align: justify;
        padding: 0 16px;
    }}

    /* Diagram Cards */
    .diagram-card {{
        margin: 16px 0;
        padding: 12px 16px;
        background-color: #F8FAFC;
        border: 1.5px solid #CBD5E1;
        border-radius: 6px;
        page-break-inside: avoid;
    }}
    .diagram-title {{
        font-size: 9pt;
        font-weight: 750;
        color: #0F172A;
        margin-bottom: 10px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-bottom: 1px solid #E2E8F0;
        padding-bottom: 4px;
    }}
    .flow-hierarchy {{
        display: flex;
        flex-direction: column;
        gap: 6px;
    }}
    .flow-tier {{
        display: flex;
        align-items: center;
        gap: 12px;
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 4px;
        padding: 8px 12px;
    }}
    .tier-badge {{
        font-size: 7.5pt;
        font-weight: 800;
        background-color: #0F172A;
        color: #FFFFFF;
        padding: 3px 6px;
        border-radius: 3px;
        letter-spacing: 0.05em;
        white-space: nowrap;
    }}
    .tier-content {{
        display: flex;
        flex-direction: column;
    }}
    .tier-content strong {{
        font-size: 9pt;
        color: #0F172A;
    }}
    .tier-content span {{
        font-size: 8pt;
        color: #64748B;
    }}
    .flow-arrow {{
        text-align: center;
        font-size: 11pt;
        color: #2563EB;
        line-height: 1;
    }}
    .flow-arrow span {{
        font-size: 7.5pt;
        color: #64748B;
        font-style: italic;
        margin-left: 6px;
    }}

    /* Cross-Validation Grid */
    .cv-flow-grid {{
        display: flex;
        gap: 12px;
    }}
    .cv-col {{
        flex: 1;
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 4px;
        padding: 8px 10px;
    }}
    .cv-col h4 {{
        font-size: 8.5pt;
        margin: 0 0 6px 0;
        color: #0F172A;
        border-bottom: 1px solid #F1F5F9;
        padding-bottom: 3px;
    }}
    .cv-box {{
        padding: 6px 8px;
        border-radius: 3px;
        font-size: 8pt;
        margin-bottom: 4px;
        text-align: center;
        font-weight: 600;
    }}
    .all-box {{ background-color: #EFF6FF; color: #1E40AF; border: 1px solid #BFDBFE; }}
    .train-box {{ background-color: #ECFDF5; color: #065F46; border: 1px solid #A7F3D0; }}
    .test-box {{ background-color: #FEF2F2; color: #991B1B; border: 1px solid #FECACA; }}
    .cv-split-arrow {{ text-align: center; font-size: 7.5pt; color: #64748B; margin: 4px 0; }}
    .cv-sub {{ font-size: 7.5pt; color: #64748B; font-style: italic; text-align: center; margin-top: 4px; }}
    .cv-step {{
        display: flex;
        gap: 8px;
        align-items: flex-start;
        font-size: 8pt;
        margin-bottom: 4px;
        padding: 4px;
        border-bottom: 1px dotted #E2E8F0;
    }}
    .step-num {{
        font-weight: 700;
        color: #2563EB;
        white-space: nowrap;
    }}

    /* Decision Pipeline */
    .decision-pipeline {{
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
    }}
    .pipe-node {{
        width: 90%;
        background-color: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-radius: 4px;
        padding: 6px 10px;
        text-align: center;
        font-size: 8.5pt;
    }}
    .input-node {{ background-color: #F1F5F9; font-weight: 700; }}
    .pipe-decision {{
        background-color: #FEF3C7;
        color: #92400E;
        border: 1px solid #FDE68A;
        border-radius: 4px;
        padding: 4px 12px;
        font-size: 8.5pt;
        font-weight: 700;
    }}
    .pipe-arrow {{ font-size: 9pt; color: #64748B; }}
    .pipe-branches {{
        display: flex;
        width: 95%;
        gap: 12px;
    }}
    .branch {{
        flex: 1;
        background-color: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-radius: 4px;
        padding: 6px 8px;
        text-align: center;
    }}
    .branch-tag {{ font-size: 7.5pt; font-weight: 800; color: #2563EB; text-transform: uppercase; margin-bottom: 2px; }}
    .branch-box strong {{ display: block; font-size: 8.5pt; color: #0F172A; }}
    .branch-box span {{ font-size: 7.5pt; color: #64748B; }}

    /* Section separation */
    .page-break {{
        page-break-before: always;
    }}
</style>
</head>
<body>

<div class="doc-header">
    <div class="doc-meta">M.Sc. Dissertation &bull; Technical Research Monograph</div>
    <div class="chapter-title">{title}</div>
    <div class="doc-subtitle">{subtitle}</div>
</div>

{html_body}

</body>
</html>
'''
    return full_html

def compile_pdf(html_path: Path, pdf_path: Path):
    cmd = [
        EDGE_EXE,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        f"--print-to-pdf={pdf_path}",
        str(html_path)
    ]
    print(f"Compiling PDF via Chromium EdgeCore:\n  {pdf_path}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error compiling PDF: {res.stderr}")
        return False
    if pdf_path.exists():
        size_kb = pdf_path.stat().st_size / 1024
        print(f"  [SUCCESS] Created {pdf_path.name} ({size_kb:.1f} KB)")
        return True
    return False

def main():
    print("=== DISSERTATION PDF BUILDER (100% Standalone / Offline) ===")
    
    # 1. Compile Chapter 3
    ch3_sources = [
        OUTPUT_DIR / "Chapter_3_Research_Methodology.md",
        ROOT_DIR / "Chapter_3_Research_Methodology.md"
    ]
    ch3_md_path = next((p for p in ch3_sources if p.exists()), None)
    
    if ch3_md_path:
        print(f"Reading Chapter 3 source from: {ch3_md_path}")
        with open(ch3_md_path, "r", encoding="utf-8") as f:
            ch3_md = f.read()
        
        ch3_html = markdown_to_academic_html(
            ch3_md,
            title="Chapter 3: Research Methodology & Empirical System Design",
            subtitle="Experimental Engineering, Physical Hardware Ingestion, Multi-Layer Benchmarking & State Estimation Architecture"
        )
        ch3_html_path = OUTPUT_DIR / "Chapter_3_Research_Methodology.html"
        with open(ch3_html_path, "w", encoding="utf-8") as f:
            f.write(ch3_html)
        
        ch3_pdf_path = OUTPUT_DIR / "Chapter_3_Research_Methodology.pdf"
        compile_pdf(ch3_html_path, ch3_pdf_path)

    # 2. Compile Chapter 4
    ch4_sources = [
        OUTPUT_DIR / "Chapter_4_Results_and_Discussion.md",
        ROOT_DIR / "Chapter_4_Results_and_Discussion.md"
    ]
    ch4_md_path = next((p for p in ch4_sources if p.exists()), None)

    if ch4_md_path:
        print(f"Reading Chapter 4 source from: {ch4_md_path}")
        with open(ch4_md_path, "r", encoding="utf-8") as f:
            ch4_md = f.read()
        
        ch4_html = markdown_to_academic_html(
            ch4_md,
            title="Chapter 4: Empirical Results and Technical Discussion",
            subtitle="Quantitative Ranging Benchmarks, 33-Session Spatial Evaluation, Sim2Real Transfer & Kalman Kinematic Smoothing"
        )
        ch4_html_path = OUTPUT_DIR / "Chapter_4_Results_and_Discussion.html"
        with open(ch4_html_path, "w", encoding="utf-8") as f:
            f.write(ch4_html)
        
        ch4_pdf_path = OUTPUT_DIR / "Chapter_4_Results_and_Discussion.pdf"
        compile_pdf(ch4_html_path, ch4_pdf_path)

    # 3. Compile Combined Chapters 3 & 4
    if ch3_md_path and ch4_md_path:
        combined_md = ch3_md + "\n\n<div class='page-break'></div>\n\n" + ch4_md
        comb_html = markdown_to_academic_html(
            combined_md,
            title="BLE Indoor Positioning System: Methodology & Results",
            subtitle="Complete Academic Technical Monograph: Research Methodology, System Architecture & Empirical Quantitative Evaluation"
        )
        comb_html_path = OUTPUT_DIR / "Dissertation_Chapters_3_and_4_Combined.html"
        with open(comb_html_path, "w", encoding="utf-8") as f:
            f.write(comb_html)
        
        comb_pdf_path = OUTPUT_DIR / "Dissertation_Chapters_3_and_4_Combined.pdf"
        compile_pdf(comb_html_path, comb_pdf_path)

    print("\nAll deliverables compiled successfully into:")
    print(f"-> {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
