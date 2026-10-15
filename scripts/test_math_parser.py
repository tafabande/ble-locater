import re

def parse_balanced_braces(s: str, start_idx: int) -> tuple[str, int]:
    """Extract content inside balanced curly braces starting at start_idx."""
    if start_idx >= len(s) or s[start_idx] != '{':
        return "", start_idx
    depth = 0
    content = []
    i = start_idx
    while i < len(s):
        if s[i] == '{':
            if depth > 0:
                content.append('{')
            depth += 1
        elif s[i] == '}':
            depth -= 1
            if depth == 0:
                return "".join(content), i + 1
            else:
                content.append('}')
        else:
            content.append(s[i])
        i += 1
    return "".join(content), i

def format_math_expr(s: str) -> str:
    s = s.strip()

    # 1. Matrices: \begin{bmatrix} ... \end{bmatrix}
    def replace_matrix(m):
        matrix_content = m.group(1).strip()
        rows = [r.strip() for r in matrix_content.split(r'\\') if r.strip()]
        row_htmls = []
        for r in rows:
            cells = [c.strip() for c in r.split('&')]
            cell_htmls = "".join([f"<td>{format_math_expr(c)}</td>" for c in cells])
            row_htmls.append(f"<tr>{cell_htmls}</tr>")
        table_rows = "".join(row_htmls)
        return (
            '<span class="math-matrix">'
            '<span class="matrix-bracket">[</span>'
            f'<table class="matrix-body">{table_rows}</table>'
            '<span class="matrix-bracket">]</span>'
            '</span>'
        )
    s = re.sub(r'\\begin\{bmatrix\}(.*?)\\end\{bmatrix\}', replace_matrix, s, flags=re.DOTALL)

    # 2. Fractions: \frac{num}{den} with arbitrary nesting
    while r'\frac' in s:
        idx = s.find(r'\frac')
        brace1 = s.find('{', idx)
        if brace1 == -1:
            break
        num, end1 = parse_balanced_braces(s, brace1)
        brace2 = s.find('{', end1 - 1)
        if brace2 == -1:
            break
        den, end2 = parse_balanced_braces(s, brace2)
        num_rendered = format_math_expr(num)
        den_rendered = format_math_expr(den)
        replacement = f'<span class="math-frac"><span class="frac-num">{num_rendered}</span><span class="frac-den">{den_rendered}</span></span>'
        s = s[:idx] + replacement + s[end2:]

    # 3. Square Root: \sqrt{radicand}
    while r'\sqrt' in s:
        idx = s.find(r'\sqrt')
        brace = s.find('{', idx)
        if brace == -1:
            break
        rad, end_idx = parse_balanced_braces(s, brace)
        rad_rendered = format_math_expr(rad)
        replacement = f'<span class="math-sqrt"><span class="sqrt-rad">&radic;</span><span class="sqrt-body">{rad_rendered}</span></span>'
        s = s[:idx] + replacement + s[end_idx:]

    # 4. Text and Fonts
    while r'\text' in s:
        idx = s.find(r'\text')
        brace = s.find('{', idx)
        if brace == -1:
            break
        txt, end_idx = parse_balanced_braces(s, brace)
        replacement = f'<span class="math-text">{txt}</span>'
        s = s[:idx] + replacement + s[end_idx:]

    while r'\mathbf' in s:
        idx = s.find(r'\mathbf')
        brace = s.find('{', idx)
        if brace == -1:
            break
        txt, end_idx = parse_balanced_braces(s, brace)
        replacement = f'<b>{txt}</b>'
        s = s[:idx] + replacement + s[end_idx:]

    # 5. Hats and Bars
    while r'\hat' in s:
        idx = s.find(r'\hat')
        brace = s.find('{', idx)
        if brace == -1:
            break
        txt, end_idx = parse_balanced_braces(s, brace)
        replacement = f'<span class="math-hat">{txt}&#770;</span>'
        s = s[:idx] + replacement + s[end_idx:]

    while r'\bar' in s:
        idx = s.find(r'\bar')
        brace = s.find('{', idx)
        if brace == -1:
            break
        txt, end_idx = parse_balanced_braces(s, brace)
        replacement = f'<span class="math-bar">{txt}&#772;</span>'
        s = s[:idx] + replacement + s[end_idx:]

    # 6. Delimiters
    s = s.replace(r'\left(', '<span class="math-delim">(</span>')
    s = s.replace(r'\right)', '<span class="math-delim">)</span>')
    s = s.replace(r'\left[', '<span class="math-delim">[</span>')
    s = s.replace(r'\right]', '<span class="math-delim">]</span>')
    s = s.replace(r'\%', '%')

    # 7. Symbols
    s = s.replace(r'\mathbb{R}', '&#8477;')
    s = s.replace(r'\le', '&le;').replace(r'\ge', '&ge;')
    s = s.replace(r'\pm', '&plusmn;').replace(r'\times', '&times;')
    s = s.replace(r'\in', '&isin;').replace(r'\rightarrow', '&rarr;').replace(r'\to', '&rarr;')
    s = s.replace(r'\emptyset', '&empty;').replace(r'\cap', '&cap;')
    s = s.replace(r'\sigma', '&sigma;').replace(r'\Delta', '&Delta;')
    s = s.replace(r'\sum', '<span class="math-sum">&sum;</span>')
    s = s.replace(r'\cdot', '&sdot;').replace(r'\quad', '&nbsp;&nbsp;')
    s = s.replace(r'\log', 'log').replace(r'\max', 'max').replace(r'\min', 'min')

    # 8. Subscripts with braces: _{...}
    while '_{' in s:
        idx = s.find('_{')
        txt, end_idx = parse_balanced_braces(s, idx + 1)
        txt_rendered = format_math_expr(txt)
        replacement = f'<sub>{txt_rendered}</sub>'
        s = s[:idx] + replacement + s[end_idx:]

    # Superscripts with braces: ^{...}
    while '^{' in s:
        idx = s.find('^{')
        txt, end_idx = parse_balanced_braces(s, idx + 1)
        txt_rendered = format_math_expr(txt)
        replacement = f'<sup>{txt_rendered}</sup>'
        s = s[:idx] + replacement + s[end_idx:]

    # 9. Simple sub/superscripts without braces (e.g. x_i, y_k, R^2, ^T)
    s = re.sub(r'\^T\b', '<sup>T</sup>', s)
    s = re.sub(r'\^2\b', '<sup>2</sup>', s)
    s = re.sub(r'\^4\b', '<sup>4</sup>', s)
    s = re.sub(r'_([a-zA-Z0-9]+)', r'<sub>\1</sub>', s)
    s = re.sub(r'_(&[a-zA-Z0-9#]+;)', r'<sub>\1</sub>', s)

    return s

def render_math_to_academic_html(text: str) -> str:
    # Convert block math $$...$$
    def replace_block(m):
        content = m.group(1).strip()
        rendered = format_math_expr(content)
        return f'<div class="math-block"><span class="math-expr">{rendered}</span></div>'

    text = re.sub(r'\$\$(.*?)\$\$', replace_block, text, flags=re.DOTALL)

    # Convert inline math $...$
    def replace_inline(m):
        content = m.group(1).strip()
        rendered = format_math_expr(content)
        return f'<span class="math-inline">{rendered}</span>'

    text = re.sub(r'(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)', replace_inline, text)

    return text

if __name__ == "__main__":
    test_cases = [
        r"$$RSSI(d) = A - 10n \log_{10}(d) + X_\sigma$$",
        r"$$\hat{d} = 10^{\frac{A - RSSI}{10n}}$$",
        r"$$e_i = \sqrt{(x_i - \hat{x}_i)^2 + (y_i - \hat{y}_i)^2}$$",
        r"$$J_r = \left(1 - \frac{J_{\text{filtered}}}{J_{\text{raw}}}\right) \times 100\%$$",
        r"$$F(\Delta t) = \begin{bmatrix} 1 & 0 & \Delta t & 0 \\ 0 & 1 & 0 & \Delta t \\ 0 & 0 & 1 & 0 \\ 0 & 0 & 0 & 1 \end{bmatrix}$$",
        r"$$\mathbf{x}_k = [x_k, y_k, v_{x,k}, v_{y,k}]^T \in \mathbb{R}^4, \quad H = \begin{bmatrix} 1 & 0 & 0 & 0 \\ 0 & 1 & 0 & 0 \end{bmatrix}$$",
        r"$$\text{MAE} = \frac{1}{N} \sum_{i=1}^{N} |y_i - \hat{y}_i|$$",
        r"$$J = \sqrt{\frac{1}{N} \sum_{i=1}^{N} \left((x_i - \bar{x})^2 + (y_i - \bar{y})^2\right)}$$"
    ]
    for i, tc in enumerate(test_cases, 1):
        print(f"=== TEST CASE {i} ===")
        print(render_math_to_academic_html(tc))
        print()
