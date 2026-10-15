import latex2mathml.converter as c
import subprocess
from pathlib import Path

exprs = [
    r'\text{MAE} = \frac{1}{N} \sum_{i=1}^{N} |y_i - \hat{y}_i| \quad [\text{meters}]',
    r'\mathbf{x}_k = \begin{bmatrix} x_k \\ y_k \\ v_{x,k} \\ v_{y,k} \end{bmatrix} \in \mathbb{R}^4, \quad \mathbf{z}_k = \begin{bmatrix} z_{x,k} \\ z_{y,k} \end{bmatrix} \in \mathbb{R}^2',
    r'F(\Delta t) = \begin{bmatrix} 1 & 0 & \Delta t & 0 \\ 0 & 1 & 0 & \Delta t \\ 0 & 0 & 1 & 0 \\ 0 & 0 & 0 & 1 \end{bmatrix}',
    r'\rho(z) = 2 \left(\sqrt{1 + z} - 1\right)',
    r'\hat{d} = 10^{\frac{A - RSSI}{10n}}',
    r'RSSI(d) = A - 10n \log_{10}(d) + X_\sigma, \quad X_\sigma \sim \mathcal{N}(0, \sigma^2)',
    r'K_k = P_{k|k-1} H^T (H P_{k|k-1} H^T + R)^{-1}',
    r'J_r = \left(1 - \frac{J_{\text{filtered}}}{J_{\text{raw}}}\right) \times 100\%'
]

html_parts = [
    '<!DOCTYPE html><html><head><meta charset="utf-8">',
    '<style>',
    'body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 40px; background: #f8fafc; color: #1e293b; }',
    '.math-box { background: white; padding: 18px 24px; margin: 16px 0; border-radius: 8px; border: 1px solid #e2e8f0; font-size: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }',
    'math { font-size: 1.15em; }',
    '</style></head><body>',
    '<h2>Edge MathML Native Rendering Test</h2>'
]

for e in exprs:
    m = c.convert(e, display='block')
    html_parts.append(f'<div class="math-box">{m}</div>')

html_parts.append('</body></html>')

test_html = Path(r'c:\Users\DEV\Desktop\Dissertation\documentation docs\test_mathml.html')
test_html.write_text('\n'.join(html_parts), encoding='utf-8')

test_png = Path(r'c:\Users\DEV\Desktop\Dissertation\documentation docs\test_mathml.png')
edge_exe = r'C:\Program Files (x86)\Microsoft\EdgeCore\154.0.4258.62\msedge.exe'
cmd = [
    edge_exe,
    '--headless=new',
    '--disable-gpu',
    '--window-size=1000,1200',
    f'--screenshot={test_png}',
    f'file:///{test_html}'
]
res = subprocess.run(cmd, capture_output=True, text=True)
print('Screenshot generated:', test_png.exists())
