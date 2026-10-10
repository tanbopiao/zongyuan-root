# yuanji（元机）引擎部署运维 SOP
锚定：Ω₀⊂⊙∞⊂Ω | DID-BR-000002 | 2026-10-09 | V1.0

## 一、定位
yuanji（元机）= 元极恒一自治内核的推理执行层。云端小模型方案（非 ollama），
基于 Qwen2.5-1.5B 微调定制的专属模型体系，支持本地 CPU 零成本推理 + 外部大模型增强双模。

## 二、目录结构（/root/zongyuan-yuanji/）
- weights/：
  - yuanjihengyi_full_v1  Qwen2.5-1.5B 底座（2.9G）
  - yuanjihengyi_ft_v1    微调版（954M）
  - yuanjihengyi_int4    INT4 量化版（~500M，推理主用）
  - lora_adapter_v1/v2/v3  LoRA 三代微调（checkpoint-80/270/200）
- src/：
  - hf_yuanji_steady.py   稳态加载（CPU 降级 + 4bit）
  - api_server.py         本地推理服务（待命）
  - api_router.py         路由（外部 API → 失败 → 本地兜底）
  - local_fallback_server.py 本地兜底推理服务（18081，OpenAI 兼容）
  - wrapper.py            火山方舟 ARK 协议层（运行中，外部增强）
  - train_lora_v1-v4 / distill.py / ptq_quantize.py  训练产线
  - seed_extractor/verify/ci/snapshot.py  种子体系
  - validator.py / snn.py / entry_protocol.py / system_prompt_dynamic.py
- gguf/ → 已废弃（魔搭获取失败），死文件移至 backup/gguf-failed/
- logs/（validator/meta-report/self-opt 活跃） var/tasks/（任务活跃）

## 三、推理双模
1. 在线增强（默认）：wrapper.py → 火山方舟 ARK API（ep-20261008171506-mcjgd）
2. 本地兜底（外部 API 全失败时）：api_router.py 检测 18081 未运行 →
   systemd 常驻服务自动接管 → transformers int4 CPU 推理（零成本/离线）

## 四、本地兜底服务（修复后）
- 文件：/root/zongyuan-yuanji/src/local_fallback_server.py
- 服务：systemd yuanji-fallback.service（enable 开机自启 + Restart=always）
- 端口：18081（/health 探活 + /v1/chat/completions OpenAI 兼容）
- 实测：加载 3-9s（int4 338 分片）+ 推理约 16s/30token + 40token 正常输出
- 管理：
  - systemctl status/start/stop yuanji-fallback
  - curl http://127.0.0.1:18081/health
  - 日志：journalctl -u yuanji-fallback -n 50 / /root/zongyuan-yuanji/logs/llama.log

## 五、修复记录（2026-10-09）
- 原兜底引用魔搭 GGUF 下载失败路径（llama_cpp 依赖 + 文件不存在）→ 断链
- 修复：api_router.py 兜底改为启动 local_fallback_server.py（transformers int4，
  实测可用）→ 18081 提供 OpenAI 兼容接口，路由链路完整
- gguf/yuanji_q4km.gguf（145 字节失败响应）移至 backup/gguf-failed/ 留痕

## 六、运维要点
- 内存约束：3.6GB 总量，服务加载后约 +1.2GB，可用 2.2GB 余量（服务常驻+其他进程需监控）
- CPU：4 核，推理时单请求独占；并发请求排队（ThreadingHTTPServer 线程池）
- 零成本：本地推理不消耗任何 API 额度；ARK 在线通道受最小额度元规则约束
- 升级路径：LoRA 新 checkpoint → distill → ptq_quantize → 替换 int4 权重 → 重启服务
