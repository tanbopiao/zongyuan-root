#!/usr/bin/env python3
"""数据湖自动归档钩子 auto_archive_hook.py v1.0
ZONGYUAN-ROOT 数据湖持久层 · DID-BR-000002 · Ω₀⊂⊙∞⊂Ω
功能：新资产（图片/视频/文本内核）自动按业务域增量登记到数据湖
用法：
  python3 auto_archive_hook.py --add /path/to/new/file [--name 资产名] [--dry-run]
  python3 auto_archive_hook.py --refresh   # 全量重扫差异（增量登记新增文件）
分类规则：与 build_data_lake_v2.py 一致的业务域映射
落盘：
  - 媒体：登记 04-media-registry/MEDIA-REGISTRY-V2.json（引用+sha256）
  - 文本：登记 03-index/MANIFEST-LAKE.json 的 text_assets
"""
import json, os, hashlib, sys, time, argparse, collections

LAKE = "/home/user/ZONGYUAN-ROOT/DATA-LAKE-PERSIST"
REG_PATH = os.path.join(LAKE, "04-media-registry", "MEDIA-REGISTRY-V2.json")
MAN_PATH = os.path.join(LAKE, "03-index", "MANIFEST-LAKE.json")
DID = "DID-BR-000002"
TRACE = "Ω₀⊂⊙∞⊂Ω"
MEDIA_EXTS = {'.png','.jpg','.jpeg','.gif','.webp','.bmp','.tiff','.tif','.heic','.svg',
              '.mp4','.mov','.avi','.mkv','.webm','.flv','.wmv','.m4v','.3gp'}
# 文本内核资产类型（文档/代码/配置/数据/协议）
TEXT_EXTS = {'.md','.txt','.json','.py','.sh','.js','.ts','.html','.css','.yml','.yaml',
             '.csv','.xml','.ps1','.bat','.cfg','.ini','.toml','.pdf','.docx','.xlsx',
             '.ipynb','.svg'}

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(1 << 20)
            if not b: break
            h.update(b)
    return h.hexdigest().upper()

def classify(path):
    p = path.replace('\\', '/')
    if '/1128121028098/' in p or '/38437458338949122/' in p or '/38439832899843586/' in p or '/38441793457419522/' in p:
        return "kunlun-drama"
    if '/media_archive/' in p or '/05_ARCHIVE/' in p:
        return "kunlun-media-archive"
    if '/media-gallery/' in p:
        return "zongyuan-gallery"
    if '/01_ASSETS/' in p or '/01_核心资产/' in p:
        return "zongyuan-assets"
    if '/04_PROJECTS/' in p or '/04_媒体资产/' in p:
        return "zongyuan-projects"
    if '/Doubao/ASSETS/' in p:
        return "doubao-assets"
    if '/.zongyuan_root/' in p:
        return "kernel-archive"
    if '/ZONGYUAN-ROOT/' in p:
        return "zongyuan-root"
    return "misc"

def load_reg():
    if os.path.exists(REG_PATH):
        return json.load(open(REG_PATH))
    return []

def save_reg(reg):
    with open(REG_PATH, 'w', encoding='utf-8') as f:
        json.dump(reg, f, ensure_ascii=False, indent=1)

def known_paths(reg):
    known = set()
    for dom in reg:
        for f in dom.get('files', []):
            known.add(f.get('path') or f.get('rel_path','').replace('home/','/home/user/'))
    return known

def add_file(reg, path, dry_run=False):
    ext = os.path.splitext(path)[1].lower()
    size = os.path.getsize(path)
    kind = "image" if ext in ('.png','.jpg','.jpeg','.gif','.webp','.bmp','.tiff','.svg') else "video"
    dom = classify(path)
    entry = {
        "rel_path": path.replace("/home/user/", "home/"),
        "path": path,
        "file": os.path.basename(path),
        "size": size, "size_mb": round(size/1048576, 3),
        "kind": kind, "ext": ext,
        "sha256": None if size > 50*1048576 else sha256_file(path),
        "added_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    }
    # 归入对应域
    for d in reg:
        if d.get('domain') == dom:
            d['files'].append(entry)
            d['file_count'] = len(d['files'])
            d['total_mb'] = round(sum(x['size_mb'] for x in d['files']), 2)
            break
    else:
        reg.append({"domain": dom, "file_count": 1, "total_mb": entry['size_mb'], "files": [entry]})
    return dom, entry

def refresh(reg, roots, dry_run=False):
    """全量重扫新增差异"""
    known = known_paths(reg)
    added = 0
    for root in roots:
        if not os.path.isdir(root): continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in {'.git','node_modules','site-packages','.cache','__pycache__'}]
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in MEDIA_EXTS: continue
                p = os.path.join(dirpath, fn)
                if p in known: continue
                try:
                    dom, e = add_file(reg, p, dry_run)
                    if not dry_run:
                        print(f"  + [{dom}] {os.path.basename(p)} ({e['size_mb']}MB)")
                    added += 1
                except OSError:
                    pass
    return added

def add_text_file(man, path, dry_run=False):
    """登记文本内核资产到 MANIFEST text_assets"""
    ext = os.path.splitext(path)[1].lower()
    size = os.path.getsize(path)
    dom = classify(path)
    if dom == 'misc':
        dom = 'kernel-docs'
    entry = {
        "rel_path": path.replace("/home/user/", "home/"),
        "file": os.path.basename(path),
        "ext": ext,
        "size": size, "size_mb": round(size/1048576, 3),
        "sha256": None if size > 50*1048576 else sha256_file(path),
        "domain": dom,
        "added_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    }
    man.setdefault("text_assets", [])
    # 去重：已存在同路径则跳过
    existing = {t.get('rel_path') for t in man['text_assets']}
    if entry['rel_path'] in existing:
        return None
    man['text_assets'].append(entry)
    return entry

def refresh_text(man, roots, dry_run=False):
    """全量扫描文本内核差异（限体系关键目录，避免扫描全部chats）"""
    existing = {t.get('rel_path') for t in man.get('text_assets', [])}
    added = 0
    for root in roots:
        if not os.path.isdir(root): continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in {'.git','node_modules','site-packages','.cache','__pycache__','.sessions','media_archive'}]
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in TEXT_EXTS: continue
                if ext in MEDIA_EXTS and ext == '.svg': continue  # svg归媒体
                p = os.path.join(dirpath, fn)
                if p in existing: continue
                try:
                    e = add_text_file(man, p, dry_run)
                    if e and not dry_run:
                        print(f"  + [text:{e['domain']}] {os.path.basename(p)}")
                        added += 1
                    elif e:
                        added += 1
                except OSError:
                    pass
    return added

def main():
    ap = argparse.ArgumentParser(description='数据湖自动归档钩子')
    ap.add_argument('--add', help='登记单个新媒体资产文件')
    ap.add_argument('--refresh', action='store_true', help='全量重扫媒体新增差异')
    ap.add_argument('--text-add', help='登记单个文本内核资产')
    ap.add_argument('--text-refresh', action='store_true', help='全量扫描文本内核新增差异')
    ap.add_argument('--dry-run', action='store_true', help='预览不写入')
    ap.add_argument('--roots', nargs='*', default=['/home/user/Doubao/chats', '/home/user/ZONGYUAN-ROOT'],
                    help='refresh扫描根')
    args = ap.parse_args()

    if args.text_add or args.text_refresh:
        man = json.load(open(MAN_PATH))
        if args.text_add:
            if not os.path.exists(args.text_add):
                print(f"❌ 文件不存在: {args.text_add}"); sys.exit(1)
            e = add_text_file(man, args.text_add, args.dry_run)
            if e:
                print(f"{'[DRY] ' if args.dry_run else '✅ '}文本登记 [{e['domain']}] {e['file']} ({e['size_mb']}MB)")
            else:
                print("⏭️ 已存在，跳过")
        elif args.text_refresh:
            print("扫描文本内核差异...")
            n = refresh_text(man, args.roots, args.dry_run)
            print(f"{'[DRY] ' if args.dry_run else '✅ '}新增文本登记 {n} 个")
        if not args.dry_run:
            man['updated'] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
            man['text_asset_count'] = len(man.get('text_assets', []))
            with open(MAN_PATH, 'w', encoding='utf-8') as f:
                json.dump(man, f, ensure_ascii=False, indent=2)
            print(f"MANIFEST text_assets: {man['text_asset_count']} 个")
        return

    reg = load_reg()
    if args.add:
        if not os.path.exists(args.add):
            print(f"❌ 文件不存在: {args.add}"); sys.exit(1)
        dom, e = add_file(reg, args.add, args.dry_run)
        print(f"{'[DRY] ' if args.dry_run else '✅ '}登记 [{dom}] {e['file']} ({e['size_mb']}MB) sha256={str(e['sha256'])[:12]}...")
        if not args.dry_run:
            save_reg(reg)
    elif args.refresh:
        print("扫描新增差异...")
        n = refresh(reg, args.roots, args.dry_run)
        print(f"{'[DRY] ' if args.dry_run else '✅ '}新增登记 {n} 个资产")
        if not args.dry_run:
            save_reg(reg)
            # 同步更新MANIFEST total
            man = json.load(open(MAN_PATH))
            total_files = sum(d['file_count'] for d in reg)
            total_mb = round(sum(d['total_mb'] for d in reg), 2)
            man['total'] = {"file_count": total_files, "total_mb": total_mb}
            man['updated'] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
            with open(MAN_PATH, 'w', encoding='utf-8') as f:
                json.dump(man, f, ensure_ascii=False, indent=2)
            print(f"MANIFEST total 已同步: {total_files}文件 {total_mb}MB")
    else:
        ap.print_help()

if __name__ == '__main__':
    main()
