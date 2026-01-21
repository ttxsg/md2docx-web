# Markdown → Word（Pandoc）Web Converter

一个基于 **FastAPI + Pandoc** 的在线工具：将 **Pandoc 友好的 Markdown** 一键转换为 **Word（.docx）**，并 **保留 LaTeX 公式**（转换为 Word 原生公式/OMML）。适合写论文、报告、技术文档时把 Markdown 快速输出为排版稳定的 Word 文档。

> 线上部署推荐：Render（免费层可用，带冷启动）  
> 核心特点：**下载的 docx 公式不会乱码**（相比“复制粘贴到 Word”更可靠）

---

## Features

- ✅ **Markdown → .docx** 一键转换  
- ✅ 支持 **LaTeX 数学公式**（`$...$` / `$$...$$`）并输出为 Word 原生公式（OMML）
- ✅ 支持上传 **reference.docx 模板**（可选）：控制字体、标题、段落、页边距等样式
- ✅ 提供 `/health`：检查 Pandoc 是否可用
- ✅ 内置示例内容，便于测试公式与列表效果
- ✅ 简单体积限制（防止超大文本拖垮免费实例）

---

## Online Demo (Optional)

如果你已部署到 Render，可把链接填在这里：

- 🌐 Demo: `(https://md2docx-web.onrender.com/)`

---

## Project Structure




## Project Structure

```

.
├── app.py               # FastAPI 服务：网页 + /convert 接口
├── requirements.txt     # Python 依赖
└── Dockerfile           # 安装 pandoc 并启动 uvicorn（Render 推荐）

````

---

## Requirements

- Python 3.11+
- Pandoc（必须）
- （可选）Docker（推荐用于部署）

---

## Quick Start (Local)

### 1) 安装 Pandoc

- macOS: `brew install pandoc`
- Ubuntu/Debian: `sudo apt-get update && sudo apt-get install -y pandoc`
- Windows: 安装 Pandoc，并确保命令行 `pandoc -v` 可用

### 2) 安装依赖并运行

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
````

打开浏览器访问：

* `http://127.0.0.1:8000`

健康检查：

* `http://127.0.0.1:8000/health`

---

## Docker Run (Recommended)

### Build

```bash
docker build -t md2docx-web .
```

### Run

```bash
docker run --rm -p 8000:8000 md2docx-web
```

打开：

* `http://127.0.0.1:8000`

---

## Deploy to Render (Recommended)

1. 将本项目推到 GitHub
2. Render → **New Web Service**
3. 选择你的 GitHub 仓库
4. Runtime 选择 **Docker**
5. Deploy

> Render 免费实例可能会在一段时间无访问后休眠，首次唤醒会有冷启动延迟。

---

## How to Write Markdown (Pandoc-friendly)

* 标题用 `# / ## / ###`
* 段落之间空一行
* 公式使用：

  * 行内：`$E=mc^2$`
  * 块级：

    ```text
    $$
    \mathbf{r}_P = \mathcal{F}(M(t)\,\mathbf{r}_{ECEF})
    $$
    ```
* 列表用 `-` 或 `1.`
* 尽量避免 HTML 标签（如 `<br>` `<span>`）

---

## API

### `GET /`

返回网页界面。

### `POST /convert`

表单参数：

* `md`：Markdown 内容（必填）
* `stem`：输出文件名（不含后缀，可选）
* `reference`：reference.docx 模板（可选）

返回：

* `.docx` 文件下载

### `GET /health`

返回 Pandoc 可用性与版本信息。

---

## Notes

* “下载 docx”是最稳定的方式（公式会被转换为 Word 原生公式）。
* Web 环境下无法像桌面程序那样“自动打开 Word/打开目录”（浏览器安全限制）。

---

## License

你可以选择并添加许可证，例如：

* MIT
* Apache-2.0

---

## Author

* 公众号：知新小窝
* 用途：Markdown 文档快速生成 Word（保留公式）


