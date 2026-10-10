# OP-GALLERY-003｜画廊网页自动渲染算子

> 算子编号：OP-GALLERY-003
> 归属体系：ZONGYUAN-ROOT 视觉资产画廊
> 状态：契约定稿 v1.0

---

## 一、真值契约

### 目标
读取 manifest.md 归档账本，自动生成静态画廊 HTML 页面，按主题/系列分组展示图片，private 资产默认隐藏，输出可直接部署的静态站点。

### 执行流程
```
Step1  读取 manifest.md，解析全部记录行
Step2  过滤 privacy_level=private 的资产（默认不渲染，除非 admin_preview=true）
Step3  按主题目录分组（01-祭祖祈福 / 02-昆仑洞天 / 03-三亚度假 / 04-深夜酒店）
Step4  每组生成缩略图网格，图片路径指向 assets/ 相对路径
Step5  生成 index.html，包含：
        - 顶部画廊标题
        - 分组导航
        - 响应式网格（手机1列，平板2列，桌面3列）
        - 点击图片放大 lightbox
        - 每张图下方显示文件名+主题标签
Step6  输出到 /gallery-dist/ 目录（index.html + 资源引用）
Step7  生成 gallery-manifest.json，记录本次渲染的图片清单
```

### 禁止项
- ❌ 禁止渲染 privacy_level=private 的资产（默认）
- ❌ 禁止在 HTML 中硬编码图片绝对路径（用相对路径）
- ❌ 禁止引入外部 CDN 依赖（纯原生 HTML/CSS/JS）
- ❌ 禁止修改原始资产文件

### 异常分支
| 异常 | 处理 |
|---|---|
| manifest.md 缺失 | 报错 `ledger_missing`，不生成空页面 |
| 图片文件不存在 | 跳过该图，记录 `image_missing` 警告 |
| 全部为 private | 输出空画廊提示页，不泄露资产列表 |

---

## 二、输入输出 Schema

### 输入
```json
{
  "op_name": "OP-GALLERY-003",
  "manifest_path": "/archive/manifest.md",
  "asset_root": "/assets/",
  "output_dir": "/gallery-dist/",
  "gallery_title": "昆仑洞天 · 视觉资产画廊",
  "admin_preview": false,
  "columns_desktop": 3,
  "columns_tablet": 2,
  "columns_mobile": 1
}
```

### 输出
```
gallery-dist/
├── index.html
├── gallery-manifest.json
└── assets/  (符号链接或复制)
```

gallery-manifest.json 结构：
```json
{
  "render_timestamp": "2026-10-10T22:40:00+08:00",
  "total_public_images": 12,
  "groups": [
    {"name": "昆仑洞天天元法则", "count": 4},
    {"name": "三亚度假Vlog", "count": 8}
  ],
  "private_hidden": 28
}
```

---

## 三、测试用例

| 编号 | 场景 | 预期 |
|---|---|---|
| TC-01 | 12张public+28张private | 只渲染12张，private_hidden=28 |
| TC-02 | admin_preview=true | 全部40张渲染 |
| TC-03 | manifest缺失 | 报错，不生成HTML |
| TC-04 | 图片文件缺失 | 跳过，警告日志 |
| TC-05 | 响应式布局 | 桌面3列/平板2列/手机1列 |
| TC-06 | 相对路径 | HTML中图片路径为相对路径，可本地打开 |

---

## 四、技术约束
- 纯静态 HTML + 内联 CSS + 原生 JS（无框架）
- 无外部 CDN，可离线打开
- lightbox 用原生 JS 实现
- 输出目录可直接上传到 gallery.huodouai.com 静态托管
