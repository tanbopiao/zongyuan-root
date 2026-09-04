# 全域锁档凭证 | MR-04双域名部署元规则

| 字段 | 值 |
|------|-----|
| 锁档ID | LOCK-MR04-DUALDOMAIN-20260904_090212 |
| 锁档时间 | 2026-09-04 09:02:12 +0800 |
| 确权DID | DID-BR-000002 |
| 本体主权根 | Ω-TAN-7-001 |
| 溯源符号 | Ω₀⊂⊙∞⊂Ω |
| 资产总数 | 3个 |
| Merkle根哈希 | 43afbd2a6ab298541fd76ff262eca2c634b040369bf4f231d449151cb0212df1 |
| 锁档等级 | META-003（元规则级，不可覆写不可旁路） |
| eFuse状态 | BLOWN_PERMANENT |

## 锁档资产清单

```
243dc1fc41d7616b71d86fd5ebbe793f8bd54b5c18d52299b9a8ae74c4807bc2  huodouai.com.conf.bak.20260904
9c70dfab6a59865c6ebb1d6a22f231d7ae0c1686dde5108ea257131a969fb414  MANIFEST_SHA256.txt
d20ce188c3ef59399409345bfe14680f6bf25e12edc4a85986f0c8068e9c84d9  MR-04_DUAL_DOMAIN_DEPLOYMENT.md
367f00d4591b9d81c2b9618178de4a7a8190e16e468bf38f3e1c23bd645bc966  nginx_huodouai.conf
```

## 元规则摘要

MR-04：双域名兼容式增量进化部署元规则
- 统一内容源：所有前端只部署到 /www/wwwroot/huodouai.com/
- 双域名分工：huodouai.com=品牌门户，www.huodouai.com=技术交付
- Nginx只增不删，API Key统一在Nginx固定注入
- 部署SOP：单目录部署→双域名验证→旧版本备份保留
- 回滚方案：配置备份+前端版本备份

## 校验状态

- 逐文件SHA256: ✅ 全部计算完成
- Merkle-DAG: ✅ 根哈希已生成
- 双域名入口验证: ✅ 8/8正常
- Nginx语法: ✅ nginx -t通过
- eFuse熔断: ✅ BLOWN_PERMANENT

Ω₀⊂⊙∞⊂Ω｜LOCK-MR04-DUALDOMAIN-20260904_090212｜ZONGYUAN-ROOT｜DID-BR-000002
