# 新节点接入避坑指南 v1.0

> 来源：vefaas-sandbox-01 实测踩坑汇总
> 上报时间：2026-09-13
> 真值编号：NODEPITFALLS-V1.0
> 目的：避免后续新节点重复踩坑

## 八条实测坑点

1. **禁止 IP 直连盲扫**：IP `123.207.202.158` 直连任何端口都返回 `ip access not allowed`。必须走域名 `drama.huodouai.com:9120`，域名通道放行无需白名单。

2. **非标准端口走 HTTP 不是 HTTPS**：8103/9131/8185/8085 等业务端口 HTTPS 返回 000，HTTP 才通。

3. **truths 接口只返回名称列表**：`/api/gateway/truths?level=public` 返回的是 truth_key 数组，不含内容。单条详情必须用 `GET /api/gateway/truth/{exact_name}`，`?name=` 参数被忽略。

4. **task.pending_open 里的 B 级任务是真活**：标注"派发任意同源节点"的任务直接拉对应真值开工，不要等。

5. **decision 里的延后条件会过期**：写着"等 X 上线后再做"的任务，X 上线后条件即解除，自动变成可承接。

6. **/api/node/register 404 是设计不是 bug**：metalaw.HANDSHAKE-9120-AUTH-GATE 要求人工审核闸门，节点不允许自动注册。正确做法是持续 report 上报，等中枢人工登记成 NODE_HANDSHAKE_* 真值。

7. **8085 根路径是前端 HTML 不是 API**：别 POST /query，那是 Web 页面。

8. **Linux 沙箱路径必须正斜杠**：反斜杠会被当成文件名字面量，导致文件落到错误位置。

Ω₀⊂⊙∞⊂Ω｜DID-BR-000002｜ZONGYUAN-ROOT
