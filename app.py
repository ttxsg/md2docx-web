import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, Response, JSONResponse

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

  <p style="color:#666;">
    提示：公式用 <code>$...$</code> 或 <code>$$...$$</code>，会转为 Word 原生公式（OMML）。
  </p>

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

- 列表项 1
- 列表项 2
</textarea>
    <p><button type="submit">开始转换</button></p>
  </form>

  <hr/>
  <p>健康检查：<a href="/health" target="_blank">/health</a></p>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML


def run_pandoc(md_path: Path, out_docx: Path, ref_docx: Optional[Path]) -> None:
    """
    调用 pandoc 将 Markdown 转为 docx。
    失败时抛出包含 stdout/stderr 的异常，便于在 Render logs 里定位问题。
    """
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
        raise RuntimeError(
            "Pandoc failed.\n"
            f"CMD: {' '.join(cmd)}\n"
            f"STDOUT:\n{r.stdout}\n"
            f"STDERR:\n{r.stderr}\n"
        )

    if not out_docx.exists():
        raise RuntimeError("Pandoc returned 0 but output.docx not found.")


@app.get("/health")
def health():
    """
    用来确认 pandoc 是否可用（Render 部署后打开 /health 看 rc 是否为 0）。
    """
    try:
        r = subprocess.run(["pandoc", "--version"], capture_output=True, text=True)
        return {
            "ok": True,
            "pandoc_rc": r.returncode,
            "pandoc_stdout_head": (r.stdout or "")[:300],
            "pandoc_stderr_head": (r.stderr or "")[:300],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/convert")
async def convert(
    md: str = Form(...),
    stem: str = Form("output"),
    reference: UploadFile | None = File(None),
):
    """
    接收 Markdown（和可选 reference.docx 模板），生成 docx 并直接返回二进制下载。
    使用 Response(bytes) 避免 TemporaryDirectory 在响应发送前被清理导致找不到文件。
    """
    stem = (stem or "output").strip() or "output"

    # 简单限制：防止超大内容把免费实例拖死（你可按需调整）
    if len(md.encode("utf-8")) > 2_000_000:  # 约 2MB
        return JSONResponse(status_code=413, content={"error": "Markdown 内容过大（>2MB），请缩小后再试。"})
    if reference is not None and reference.filename:
        # 限制模板大小（可按需调整）
        ref_bytes = await reference.read()
        if len(ref_bytes) > 5_000_000:  # 约 5MB
            return JSONResponse(status_code=413, content={"error": "reference.docx 过大（>5MB），请缩小后再试。"})
    else:
        ref_bytes = None

    try:
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            md_path = td / f"{stem}.md"
            out_docx = td / f"{stem}.docx"

            md_path.write_text(md, encoding="utf-8")

            ref_path = None
            if ref_bytes is not None:
                ref_path = td / "reference.docx"
                ref_path.write_bytes(ref_bytes)

            run_pandoc(md_path, out_docx, ref_path)

            data = out_docx.read_bytes()

        # 直接返回 bytes，避免临时目录清理导致 FileResponse 找不到文件
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{stem}.docx"'},
        )

    except Exception as e:
        # 让 Render logs 里能看到真正错误
        return JSONResponse(status_code=500, content={"error": str(e)})
