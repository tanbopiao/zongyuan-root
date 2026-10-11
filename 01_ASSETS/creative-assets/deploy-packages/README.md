# deploy-packages

本目录存放元极恒一/火斗云智体系的部署与运维压缩包，平铺放置。每个包均附 SHA-256 校验值，便于对外展示可溯源。

## 包清单与用途概要

| 文件名 | 用途概要 | SHA-256 |
|---|---|---|
| huodouai-deploy-v2.0.zip | 火斗云智 AIOS V2.0 完整部署包 | `11f04b47fc73ee7579ed87d45a57e4697b71b0d6af2f5bd1095b5e8b42cd7793` |
| huodouai-deploy.tar.gz | 火斗云智部署包 tar.gz 压缩格式（同内容备份） | `09409aaf6128649899d502531d0af5baa703c8854163055351c5d2f04aff9a3e` |
| 产品矩阵V2部署包.zip | 产品矩阵 V2 版本一键部署包 | `e4b51bcb8981fc7d3c4d3f81a23137cd46085664f642894781742714dc899594` |
| kunlun-gallery-rose.zip | 昆仑洞天画廊/图片素材资源包（rose 主题） | `a107b9c9f13b8132ad06a0bad2d5d9622fc7228623eee24843bc22d00759d911` |
| memory-gateway-fix-v1.0-all.zip | 记忆网关修复补丁 v1.0 全量包（含依赖） | `1f43aaea2fb0eab8e0e07f96a22a42b3fc426a831c9faa7d878822c6fb4f4460` |
| memory-gateway-fix-v1.0.zip | 记忆网关修复补丁 v1.0 主程序包 | `639c3ecb7fa39f2dd8ade220240ffff3a2f8121479c49cb950fe6130a97f83be` |
| nginx-502修复包.zip | Nginx 502 网关错误故障修复包 | `feea1967cb80c0015aef5c2b0c5e831bb9282d78c3e9aa4478d1dad91a092043` |
| sync_channels_bundle.zip | 多渠道同步通道配置与脚本捆绑包 | `fb1b3b2dc3fa071a88277beed6e723e176202d18881900b21d1e39c9f425463d` |
| auto-archive-v1.0.zip | 自动归档守护进程 v1.0 部署包 | `5e1eb88f10030cfc9453ccf146b5365884023ef9d5a5dc522bf03100e9b5b1ab` |

## 校验方法

```bash
cd deploy-packages
sha256sum -c <(awk 'NR>1 {print $4"  "$2}' README.md | tr -d '`')
```
