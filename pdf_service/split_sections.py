import os
import re
import subprocess
import sys
import shutil
import argparse

# ==========================================
# [設定區] 自動偵測路徑
# ==========================================
PANDOC_PATH = shutil.which("pandoc") or "pandoc"
LATEXMK_PATH = shutil.which("latexmk") or "latexmk"

# ==========================================

SOURCE_MD = "paper.md"
OUTPUT_DIR = "sections"
METADATA_FILE = os.path.join(OUTPUT_DIR, "metadata.tex")
BODY_FILE = os.path.join(OUTPUT_DIR, "body.tex")
PANDOC_ARGS = ["-f", "markdown", "-t", "latex", "--biblatex"]

FORMAT_MAPPING = {"cjp": "main_cjp.tex", "apa": "main_apa.tex"}


def ensure_placeholder_png(path: str):
    """Create a tiny valid PNG placeholder if the target path does not exist."""
    if os.path.exists(path):
        return
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0b"
        b"IDAT\x08\xd7c````\x00\x00\x00\x05\x00\x01\x0d\n\x2d\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png_bytes)


def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def transform_content(content):
    """
    對 Markdown 內文進行預處理
    """
    
    # --- 1. 圖片處理 (保持不變) ---
    fig_pattern = re.compile(
        r"!\[(.*?)\]\((.*?)\)\{#(.*?)\}\s*\n\s*\[Fig_Note\]\s*(.*?)(?=\n|$)",
        re.MULTILINE,
    )

    def fig_replacer(match):
        caption = match.group(1)
        raw_path = match.group(2)
        label = match.group(3)
        note = match.group(4)
        clean_path = os.path.splitext(raw_path)[0]

        return (
            f"\n\\begin{{figure}}[htbp]\n"
            f"    \\centering\n"
            f"    \\caption{{{caption}}}\\label{{{label}}}\n"
            f"    \\includegraphics[width=0.8\\textwidth]{{{clean_path}}}\n"
            f"    \\par\\raggedright\\footnotesize\n"
            f"    {note}\n"
            f"\\end{{figure}}\n"
        )

    content = fig_pattern.sub(fig_replacer, content)

    # --- 2. [新增] 表格註解處理 ---
    # 偵測 [Tab_Note] 開頭，直到遇到「空白行 (\n\n)」或「檔案結尾」
    # 將其包裹在我們剛定義的 tablenote 環境中
    tab_pattern = re.compile(
        r"\[Tab_Note\]\s*(.+?)(?=\n\s*\n|\Z)", 
        re.DOTALL # 允許 . 匹配換行，因為註解可能有多行
    )

    def tab_replacer(match):
        note_content = match.group(1)
        # 使用 Pandoc raw latex 語法包裹
        return f"\n`\\begin{{tablenote}}`{{=latex}}\n{note_content}\n`\\end{{tablenote}}`{{=latex}}"

    content = tab_pattern.sub(tab_replacer, content)

    # --- 3. 參考文獻處理 (保持不變) ---
    if "[Ref_List]" in content:
        print("💡 偵測到 [Ref_List] 標記，已注入參考文獻列印指令。")
        content = content.replace("[Ref_List]", "\n`\\printbibliography[heading=none]`{=latex}\n")
    
    return content


def ensure_figures_exist(full_content: str):
    """Create placeholder images for any Figure/* references to avoid LaTeX aborts when files are missing."""
    figure_refs = re.findall(r"Figure/([^\s}\)]+)", full_content)
    for ref in figure_refs:
        target = os.path.join("Figure", ref)
        ensure_placeholder_png(target)


def parse_yaml_to_latex(content):
    latex_lines = ["% Auto-generated metadata"]
    yaml_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not yaml_match:
        return "", None
    yaml_block = yaml_match.group(1)

    format_match = re.search(
        r'^output_format:\s*["\']?(.*?)["\']?\s*$', yaml_block, re.MULTILINE
    )
    target_format = format_match.group(1).strip().lower() if format_match else None

    mappings = [
        ("title_zh", "MyTitleZh"),
        ("title_en", "MyTitleEn"),
        ("short_title", "MyShortTitle"),
        ("author_zh", "MyAuthorZh"),
        ("author_en", "MyAuthorEn"),
        ("affiliation_zh", "MyAffiliationZh"),
        ("affiliation_en", "MyAffiliationEn"),
        ("keywords_zh", "MyKeywordsZh"),
        ("keywords_en", "MyKeywordsEn"),
    ]
    for key, cmd in mappings:
        match = re.search(rf'^{key}:\s*["\']?(.*?)["\']?\s*$', yaml_block, re.MULTILINE)
        val = match.group(1).strip() if match else ""
        latex_lines.append(f"\\newcommand\\{cmd}{{{val}}}")

    for lang in ["zh", "en"]:
        key = f"abstract_{lang}"
        cmd = f"MyAbstract{lang.capitalize()}"
        match = re.search(
            rf"^{key}:\s*\|\s*\n(.*?)(?=^\w+:|\Z)", yaml_block, re.DOTALL | re.MULTILINE
        )
        val = match.group(1).strip() if match else ""
        latex_lines.append(f"\\newcommand\\{cmd}{{{val}}}")

    return "\n".join(latex_lines), target_format


def compile_pdf(tex_file):
    print(f"\n🚀 正在編譯 PDF ({tex_file})...")

    if not shutil.which("latexmk"):
         print(f"❌ 錯誤: 找不到 Latexmk 指令。")

    # 防呆機制
    if not os.path.exists("references.bib"):
        print("⚠️ 警告: 找不到 references.bib，建立空檔案以避免編譯器崩潰。")
        with open("references.bib", "w") as f:
            f.write("")
    # Use latexmk + biber explicitly to ensure bibliography is generated for APA
    pdf_job = tex_file.replace(".tex", "")
    cmd = [
        LATEXMK_PATH,
        "-pdf",
        "-xelatex",
        "-synctex=1",
        "-interaction=nonstopmode",
        "-file-line-error",
        "-outdir=.",
        tex_file,
    ]

    def run_latexmk(pass_name: str, allow_fail: bool = False):
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"⚠️ latexmk {pass_name} 退出碼 {result.returncode}")
            print(result.stdout)
            print(result.stderr)
            if not allow_fail:
                raise subprocess.CalledProcessError(result.returncode, cmd)
        return result

    # First pass to produce .bcf even if citations are missing
    run_latexmk("pass1", allow_fail=True)

    bcf_path = f"{pdf_job}.bcf"
    if os.path.exists(bcf_path):
        biber = subprocess.run(["biber", pdf_job], capture_output=True, text=True)
        if biber.returncode != 0:
            print("❌ biber 失敗")
            print(biber.stdout)
            print(biber.stderr)
            raise subprocess.CalledProcessError(biber.returncode, biber.args)
        else:
            print("✅ biber 完成")

    # Two more passes to resolve references/citations
    run_latexmk("pass2", allow_fail=True)
    final_run = run_latexmk("final", allow_fail=True)

    pdf_path = tex_file.replace(".tex", ".pdf")
    if final_run.returncode != 0 and not os.path.exists(pdf_path):
        raise subprocess.CalledProcessError(final_run.returncode, cmd)

    print(f"✅ 成功生成: {pdf_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--web-mode", action="store_true", help="Web mode: skip YAML parsing")
    parser.add_argument("--format", default="cjp", help="Target format (cjp/apa)")
    args = parser.parse_args()

    print(f"--- 讀取 {SOURCE_MD} ---")
    if not os.path.exists(SOURCE_MD):
        print(f"❌ 錯誤: 找不到 {SOURCE_MD}")
        sys.exit(1)

    with open(SOURCE_MD, "r", encoding="utf-8") as f:
        full_content = f.read()

    ensure_dir(OUTPUT_DIR)

    if args.web_mode:
        print("🌐 網頁模式：使用外部 metadata.tex，跳過 YAML 解析。")
        target_format = args.format
    else:
        latex_meta, yaml_format = parse_yaml_to_latex(full_content)
        target_format = yaml_format if yaml_format else "cjp"
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            f.write(latex_meta)

    # 使用新的處理函式
    processed_content = transform_content(full_content)

    print("轉換 Markdown 內文...")
    try:
        result = subprocess.run(
            [PANDOC_PATH] + PANDOC_ARGS,
            input=processed_content,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        latex_body = result.stdout
    except Exception as e:
        print(f"Pandoc 錯誤: {e}")
        sys.exit(1)

    pattern = re.compile(r"(\\section\{([^}]+)\}.*?)(?=\\section\{|$)", re.DOTALL)
    matches = pattern.findall(latex_body)

    body_content = []
    if not matches:
        with open(os.path.join(OUTPUT_DIR, "content.tex"), "w", encoding="utf-8") as f:
            f.write(latex_body)
        body_content.append(f"\\input{{sections/content}}")
    else:
        for content, title in matches:
            slug = re.sub(r"[^\w]", "_", title.lower().strip())
            fname = f"{slug}.tex"
            with open(os.path.join(OUTPUT_DIR, fname), "w", encoding="utf-8") as f:
                f.write(content)
            body_content.append(f"\\input{{sections/{slug}}}")

    with open(BODY_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(body_content))

    if target_format and target_format in FORMAT_MAPPING:
        compile_pdf(FORMAT_MAPPING[target_format])
    else:
        print(f"⚠️ 未指定格式或格式錯誤 (目前設定: {target_format})，僅完成轉換。")


if __name__ == "__main__":
    main()