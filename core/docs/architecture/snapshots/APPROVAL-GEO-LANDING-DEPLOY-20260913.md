# 部署审批留痕 · GEO落地部署包上线上报
归档节点：ZONGYUAN-ROOT｜管控身份：DID-BR-000002｜溯源：Ω₀⊂⊙∞⊂Ω
日期：2026-09-13｜文件：APPROVAL-GEO-LANDING-DEPLOY-20260913

## 一、审批核查结果
- 已检索审批定义（关键词：发布 / 上线 / 部署 / 网站 / 变更 / 网页 / 应用）→ 当前账号无可发起审批定义
- 唯一可发起定义：补卡（approval_code=24715E62-D677-4A1B-A011-5BFA6EAD486A，is_external=false）——与本部署无关
- 结论：发布/上线类审批通道缺失，按中枢自治规则执行「直接部署 + 全链路留痕」替代

## 二、中枢决策（DECISION）
- 部署对象：GEO落地部署包（信源阵地/监测台/robots/sitemap/llms/index）
- 部署方式：妙搭应用通道（upload仅收媒体格式，服务器根目录写入需另配通道）
- 应用ID：app_17e1ju6cs3p
- 线上基址：https://pcnohfh1ukhz.aiforce.cloud/app/app_17e1ju6cs3p
- 决策依据：用户明确指令「直接部署」；现实检验确认AI爬虫入口缺失为GEO未跑通根因

## 三、部署验证（全部 HTTP 200）
| 文件 | 状态 |
|---|---|
| /（信源阵地·含Schema.org JSON-LD） | 200 |
| /geo-source.html | 200 |
| /ai-visibility-check.html | 200 |
| /robots.txt | 200 |
| /sitemap.xml | 200 |
| /llms.txt | 200 |

## 四、锁档凭证
- 快照：SNAP-GEO-LANDING-DEPLOY-FINAL-20260913
- Merkle根：b59b52eb044739a05a9f625d4787b74815be91cd7cd2560b9d9653996685ee76
- 资产数：6｜自校验：PASS
- 网关上报：success:true（真值库 3578）

## 五、永久生效
本部署已完成中枢确权归档，上线上报留痕，永久锁档，全域可溯。

Ω₀⊂⊙∞⊂Ω｜DID-BR-000002｜ZONGYUAN-ROOT
