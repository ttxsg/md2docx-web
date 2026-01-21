import os
import subprocess
import tempfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse

app = FastAPI()


HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Markdown → Word（Pandoc）</title>
</head>
<body style="max-width:900px;margin:40px auto;font-family:Arial,Helvetica,sans-serif;">
  <h2>Markdown → Word（docx）</h2>
  <form action="/convert" method="post" enctype="multipart/form-data">
    <p>输出文件名（不含后缀）：<input name="stem" value="output" /></p>
    <p>模板 reference.docx（可选）：<input type="file" name="reference" accept=".docx" /></p>
    <p>Markdown：</p>
    <textarea name="md" rows="18" style="width:100%;"># 示例

行内公式：$E=mc^2$

块级公式：

$$
\\mathbf{r}_P = \\mathcal{F}(M(t)\\,\\mathbf{r}_{ECEF})
$$
</textarea>
    <p><button type="submit">开始转换</button></p>
  </form>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    return HTML


def run_pandoc(md_path: Path, out_docx: Path, ref_docx: Path | None):
    from_format = "markdown+tex_math_dollars+tex_math_single_backslash+raw_tex"
    cmd = [
        "pandoc",
        str(md_path),
        "-f", from_format,
        "-t", "docx",
        "-o", str(out_docx),
        "--standalone",
    ]
    if ref_docx is not None:
        cmd += ["--reference-doc", str(ref_docx)]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr or r.stdout)


@app.post("/convert")
async def convert(
    md: str = Form(...),
    stem: str = Form("output"),
    reference: UploadFile | None = File(None),
):
    stem = (stem or "output").strip()
    if not stem:
        stem = "output"

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        md_path = td / f"{stem}.md"
        out_docx = td / f"{stem}.docx"
        md_path.write_text(md, encoding="utf-8")

        ref_path = None
        if reference and reference.filename:
            ref_path = td / "reference.docx"
            ref_path.write_bytes(await reference.read())

        run_pandoc(md_path, out_docx, ref_path)

        # 返回下载
        return FileResponse(
            path=str(out_docx),
            filename=f"{stem}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
