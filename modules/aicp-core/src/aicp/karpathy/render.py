from __future__ import annotations

import html
import os
import pathlib
import shutil
import subprocess
import tempfile
import webbrowser
from dataclasses import dataclass
from typing import Any

import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_for_filename

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".ico",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".mp3", ".mp4", ".mov", ".avi", ".mkv", ".wav", ".ogg", ".flac",
    ".ttf", ".otf", ".eot", ".woff", ".woff2",
    ".so", ".dll", ".dylib", ".class", ".jar", ".exe", ".bin",
}

MARKDOWN_EXTENSIONS = {".md", ".markdown", ".mdown", ".mkd", ".mkdn"}


@dataclass
class RenderDecision:
    include: bool
    reason: str


@dataclass
class FileInfo:
    path: pathlib.Path
    rel: str
    size: int
    decision: RenderDecision


def _run(cmd: list[str], cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, check=True, text=True, capture_output=True)


def _git_clone(url: str, dst: str) -> None:
    _run(["git", "clone", "--depth", "1", url, dst])


def _git_head_commit(repo_dir: str) -> str:
    try:
        cp = _run(["git", "rev-parse", "HEAD"], cwd=repo_dir)
        return cp.stdout.strip()
    except Exception:
        return "(unknown)"


def _bytes_human(n: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    f = float(n)
    i = 0
    while f >= 1024.0 and i < len(units) - 1:
        f /= 1024.0
        i += 1
    return f"{int(f)} {units[i]}" if i == 0 else f"{f:.1f} {units[i]}"


def _looks_binary(path: pathlib.Path) -> bool:
    ext = path.suffix.lower()
    if ext in BINARY_EXTENSIONS:
        return True
    try:
        with path.open("rb") as f:
            chunk = f.read(8192)
        if b"\x00" in chunk:
            return True
        chunk.decode("utf-8")
        return False
    except Exception:
        return True


def _decide_file(path: pathlib.Path, repo_root: pathlib.Path, max_bytes: int) -> FileInfo:
    rel = str(path.relative_to(repo_root)).replace(os.sep, "/")
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        size = 0

    if "/.git/" in f"/{rel}/" or rel.startswith(".git/"):
        return FileInfo(path, rel, size, RenderDecision(False, "ignored"))
    if size > max_bytes:
        return FileInfo(path, rel, size, RenderDecision(False, "too_large"))
    if _looks_binary(path):
        return FileInfo(path, rel, size, RenderDecision(False, "binary"))
    return FileInfo(path, rel, size, RenderDecision(True, "ok"))


def _collect_files(repo_root: pathlib.Path, max_bytes: int) -> list[FileInfo]:
    infos: list[FileInfo] = []
    for p in sorted(repo_root.rglob("*")):
        if p.is_symlink() or not p.is_file():
            continue
        infos.append(_decide_file(p, repo_root, max_bytes))
    return infos


def _read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _render_markdown_text(md_text: str) -> str:
    return markdown.markdown(md_text, extensions=["fenced_code", "tables", "toc"])


def _highlight_code(text: str, filename: str, formatter: HtmlFormatter) -> str:
    try:
        lexer = get_lexer_for_filename(filename, stripall=False)
    except Exception:
        lexer = TextLexer(stripall=False)
    return highlight(text, lexer, formatter)


def _slugify(path_str: str) -> str:
    out = []
    for ch in path_str:
        if ch.isalnum() or ch in {"-", "_"}:
            out.append(ch)
        else:
            out.append("-")
    return "".join(out)


def _generate_cxml_text(infos: list[FileInfo], repo_dir: pathlib.Path) -> str:
    lines = ["<documents>"]
    rendered = [i for i in infos if i.decision.include]
    for index, i in enumerate(rendered, 1):
        lines.append(f'<document index="{index}">')
        lines.append(f"<source>{i.rel}</source>")
        lines.append("<document_content>")
        try:
            text = _read_text(i.path)
            lines.append(text)
        except Exception as e:
            lines.append(f"Failed to read: {str(e)}")
        lines.append("</document_content>")
        lines.append("</document>")
    lines.append("</documents>")
    return "\n".join(lines)


def _build_html(
    repo_url: str,
    repo_dir: pathlib.Path,
    head_commit: str,
    infos: list[FileInfo],
) -> str:
    formatter = HtmlFormatter(nowrap=False)
    pygments_css = formatter.get_style_defs(".highlight")

    rendered = [i for i in infos if i.decision.include]
    skipped_binary = [i for i in infos if i.decision.reason == "binary"]
    skipped_large = [i for i in infos if i.decision.reason == "too_large"]
    skipped_ignored = [i for i in infos if i.decision.reason == "ignored"]

    toc_items = []
    for i in rendered:
        anchor = _slugify(i.rel)
        toc_items.append(
            f'<li><a href="#file-{anchor}">{html.escape(i.rel)}</a> '
            f'<span class="muted">({_bytes_human(i.size)})</span></li>'
        )
    toc_html = "".join(toc_items)

    sections = []
    for i in rendered:
        anchor = _slugify(i.rel)
        ext = i.path.suffix.lower()
        try:
            text = _read_text(i.path)
            if ext in MARKDOWN_EXTENSIONS:
                body_html = _render_markdown_text(text)
            else:
                code_html = _highlight_code(text, i.rel, formatter)
                body_html = f'<div class="highlight">{code_html}</div>'
        except Exception as e:
            body_html = f'<pre class="error">Failed to render: {html.escape(str(e))}</pre>'
        sections.append(f"""
<section class="file-section" id="file-{anchor}">
  <h2>{html.escape(i.rel)} <span class="muted">({_bytes_human(i.size)})</span></h2>
  <div class="file-body">{body_html}</div>
  <div class="back-top"><a href="#top">↑ Back to top</a></div>
</section>
""")

    cxml_text = _generate_cxml_text(infos, repo_dir)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Flattened repo – {html.escape(repo_url)}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 0; line-height: 1.45; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 0 1rem; }}
  .meta small {{ color: #666; }}
  .muted {{ color: #777; font-weight: normal; font-size: 0.9em; }}
  .page {{ display: grid; grid-template-columns: 320px minmax(0,1fr); gap: 0; }}
  #sidebar {{ position: sticky; top: 0; align-self: start; height: 100vh; overflow: auto; border-right: 1px solid #eee; background: #fafbfc; }}
  #sidebar .sidebar-inner {{ padding: 0.75rem; }}
  #sidebar h2 {{ margin: 0 0 0.5rem 0; font-size: 1rem; }}
  .toc {{ list-style: none; padding-left: 0; margin: 0; overflow-x: auto; }}
  .toc li {{ padding: 0.15rem 0; white-space: nowrap; }}
  .toc a {{ text-decoration: none; color: #0366d6; display: inline-block; }}
  main.container {{ padding-top: 1rem; }}
  pre {{ background: #f6f8fa; padding: 0.75rem; overflow: auto; border-radius: 6px; }}
  code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }}
  .highlight {{ overflow-x: auto; }}
  .file-section {{ padding: 1rem; border-top: 1px solid #eee; }}
  .file-section h2 {{ margin: 0 0 0.5rem 0; font-size: 1.1rem; }}
  .back-top {{ font-size: 0.9rem; }}
  .error {{ color: #b00020; background: #fff3f3; }}
  .view-toggle {{ margin: 1rem 0; display: flex; gap: 0.5rem; align-items: center; }}
  .toggle-btn {{ padding: 0.5rem 1rem; border: 1px solid #d1d9e0; background: white; cursor: pointer; border-radius: 6px; font-size: 0.9rem; }}
  .toggle-btn.active {{ background: #0366d6; color: white; border-color: #0366d6; }}
  #llm-view {{ display: none; }}
  #llm-text {{ white-space: pre-wrap; font-family: monospace; background: #f6f8fa; padding: 1rem; overflow: auto; }}
  .tree {{ font-family: monospace; white-space: pre; font-size: 0.85rem; }}
</style>
</head>
<body>
<div class="page">
  <div id="sidebar"><div class="sidebar-inner">
    <h2>{html.escape(repo_url.split("/")[-1])}</h2>
    <p class="meta"><small>{head_commit[:7]}</small></p>
    <div class="counts">{len(rendered)} files shown, {len(skipped_binary)} binary, {len(skipped_large)} large, {len(skipped_ignored)} ignored</div>
    <ul class="toc">{toc_html}</ul>
  </div></div>
  <main class="container">
    <div class="view-toggle">
      <button class="toggle-btn active" onclick="showView('human')">👤 Human View</button>
      <button class="toggle-btn" onclick="showView('llm')">🤖 LLM View</button>
    </div>
    <div id="human-view">
      <pre class="tree">{_try_tree_command(repo_dir)}</pre>
      {"".join(sections)}
    </div>
    <div id="llm-view"><pre id="llm-text">{html.escape(cxml_text)}</pre></div>
  </main>
</div>
<script>
function showView(view) {{
  document.getElementById('human-view').style.display = view === 'human' ? 'block' : 'none';
  document.getElementById('llm-view').style.display = view === 'llm' ? 'block' : 'none';
  document.querySelectorAll('.toggle-btn').forEach((btn, i) => {{
    btn.classList.toggle('active', (i === 0 && view === 'human') || (i === 1 && view === 'llm'));
  }});
}}
</script>
</body>
</html>"""


def _try_tree_command(root: pathlib.Path) -> str:
    try:
        cp = _run(["tree", "-a", "."], cwd=str(root))
        return cp.stdout
    except Exception:
        return _generate_tree_fallback(root)


def _generate_tree_fallback(root: pathlib.Path) -> str:
    lines = []
    prefix_stack: list[str] = []

    def walk(dir_path: pathlib.Path, prefix: str = "") -> None:
        entries = [e for e in dir_path.iterdir() if e.name != ".git"]
        entries.sort(key=lambda e: (not e.is_dir(), e.name.lower()))
        for i, e in enumerate(entries):
            last = i == len(entries) - 1
            branch = "└── " if last else "├── "
            lines.append(prefix + branch + e.name)
            if e.is_dir():
                extension = "    " if last else "│   "
                walk(e, prefix + extension)

    lines.append(root.name)
    walk(root)
    return "\n".join(lines)


async def render_repository(
    repo_url: str,
    max_bytes: int = 50_000,
    open_browser: bool = False,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        repo_path = os.path.join(tmpdir, repo_name)

        _git_clone(repo_url, repo_path)

        head_commit = _git_head_commit(repo_path)

        infos = _collect_files(pathlib.Path(repo_path), max_bytes)

        html_content = _build_html(repo_url, pathlib.Path(repo_path), head_commit, infos)

        output_path = os.path.join(tmpdir, f"{repo_name}.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        final_path = os.path.expanduser(f"~/Downloads/{repo_name}.html")
        shutil.copy(output_path, final_path)

        if open_browser:
            webbrowser.open(f"file://{final_path}")

        rendered = [i for i in infos if i.decision.include]
        skipped = [i for i in infos if not i.decision.include]

        return {
            "repo_url": repo_url,
            "max_bytes": max_bytes,
            "output_path": final_path,
            "files_included": len(rendered),
            "files_skipped": len(skipped),
            "commit": head_commit,
        }
