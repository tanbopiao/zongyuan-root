# OP-ASSET-REPORT-010｜月度资产报表算子

> 算子编号：OP-ASSET-REPORT-010
> 归属体系：ZONGYUAN-ROOT 运营层
> 状态：契约定稿 v1.0

---

## 一、真值契约

### 目标
每月初自动汇总上月资产数据：图片总量、视频总量、分类分布、新增量、对外公开量、巡检异常数，输出结构化月报 Markdown。

### 执行流程
```
Step1  读取 manifest.md 全量记录
Step2  按月份筛选上月新增资产
Step3  统计维度：
        - 总资产数（图片/视频/文档）
        - 分类分布（按主题目录）
        - 公开/私有比例
        - 新增趋势（对比上月）
        - 巡检异常数（从OP-VERIFY-002日志读取）
        - 魔搭同步状态
Step4  生成 monthly-report-YYYYMM.md
Step5  推送至飞书云盘指定文件夹
Step6  输出回执
```

### 输入
```json
{
  "op_name": "OP-ASSET-REPORT-010",
  "manifest_path": "/archive/manifest.md",
  "report_month": "2026-10",
  "lark_upload_enabled": true,
  "lark_folder_token": ""
}
```

### 输出月报结构
```markdown
# 昆仑洞天资产月报｜2026年10月

## 总览
- 总资产：XX 件（图片 XX / 视频 XX / 文档 XX）
- 本月新增：XX 件
- 公开资产：XX 件（XX%）
- 私有资产：XX 件（XX%）

## 分类分布
| 主题 | 数量 | 占比 |
|---|---|---|
| 昆仑洞天 | XX | XX% |
| 三亚度假 | XX | XX% |
| ... | | |

## 运营异常
- 巡检告警：X 起
- 魔搭同步：成功/失败
- 备份状态：正常/异常
```

### 禁止项
- ❌ 月报中不泄露 private 资产的具体内容
- ❌ 不修改 manifest.md，只读统计
- ❌ 不输出原始文件路径

---

## 二、测试用例

| 编号 | 场景 | 预期 |
|---|---|---|
| TC-01 | 10月有40条记录 | 月报统计数=40，分类占比合计100% |
| TC-02 | 上月无新增 | 月报显示0新增，不报错 |
| TC-03 | 巡检有3起告警 | 月报异常栏列出3起 |
| TC-04 | private资产不泄露内容 | 月报只显示数量，不显示文件名 |
| TC-05 | 飞书上传成功 | 回执 lark_upload=success |
