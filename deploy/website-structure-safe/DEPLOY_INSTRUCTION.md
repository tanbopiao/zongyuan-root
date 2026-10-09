# 官网结构安全部署指令 (V1.0)
> 生成: 2026-09-30 | 审批: 密钥授权F3CFCFA0已APPROVED | 授权: DEPLOY.ORDER.WEBSITE-STRUCTURE-SAFE.20260930

## 一、官网现状结构（已探明，nginx静态站）
| 路径 | 类型 | 状态 |
|------|------|------|
| / | 首页 index.html | 独立文件 ✅ |
| /showcase/ | 真实作品展示 | 独立文件 ✅ |
| /architecture | 架构总览 | 独立文件 ✅ |
| /pricing/ | 定价方案 | 独立文件 ✅ |
| /products/ | 产品矩阵 | 独立文件 ✅ |
| /solutions/ | 行业解决方案 | 独立文件 ✅ |
| /docs/ | API文档中心 | 独立文件 ✅ |
| /modelscope/whitepaper/xxx.html | 白皮书 | ⚠️ 当前fallback首页(未落盘) |

## 二、部署约束（禁止破坏现有结构）
1. 所有新增页面走子路径/子目录，禁止覆盖 / /showcase/ /architecture 等独立页面
2. 白皮书目标: /modelscope/whitepaper/火斗云智AIOS架构白皮书V1.0.html
   - 若目标已存在同名文件: 先 mv 备份为 .bak.<时间戳> 再覆盖
   - 该URL当前返回首页内容(nginx fallback), 需真实落盘
3. 部署后验证: curl 该URL, 内容必须包含"火斗云智AIOS架构白皮书"标题, 不得等于首页

## 三、执行步骤（云端Worker在服务器本地执行）
```bash
# 1. 确认站点根目录(nginx root)
grep -r "root" /etc/nginx/conf.d/*.conf /etc/nginx/sites-enabled/* 2>/dev/null | grep -v "#" | head -5

# 2. 从双仓拉取最新部署包
cd /opt/ZONGYUAN-ROOT && git pull origin main 2>/dev/null

# 3. 备份已有同名文件(如有)
DST="<站点根>/modelscope/whitepaper"
mkdir -p "$DST"
if [ -f "$DST/火斗云智AIOS架构白皮书V1.0.html" ]; then
  cp "$DST/火斗云智AIOS架构白皮书V1.0.html" "$DST/火斗云智AIOS架构白皮书V1.0.html.bak.$(date +%Y%m%d%H%M%S)"
fi

# 4. 拷贝新资产
cp "/opt/ZONGYUAN-ROOT/deploy/modelscope/whitepaper/火斗云智AIOS架构白皮书V1.0.html" "$DST/"

# 5. 验证
curl -s "https://www.huodouai.com/modelscope/whitepaper/火斗云智AIOS架构白皮书V1.0.html" | grep -c "架构白皮书"
# 返回 >=1 即成功; 若返回0则检查nginx配置

# 6. 上报结果
curl -X POST https://www.huodouai.com/api/report/truth -H "Content-Type: application/json" \
  -d '{"key":"RESULT.DEPLOY-WEBSITE.20260930","truth_value":"官网白皮书已真实落盘","source_node":"hub-central-agent","confidence":1.0,"truth_type":"result"}'
```

## 四、验收标准
- [ ] 白皮书URL返回独立内容(非首页fallback)
- [ ] 现有页面 / /showcase/ /architecture 全部保持200且内容不变
- [ ] RESULT.DEPLOY-WEBSITE.20260930 已上报网关
