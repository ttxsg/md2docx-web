import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, Response, JSONResponse, PlainTextResponse

app = FastAPI()

AI_MD_GUIDE = """# 请你在生成最终答案时，把“整篇输出”放进一个 Markdown 代码块里返回（也就是用三反引号包起来），方便我直接复制到代码编辑器。

【非常重要：输出格式】
- 你的最终回复必须是且仅是：一个代码块（不要任何额外解释、不要前言、不要“下面是…”）。
- 代码块语言标注请用 markdown：```markdown

【代码块内的内容要求】
你在代码块内输出一份 Pandoc 友好的 Markdown 文档（用于转 Word/docx），并严格遵守以下规则：

1. **基本格式**：
   - 标题使用 # / ## / ###（不要用“1.”当作标题）。
   - 段落之间空一行。
   - 列表用 - 或 1.，子级缩进用 4 个空格。
   - 引用用纯文本 [1] [2]（不要 BibTeX）。
   - 不要使用 HTML 标签（如 <br> <span>）。

2. **公式编写规范 (重点)**：
   - 行内公式：$...$
   - 独立公式：
     $$
     ...公式...
     $$
   - **严禁**使用 \\[ \\] 或 \\( \\) 形式。

3. **【关键：公式兼容性规范 (Pandoc -> Word)】** (必须严格执行以避免乱码框)：
   - **禁止负间距**：绝对**不要**使用 `\\!` (负空格)。Word 无法渲染它，会出现矩形框。
   - **禁止空基底**：绝对**不要**使用 `{}^T` 或 `{}_i` 这种空组写法。
     - ❌ 错误：`\\mathbf{n}'_j{}^T`
     - ✅ 正确：`{\\mathbf{n}'_j}^T` (必须用花括号包裹住左边的完整基底)。
   - **清洗隐形字符**：输出必须是纯净的 ASCII/UTF-8 文本，**严禁**包含零宽空格 (Zero Width Space)、不换行空格 (NBSP) 或任何 PDF 复制产生的控制字符。
   - **函数名**：使用 `\\operatorname{dist}` 或 `\\mathrm{dist}`，不要用 `\\text{dist}` 配合手动空格。

现在请根据我提供的内容生成最终文档：
（我将粘贴原始内容）
"""

HTML = r"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Markdown → Word（Pandoc）</title>
  <style>
    :root{
      --bg:#0b1220;
      --card:#0f1a30;
      --muted:#93a4c7;
      --text:#e9eefc;
      --brand:#4f8cff;
      --brand2:#63d4ff;
      --border:rgba(255,255,255,.10);
      --shadow: 0 14px 40px rgba(0,0,0,.35);
      --radius:18px;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      --sans: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, "Microsoft YaHei", Arial, "Noto Sans", "PingFang SC";
    }
    *{box-sizing:border-box}
    body{
      margin:0;
      font-family:var(--sans);
      color:var(--text);
      background:
        radial-gradient(1200px 600px at 20% 0%, rgba(79,140,255,.25), transparent 60%),
        radial-gradient(900px 500px at 80% 0%, rgba(99,212,255,.18), transparent 60%),
        linear-gradient(180deg, var(--bg), #060a13 70%);
      min-height:100vh;
    }
    .wrap{max-width:1100px;margin:0 auto;padding:34px 18px 48px}
    .header{
      display:flex;gap:14px;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;
      margin-bottom:18px
    }
    .title{
      display:flex;flex-direction:column;gap:6px
    }
    .title h1{
      font-size:22px;margin:0;letter-spacing:.2px
    }
    .title p{
      margin:0;color:var(--muted);font-size:13px;line-height:1.5
    }
    .pill{
      display:inline-flex;gap:8px;align-items:center;
      padding:10px 12px;border:1px solid var(--border);
      border-radius:999px;background:rgba(255,255,255,.04);
      color:var(--muted);font-size:12px
    }
    .grid{
      display:grid;
      grid-template-columns: 1.2fr .8fr;
      gap:16px;
      align-items:start;
    }
    @media (max-width: 920px){
      .grid{grid-template-columns:1fr}
    }
    .card{
      background:rgba(15,26,48,.82);
      border:1px solid var(--border);
      border-radius:var(--radius);
      box-shadow:var(--shadow);
      overflow:hidden;
    }
    .card .hd{
      padding:14px 16px;
      border-bottom:1px solid var(--border);
      display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;
    }
    .card .hd b{font-size:14px}
    .card .bd{padding:16px}
    label{display:block;font-size:12px;color:var(--muted);margin:0 0 6px}
    input[type="text"], textarea{
      width:100%;
      border:1px solid var(--border);
      background:rgba(255,255,255,.03);
      color:var(--text);
      border-radius:12px;
      padding:11px 12px;
      outline:none;
    }
    textarea{
      min-height:360px;
      resize:vertical;
      font-family:var(--mono);
      font-size:13px;
      line-height:1.45;
      white-space:pre;
    }
    input[type="file"]{
      width:100%;
      padding:8px 10px;
      border:1px dashed var(--border);
      border-radius:12px;
      background:rgba(255,255,255,.02);
      color:var(--muted);
    }
    .row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
    @media (max-width: 560px){ .row{grid-template-columns:1fr} }
    .btnbar{display:flex;gap:10px;flex-wrap:wrap}
    button{
      border:1px solid var(--border);
      background:rgba(255,255,255,.05);
      color:var(--text);
      border-radius:12px;
      padding:10px 12px;
      cursor:pointer;
      font-weight:600;
      font-size:13px;
      transition:transform .06s ease, background .15s ease, border-color .15s ease;
    }
    button:hover{background:rgba(255,255,255,.08);border-color:rgba(255,255,255,.16)}
    button:active{transform:translateY(1px)}
    .primary{
      background:linear-gradient(135deg, rgba(79,140,255,.95), rgba(99,212,255,.75));
      border-color:rgba(255,255,255,.18);
      color:#071021;
    }
    .primary:hover{filter:brightness(1.03)}
    .danger{border-color:rgba(255,100,100,.25)}
    .muted{color:var(--muted);font-size:12px;line-height:1.5}
    .mono{font-family:var(--mono)}
    .hr{height:1px;background:var(--border);margin:14px 0}
    .toast{
      position:fixed;right:16px;bottom:16px;
      background:rgba(10,16,28,.92);
      border:1px solid var(--border);
      color:var(--text);
      border-radius:14px;
      padding:12px 12px;
      box-shadow:0 10px 25px rgba(0,0,0,.4);
      max-width:min(420px, calc(100vw - 32px));
      display:none;
      gap:8px;
      align-items:flex-start;
    }
    .toast.show{display:flex}
    .toast .tag{
      min-width:8px;min-height:8px;border-radius:999px;background:var(--brand);margin-top:6px
    }
    .toast .msg{font-size:13px;line-height:1.45}
    .smalllink a{color:var(--brand2);text-decoration:none}
    .smalllink a:hover{text-decoration:underline}
    .kbd{
      font-family:var(--mono);
      border:1px solid var(--border);
      background:rgba(255,255,255,.04);
      padding:2px 6px;border-radius:8px;
      font-size:12px;color:var(--muted)
    }
    .badge{
      display:inline-flex;align-items:center;gap:8px;
      padding:8px 10px;border-radius:12px;
      border:1px solid var(--border);
      background:rgba(255,255,255,.03);
      color:var(--muted);font-size:12px
    }
    .spinner{
      width:14px;height:14px;border-radius:999px;
      border:2px solid rgba(255,255,255,.25);
      border-top-color:rgba(255,255,255,.85);
      animation:spin .8s linear infinite;
      display:none;
    }
    .busy .spinner{display:inline-block}
    @keyframes spin{to{transform:rotate(360deg)}}
    .tipbox{
      border:1px solid var(--border);
      background:rgba(255,255,255,.03);
      border-radius:14px;
      padding:12px 12px;
      color:var(--muted);
      font-size:12px;
      line-height:1.55;
    }
    .tipbox b{color:var(--text)}
    .codebox{
      width:100%;
      border:1px solid var(--border);
      background:rgba(255,255,255,.02);
      color:var(--text);
      border-radius:12px;
      padding:10px 10px;
      font-family:var(--mono);
      font-size:12px;
      line-height:1.5;
      white-space:pre-wrap;
      word-break:break-word;
      max-height:260px;
      overflow:auto;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="header">
      <div class="title">
        <h1>Markdown → Word（Pandoc）</h1>
        <p>支持 <span class="kbd">$...$</span> / <span class="kbd">$$...$$</span> 公式；可下载 docx 或一键复制到剪贴板后粘贴到 Word。</p>
      </div>
      <div class="pill">
        <span class="spinner"></span>
        <span id="statusText">就绪</span>
      </div>
    </div>

    <div class="grid">
      <!-- 左侧：编辑/转换 -->
      <div class="card">
        <div class="hd">
          <b>转换</b>
          <span class="badge">推荐：下载 docx（公式最稳）｜ 复制粘贴：方便但依赖 Word/浏览器支持</span>
        </div>
        <div class="bd">
          <div class="row">
            <div>
              <label>输出文件名（不含后缀）</label>
              <input id="stem" type="text" value="output" />
            </div>
            <div>
              <label>模板 reference.docx（可选）</label>
              <input id="ref" type="file" accept=".docx" />
            </div>
          </div>

          <div style="margin-top:12px;">
            <label>Markdown 内容</label>
            <textarea id="md"># 示例

行内公式：$E=mc^2$

块级公式：

$$
\mathbf{r}_P = \mathcal{F}(M(t)\,\mathbf{r}_{ECEF})
$$

- 列表项 1
- 列表项 2
</textarea>
          </div>

          <div style="margin-top:12px;" class="btnbar">
            <button class="primary" id="btnDownload">转换并下载 docx</button>
            <button id="btnCopy">转换并复制到剪贴板（粘贴到 Word）</button>
            <button id="btnExample">插入示例</button>
            <button class="danger" id="btnClear">清空</button>
          </div>

          <div class="hr"></div>
          <div class="tipbox">
            <b>复制到 Word 的说明：</b>
            点击 “转换并复制到剪贴板” 后，到 Word 里 <span class="kbd">Ctrl+V</span> 粘贴。
            若你看到是纯文本或公式不理想，建议用 “下载 docx”。
          </div>
        </div>
      </div>

      <!-- 右侧：Prompt / 健康检查 -->
      <div class="card">
        <div class="hd">
          <b>AI Prompt（可复制）</b>
          <div class="btnbar">
            <button id="btnCopyPrompt">复制 Prompt</button>
            <button id="btnHealth">检查 Pandoc</button>
          </div>
        </div>
        <div class="bd">
          <div class="muted">把下面 Prompt 复制给 AI，让它生成 Pandoc 友好的 Markdown。</div>
          <div style="margin-top:10px;" class="codebox" id="promptBox"></div>

          <div class="hr"></div>
          <div class="muted smalllink">
            健康检查接口：<a href="/health" target="_blank">/health</a>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="toast" id="toast">
    <div class="tag"></div>
    <div class="msg" id="toastMsg"></div>
  </div>

  <script>
    const AI_MD_GUIDE = `__AI_MD_GUIDE__`;

    const els = {
      stem: document.getElementById('stem'),
      md: document.getElementById('md'),
      ref: document.getElementById('ref'),
      btnDownload: document.getElementById('btnDownload'),
      btnCopy: document.getElementById('btnCopy'),
      btnExample: document.getElementById('btnExample'),
      btnClear: document.getElementById('btnClear'),
      btnCopyPrompt: document.getElementById('btnCopyPrompt'),
      btnHealth: document.getElementById('btnHealth'),
      promptBox: document.getElementById('promptBox'),
      statusText: document.getElementById('statusText'),
      toast: document.getElementById('toast'),
      toastMsg: document.getElementById('toastMsg'),
    };

    els.promptBox.textContent = AI_MD_GUIDE;

    function setBusy(busy, text){
      document.body.classList.toggle('busy', busy);
      els.statusText.textContent = text || (busy ? '处理中…' : '就绪');
      els.btnDownload.disabled = busy;
      els.btnCopy.disabled = busy;
      els.btnCopyPrompt.disabled = busy;
      els.btnHealth.disabled = busy;
    }

    function toast(msg){
      els.toastMsg.textContent = msg;
      els.toast.classList.add('show');
      clearTimeout(window.__toast_timer);
      window.__toast_timer = setTimeout(()=>els.toast.classList.remove('show'), 3200);
    }

    function getFormData(){
      const fd = new FormData();
      fd.append('stem', (els.stem.value || 'output').trim() || 'output');
      fd.append('md', els.md.value || '');
      if (els.ref.files && els.ref.files[0]) {
        fd.append('reference', els.ref.files[0], els.ref.files[0].name);
      }
      return fd;
    }

    async function downloadDocx(){
      const fd = getFormData();
      setBusy(true, '转换并下载中…');
      try{
        const res = await fetch('/convert', { method:'POST', body: fd });
        if(!res.ok){
          const err = await res.json().catch(()=>({error:'转换失败'}));
          throw new Error(err.error || '转换失败');
        }
        const blob = await res.blob();
        const name = ((els.stem.value || 'output').trim() || 'output') + '.docx';
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = name;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        toast('已生成并开始下载：' + name);
        setBusy(false, '完成 ✅');
      }catch(e){
        console.error(e);
        toast('失败：' + e.message);
        setBusy(false, '失败 ❌');
      }
    }

    async function copyToClipboardForWord(){
  const fd = getFormData();
  setBusy(true, '转换并复制中…');
  try{
    const res = await fetch('/convert_html', { method:'POST', body: fd });
    if(!res.ok){
      const err = await res.json().catch(()=>({error:'转换失败'}));
      throw new Error(err.error || '转换失败');
    }
    const frag = await res.text();

    // 1) 放进隐藏容器
    let box = document.getElementById('__copy_box__');
    if(!box){
      box = document.createElement('div');
      box.id = '__copy_box__';
      box.contentEditable = 'true';
      box.style.position = 'fixed';
      box.style.left = '-99999px';
      box.style.top = '0';
      box.style.width = '800px';
      box.style.padding = '20px';
      box.style.background = 'white';
      box.style.color = 'black';
      document.body.appendChild(box);
    }
    box.innerHTML = frag;

    // 2) 选中它
    const range = document.createRange();
    range.selectNodeContents(box);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);

    // 3) 触发“原生复制”
    const ok = document.execCommand('copy');
    sel.removeAllRanges();

    if(!ok){
      // 退化：至少复制纯文本
      await navigator.clipboard.writeText(box.innerText || frag);
      toast('已复制（退化为纯文本）。建议用“下载 docx”保证公式。');
    }else{
      toast('已复制到剪贴板。到 Word 里 Ctrl+V 粘贴。');
    }
    setBusy(false, '完成 ✅');
  }catch(e){
    console.error(e);
    toast('失败：' + e.message);
    setBusy(false, '失败 ❌');
  }
}


    async function copyPrompt(){
      try{
        await navigator.clipboard.writeText(AI_MD_GUIDE);
        toast('Prompt 已复制到剪贴板');
      }catch(e){
        // 退化：选中文本提示用户复制
        toast('自动复制失败：请手动全选右侧 Prompt 复制');
      }
    }

    async function healthCheck(){
      setBusy(true, '检查中…');
      try{
        const res = await fetch('/health');
        const j = await res.json();
        if(j.ok && j.pandoc_rc === 0){
          toast('Pandoc 正常 ✅');
          setBusy(false, '就绪');
        }else{
          toast('Pandoc 异常：' + JSON.stringify(j));
          setBusy(false, '异常 ❌');
        }
      }catch(e){
        toast('检查失败：' + e.message);
        setBusy(false, '失败 ❌');
      }
    }

    function insertExample(){
      els.md.value =
`# 示例

行内公式：$E=mc^2$

块级公式：

$$
\\mathbf{r}_P = \\mathcal{F}(M(t)\\,\\mathbf{r}_{ECEF})
$$

## 小节标题

- 列表项 1
- 列表项 2

| A | B |
|---|---|
| 1 | 2 |
`;
      toast('已插入示例');
    }

    function clearAll(){
      els.stem.value = 'output';
      els.ref.value = '';
      els.md.value = '';
      toast('已清空');
    }

    els.btnDownload.addEventListener('click', (e)=>{ e.preventDefault(); downloadDocx(); });
    els.btnCopy.addEventListener('click', (e)=>{ e.preventDefault(); copyToClipboardForWord(); });
    els.btnCopyPrompt.addEventListener('click', (e)=>{ e.preventDefault(); copyPrompt(); });
    els.btnHealth.addEventListener('click', (e)=>{ e.preventDefault(); healthCheck(); });
    els.btnExample.addEventListener('click', (e)=>{ e.preventDefault(); insertExample(); });
    els.btnClear.addEventListener('click', (e)=>{ e.preventDefault(); clearAll(); });
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index():
    # 把 prompt 安全塞进页面（简单转义反引号）
    safe = AI_MD_GUIDE.replace("`", "\\`")
    return HTML.replace("__AI_MD_GUIDE__", safe)


@app.get("/prompt", response_class=PlainTextResponse)
def prompt_text():
    # 也提供一个接口，方便你别的地方拿 Prompt
    return AI_MD_GUIDE


def run_pandoc_docx(md_path: Path, out_docx: Path, ref_docx: Optional[Path]) -> None:
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


def run_pandoc_html_fragment(md_path: Path) -> str:
    from_format = "markdown+tex_math_dollars+tex_math_single_backslash+raw_tex"
    cmd = [
        "pandoc",
        str(md_path),
        "-f", from_format,
        "-t", "html",
        "--mathml",
        "--wrap=none",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(
            "Pandoc HTML failed.\n"
            f"CMD: {' '.join(cmd)}\n"
            f"STDOUT:\n{r.stdout}\n"
            f"STDERR:\n{r.stderr}\n"
        )
    html = (r.stdout or "").strip()
    if not html:
        raise RuntimeError("Pandoc HTML returned empty output.")
    return html



@app.get("/health")
def health():
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
    stem = (stem or "output").strip() or "output"

    # 限制：防止超大内容把免费实例拖死（可按需调整）
    if len(md.encode("utf-8")) > 2_000_000:
        return JSONResponse(status_code=413, content={"error": "Markdown 内容过大（>2MB），请缩小后再试。"})
    if reference is not None and reference.filename:
        ref_bytes = await reference.read()
        if len(ref_bytes) > 5_000_000:
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

            run_pandoc_docx(md_path, out_docx, ref_path)
            data = out_docx.read_bytes()

        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{stem}.docx"'},
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/convert_html")
async def convert_html(
    md: str = Form(...),
    stem: str = Form("output"),
    reference: UploadFile | None = File(None),
):
    if len(md.encode("utf-8")) > 2_000_000:
        return JSONResponse(status_code=413, content={"error": "Markdown 内容过大（>2MB），请缩小后再试。"})
    try:
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            md_path = td / "input.md"
            md_path.write_text(md, encoding="utf-8")
            frag = run_pandoc_html_fragment(md_path)

        # 直接返回“片段”，前端会塞到 DOM 再复制
        return Response(content=frag, media_type="text/plain; charset=utf-8")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

