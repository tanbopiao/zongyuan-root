# OP-SYNC-MODEL-006｜魔搭数据湖资产同步算子

> 算子编号：OP-SYNC-MODEL-006
> 归属体系：ZONGYUAN-ROOT 对外资产发布
> 状态：契约定稿 v1.0

---

## 一、真值契约

### 目标
从本地归档账本筛选标记 public 的资产，脱敏后增量同步至魔搭数据集；private 资产直接跳过，禁止外泄。

### 执行流程
```
Step1  读取 manifest.md 归档账本
Step2  筛选 privacy_level = public 的资产记录
Step3  校验选中文件哈希完整性（调用 OP-VERIFY-002 子校验）
Step4  读取配套元数据，剥离内部 DID、账本标记、本地路径（脱敏）
Step5  按魔搭数据集目录结构打包素材、提示词、README
Step6  调用魔搭 API，增量上传，哈希一致则跳过
Step7  在本地 manifest 追加同步记录，标记魔搭数据集版本号
Step8  输出同步回执
```

### 禁止项
- ❌ 禁止同步 private 隐私资产
- ❌ 禁止上传原始内部账本、DID凭证、密钥
- ❌ 禁止覆盖魔搭内已存在且哈希一致的文件
- ❌ 同步失败时不修改本地 manifest 原有记录

### 异常分支
| 异常 | 处理 |
|---|---|
| 网络中断 | 记录断点，下次增量续传 |
| 哈希校验失败 | 跳过该文件，告警，不继续上传 |
| 魔搭 API 配额耗尽 | 终止任务，输出告警，记录断点 |
| 无 public 资产 | 退出，回执标记 no_public_asset |

---

## 二、输入输出 Schema

### 输入
```json
{
  "op_name": "OP-SYNC-MODEL-006",
  "manifest_path": "/archive/manifest.md",
  "modelscope_dataset_id": "kunlun-dongtian-gallery",
  "dry_run": false,
  "batch_size": 10
}
```

### 输出回执
```json
{
  "op_name": "OP-SYNC-MODEL-006",
  "run_timestamp": "2026-10-10T23:40:00+08:00",
  "summary": {
    "total_public_asset": 12,
    "upload_new": 3,
    "skip_exist": 9,
    "sync_fail": 0
  },
  "dataset_version": "v0.1.2",
  "breakpoint": null,
  "warnings": []
}
```

---

## 三、测试用例

| 编号 | 场景 | 预期 |
|---|---|---|
| TC-01 | 存在 public 资产，首次上传 | 打包脱敏后上传，账本追加同步记录 |
| TC-02 | 资产已在魔搭，哈希一致 | 跳过，标记 skip_exist |
| TC-03 | 全部资产 private | no_public_asset，无上传动作 |
| TC-04 | 待同步文件哈希校验失败 | 跳过，告警，其余继续 |
| TC-05 | 上传中途断网 | 保存断点，下次续传 |
| TC-06 | dry_run=true | 只生成打包预览，不调用上传API |
