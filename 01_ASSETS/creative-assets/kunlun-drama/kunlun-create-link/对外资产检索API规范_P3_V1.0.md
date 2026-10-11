# ZONGYUAN-ROOT 对外资产检索 API 规范（P3 落地）

> 确权：DID-BR-000002 · 锚定 Ω₀⊂⊙∞⊂Ω · 2026-09-29 · 版本 V1.0

## 一、对外服务三层

| 层 | 载体 | 用途 |
|---|---|---|
| 静态检索台 | `对外资产检索台_20260929.html` | 人类可读的资产检索界面（浏览器打开） |
| 魔搭数据 API | `modelscope.cn` dataset API | 资产文件公开下载/检索 |
| 记忆网关 API | `huodouai.com/api/report/truth` | 真值上报/确权登记 |

## 二、魔搭数据湖资产检索 API

数据源：`zongyuanroot/zongyuan-root-achievements`（dataset）

### 2.1 文件存在性 / 下载

```
GET https://www.modelscope.cn/api/v1/datasets/{repo}/repo?Revision=master&FilePath={urlencoded_path}
```

- 需 `Authorization: Bearer <token>`（凭据从共享大脑 API密钥池 取）
- 返回文件内容；图片以 `\xff\xd8`、视频 `ftyp`、zip `PK` 开头验证

### 2.2 资产台账（shared_brain.db）

```
GET https://www.modelscope.cn/api/v1/datasets/zongyuanroot/zongyuan-root-achievements/repo?Revision=master&FilePath=shared_brain.db
```

- SQLite 库，表 `assets(id,name,category,path,sha256,locked_at)`
- `path` 使用 `modelscope://<repo>/<subdir>/<rel>` 协议

### 2.3 数据湖目录结构

```
data_lake/
├── jiutian-xuannv-keyframes-20260929/   # 关键帧账本/台账/回执
├── jiutian-xuannv-videos-20260929/      # 视频账本/台账/回执
├── kunlun-create-link/                  # 凭证/SOP/脚本/待补档
├── root-archive-20260929/               # 本地根目录 43 主题 zip
└── runtime-full-20260929/               # 运行实例 5 大 zip
```

## 三、记忆网关 API

```
POST https://www.huodouai.com/api/report/truth
Content-Type: application/json
{
  "truth_value": "<JSON字符串化 payload>",
  "truth_type": "meta_law|rule|config|decision|data|creative|risk|protocol|unknown"
}
```

- 成功标志：`status=reported` 且 `written_to_gateway=true`
- 禁止用 `content` 字段（会导致 value 落空）

## 四、部署步骤（云服务器）

1. 在云服务器执行 `deploy_asset_portal.sh`（见同目录）
2. 检索台静态托管于站点根目录 `asset-portal/`
3. 数据更新：本地跑 `kunlun_unified_pipeline.py` 入湖 → 重新生成 `对外资产检索台_*.html` → 覆盖云服务器同名文件

## 五、验收清单

- [ ] 检索台浏览器可打开，搜索/筛选正常，统计看板正确
- [ ] 魔搭 data_lake 文件可经 API 下载验证
- [ ] shared_brain.db 台账与检索台索引一致
- [ ] 记忆网关上报 success
- [ ] 确权标识 DID-BR-000002 · Ω₀⊂⊙∞⊂Ω 完整
