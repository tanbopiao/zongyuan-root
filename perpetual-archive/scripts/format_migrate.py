#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
格式迁移工具
将专有格式文档转换为长期保存格式（PDF/A + Markdown + 纯文本）
用法：python3 format_migrate.py <资产目录> [--output <输出目录>]
依赖：pandoc（用于.docx→.md转换），libreoffice（用于.docx→.pdf转换）
"""
import os, sys, subprocess, argparse, shutil
from pathlib import Path
from datetime import datetime

# 支持迁移的格式
MIGRATABLE_EXTENSIONS = {'.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls', '.odt', '.rtf'}

def check_dependencies():
    """检查依赖工具"""
    deps = {}
    deps['pandoc'] = shutil.which('pandoc') is not None
    deps['libreoffice'] = shutil.which('libreoffice') is not None or shutil.which('soffice') is not None
    return deps

def convert_to_pdf(src_file, output_dir):
    """使用libreoffice转换为PDF"""
    soffice = shutil.which('libreoffice') or shutil.which('soffice')
    if not soffice:
        return None
    try:
        result = subprocess.run(
            [soffice, '--headless', '--convert-to', 'pdf', '--outdir', output_dir, src_file],
            capture_output=True, text=True, timeout=120
        )
        pdf_name = Path(src_file).stem + '.pdf'
        pdf_path = os.path.join(output_dir, pdf_name)
        if os.path.exists(pdf_path):
            return pdf_path
    except Exception as e:
        print(f"  PDF转换失败: {e}")
    return None

def convert_to_markdown(src_file, output_dir):
    """使用pandoc转换为Markdown"""
    if not shutil.which('pandoc'):
        return None
    try:
        md_name = Path(src_file).stem + '.md'
        md_path = os.path.join(output_dir, md_name)
        result = subprocess.run(
            ['pandoc', src_file, '-o', md_path, '--wrap=none'],
            capture_output=True, text=True, timeout=60
        )
        if os.path.exists(md_path):
            return md_path
    except Exception as e:
        print(f"  Markdown转换失败: {e}")
    return None

def convert_to_text(src_file, output_dir):
    """转换为纯文本（使用pandoc或直接提取）"""
    if shutil.which('pandoc'):
        try:
            txt_name = Path(src_file).stem + '.txt'
            txt_path = os.path.join(output_dir, txt_name)
            result = subprocess.run(
                ['pandoc', src_file, '-o', txt_path, '-t', 'plain'],
                capture_output=True, text=True, timeout=60
            )
            if os.path.exists(txt_path):
                return txt_path
        except Exception:
            pass
    return None

def migrate_directory(src_dir, output_dir):
    """迁移整个目录"""
    src_dir = os.path.abspath(src_dir)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    migrated = []
    skipped = []
    failed = []

    for root, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        rel_root = os.path.relpath(root, src_dir)
        out_root = os.path.join(output_dir, rel_root) if rel_root != '.' else output_dir
        os.makedirs(out_root, exist_ok=True)

        for fname in files:
            ext = Path(fname).suffix.lower()
            src_file = os.path.join(root, fname)

            if ext not in MIGRATABLE_EXTENSIONS:
                # 非可迁移格式，直接复制
                dst_file = os.path.join(out_root, fname)
                if not os.path.exists(dst_file):
                    shutil.copy2(src_file, dst_file)
                skipped.append(fname)
                continue

            print(f"  迁移: {fname}")
            results = {"source": fname, "pdf": None, "markdown": None, "text": None}

            # 复制原文件
            dst_file = os.path.join(out_root, fname)
            if not os.path.exists(dst_file):
                shutil.copy2(src_file, dst_file)

            # 转换为PDF
            pdf_path = convert_to_pdf(src_file, out_root)
            if pdf_path:
                results['pdf'] = os.path.basename(pdf_path)

            # 转换为Markdown
            md_path = convert_to_markdown(src_file, out_root)
            if md_path:
                results['markdown'] = os.path.basename(md_path)

            # 转换为纯文本
            txt_path = convert_to_text(src_file, out_root)
            if txt_path:
                results['text'] = os.path.basename(txt_path)

            if results['pdf'] or results['markdown'] or results['text']:
                migrated.append(results)
            else:
                failed.append(fname)

    return migrated, skipped, failed

def main():
    parser = argparse.ArgumentParser(description='格式迁移工具（专有格式→长期保存格式）')
    parser.add_argument('directory', help='待迁移的资产目录')
    parser.add_argument('--output', '-o', help='输出目录（默认在源目录下创建_migrated）')
    args = parser.parse_args()

    src_dir = os.path.abspath(args.directory)
    output_dir = args.output or os.path.join(src_dir, '_migrated')

    print(f"{'='*70}")
    print(f"  格式迁移工具")
    print(f"  DID: DID-BR-000002 | 确权: Ω₀⊂⊙∞⊂Ω")
    print(f"{'='*70}")
    print(f"源目录: {src_dir}")
    print(f"输出目录: {output_dir}")

    # 检查依赖
    deps = check_dependencies()
    print(f"\n依赖检查:")
    print(f"  pandoc: {'✅' if deps['pandoc'] else '❌ 未安装（.md/.txt转换不可用）'}")
    print(f"  libreoffice: {'✅' if deps['libreoffice'] else '❌ 未安装（.pdf转换不可用）'}")

    if not deps['pandoc'] and not deps['libreoffice']:
        print("\n⚠️  未安装任何转换工具，无法进行格式迁移")
        print("安装方法:")
        print("  Ubuntu/Debian: sudo apt install pandoc libreoffice")
        print("  macOS: brew install pandoc libreoffice")
        sys.exit(1)

    print(f"\n开始迁移...\n")
    migrated, skipped, failed = migrate_directory(src_dir, output_dir)

    # 生成迁移报告
    report = {
        "did": "DID-BR-000002",
        "trace_mark": "Ω₀⊂⊙∞⊂Ω",
        "migration_time": datetime.now().isoformat(),
        "source": src_dir,
        "output": output_dir,
        "migrated_count": len(migrated),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "migrated_files": migrated,
        "failed_files": failed
    }

    report_path = os.path.join(output_dir, "_migration_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*70}")
    print(f"✅ 迁移完成")
    print(f"  已迁移: {len(migrated)} 个文件")
    print(f"  直接复制(非可迁移格式): {len(skipped)} 个文件")
    print(f"  转换失败: {len(failed)} 个文件")
    print(f"  输出目录: {output_dir}")
    print(f"  迁移报告: {report_path}")
    print(f"{'='*70}")
    print(f"\n长期保存格式说明:")
    print(f"  .pdf  - PDF格式，通用可读，建议进一步转为PDF/A归档标准")
    print(f"  .md   - Markdown纯文本，人类可读，版本控制友好")
    print(f"  .txt  - 纯文本，最长期可读，无格式依赖")

if __name__ == "__main__":
    main()
