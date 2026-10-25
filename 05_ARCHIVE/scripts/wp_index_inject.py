#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZONGYUAN-ROOT 官网白皮书库索引注入器（幂等）
DID-BR-000002 | Ω₀⊂⊙∞⊂Ω

在 huodouai.com/whitepaper/index.html 中新增一张白皮书卡片，
并同步「共 N 份白皮书」计数。

线上模板（2026-10-18 实测，与 huodouai.com 一致）：
    <h1>技术白皮书库</h1>
    <p>共 85 份白皮书</p>
    <div class="grid">
    <div class="card"><h3>标题</h3><a href="slug.html">查看 →</a></div>
    ...（卡片连续拼接，无分隔符）
    </div>
    <div style="text-align:center;padding:20px;...">页脚</div>

安全约束（风险最小铁律）：
  - 幂等：同 slug 链接已存在 → skipped，不改任何字节
  - 定位失败 → 直接非零退出，绝不"猜改"
  - 写入前自动备份；写入后自校验，校验失败自动回滚
  - 仅操作 index.html，不触碰其他卡片
"""
import argparse
import base64
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

GRID_OPEN = '<div class="grid">'
FOOTER_MARK = '<div style="text-align:center'
COUNT_RE = re.compile(r'共\s*(\d+)\s*份白皮书')
CARD_OPEN = '<div class="card">'


def build_card(slug: str, title: str) -> str:
    # 最小 HTML 转义，防止标题中的 &<>" 破坏文档结构
    esc = (title.replace('&', '&amp;').replace('<', '&lt;')
                .replace('>', '&gt;').replace('"', '&quot;'))
    return f'<div class="card"><h3>{esc}</h3><a href="{slug}.html">查看 →</a></div>'


def emit(obj: dict, as_json: bool, human: str) -> None:
    print(json.dumps(obj, ensure_ascii=False) if as_json else human)


def main() -> int:
    ap = argparse.ArgumentParser(description='白皮书库索引幂等注入器')
    ap.add_argument('--index', required=True, help='index.html 路径')
    ap.add_argument('--slug', required=True, help='白皮书文件名（不含 .html）')
    ap.add_argument('--title', help='卡片标题（原生）')
    ap.add_argument('--title-b64', help='卡片标题（base64(utf-8)，规避远端引号转义）')
    ap.add_argument('--position', choices=['top', 'bottom'], default='top')
    ap.add_argument('--check-only', action='store_true', help='只报告状态，不修改')
    ap.add_argument('--no-backup', action='store_true')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()

    title = None
    if a.title_b64:
        title = base64.b64decode(a.title_b64).decode('utf-8')
    elif a.title:
        title = a.title
    elif not a.check_only:
        print('需要 --title 或 --title-b64', file=sys.stderr)
        return 2

    p = Path(a.index)
    if not p.is_file():
        print(f'索引不存在: {p}', file=sys.stderr)
        return 2
    content = p.read_text(encoding='utf-8')

    link = f'href="{a.slug}.html"'
    already = link in content

    m = COUNT_RE.search(content)
    if not m:
        print('未找到「共 N 份白皮书」计数标记，模板不匹配，中止（不猜改）', file=sys.stderr)
        return 3
    count_before = int(m.group(1))
    cards_before = content.count(CARD_OPEN)

    if a.check_only:
        emit({'status': 'checked', 'slug': a.slug, 'present': already,
              'count_before': count_before, 'cards_before': cards_before},
             a.json, f'{a.slug}: present={already} count={count_before} cards={cards_before}')
        return 0

    if already:
        emit({'status': 'skipped', 'reason': 'already_present', 'slug': a.slug,
              'count_before': count_before, 'cards_before': cards_before},
             a.json, f'已存在，跳过: {a.slug}')
        return 0

    grid_open = content.find(GRID_OPEN)
    if grid_open < 0:
        print('未找到 <div class="grid"> 容器，中止（不猜改）', file=sys.stderr)
        return 3
    grid_open_end = grid_open + len(GRID_OPEN)

    footer = content.find(FOOTER_MARK, grid_open_end)
    if footer < 0:
        print('未找到页脚锚点，无法定位 grid 闭合标签，中止（不猜改）', file=sys.stderr)
        return 3
    grid_close = content.rfind('</div>', grid_open_end, footer)
    if grid_close < 0:
        print('未定位到 grid 闭合标签，中止（不猜改）', file=sys.stderr)
        return 3

    card = build_card(a.slug, title)
    insert_at = grid_open_end if a.position == 'top' else grid_close
    new_content = content[:insert_at] + card + content[insert_at:]
    new_content, subs = COUNT_RE.subn(
        lambda mm: f'共 {int(mm.group(1)) + 1} 份白皮书', new_content, count=1)
    if subs != 1:
        print('计数替换次数异常，中止', file=sys.stderr)
        return 3

    backup = None
    if not a.no_backup:
        ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        backup = f'{a.index}.bak.{ts}'
        shutil.copy2(a.index, backup)

    p.write_text(new_content, encoding='utf-8')

    # 写入后自校验（失败即回滚）
    verify = p.read_text(encoding='utf-8')
    cards_after = verify.count(CARD_OPEN)
    m2 = COUNT_RE.search(verify)
    count_after = int(m2.group(1)) if m2 else -1
    ok = (link in verify) and (cards_after == cards_before + 1) and (count_after == count_before + 1)
    if not ok:
        if backup:
            shutil.copy2(backup, a.index)
        print(f'自校验失败，已回滚: link={link in verify} cards={cards_before}->{cards_after} '
              f'count={count_before}->{count_after}', file=sys.stderr)
        return 4

    emit({'status': 'injected', 'slug': a.slug, 'title': title, 'position': a.position,
          'count_before': count_before, 'count_after': count_after,
          'cards_before': cards_before, 'cards_after': cards_after,
          'backup': backup, 'index': a.index},
         a.json,
         f'已注入: {a.slug} | 计数 {count_before}->{count_after} | 卡片 {cards_before}->{cards_after}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
