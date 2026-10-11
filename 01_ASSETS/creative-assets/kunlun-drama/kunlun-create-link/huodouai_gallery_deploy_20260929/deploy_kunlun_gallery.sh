#!/usr/bin/env bash
# ============================================================================
# deploy_kunlun_gallery.sh — 昆仑洞天关键帧画廊 一键部署脚本
# 目标站点: https://www.huodouai.com/gallery/kunlun-keyframes/
# 确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω | ZONGYUAN-ROOT
#
# ⚠️⚠️⚠️ 重要声明 ⚠️⚠️⚠️
# 本脚本由【用户本人】在【本地】执行；它会通过 SSH/rsync 连接到您的服务器。
# 本方案包【不会】替您连接服务器，也【不包含】任何真实服务器凭据。
# 执行前必须 export 下列占位符变量（替换为您自己的服务器信息）：
#   export SERVER_HOST='您的服务器IP或域名'
#   export SERVER_USER='SSH登录用户(如 root/ubuntu)'
#   export SERVER_PORT='SSH端口(如 22)'
#   export SSH_KEY='私钥文件路径(如 ~/.ssh/id_rsa)'
# 可选：
#   export HTML_SRC='本地画廊HTML路径'   # 默认取同目录下 昆仑洞天作品关键帧画廊.html
#   export SITE_DIR='/var/www/kunlun-keyframes'   # 服务器端站点目录
#   export DRY_RUN=1   # 仅打印将要执行的命令，不实际连接/变更
# ============================================================================
set -euo pipefail

# ---------- 0. 占位符环境变量强制检查 ----------
# 任何一项未设置，立即退出并提示用户填写。绝不硬编码真实凭据。
: "${SERVER_HOST:?❌ 未设置 SERVER_HOST —— 请执行: export SERVER_HOST='[用户提供: 服务器IP或域名]'}"
: "${SERVER_USER:?❌ 未设置 SERVER_USER —— 请执行: export SERVER_USER='[用户提供: SSH登录用户]'}"
: "${SERVER_PORT:?❌ 未设置 SERVER_PORT —— 请执行: export SERVER_PORT='[用户提供: SSH端口，通常22]'}"
: "${SSH_KEY:?❌ 未设置 SSH_KEY —— 请执行: export SSH_KEY='[用户提供: 私钥路径，如 ~/.ssh/id_rsa]'}"

# ---------- 1. 可配置项（均有默认值，可用环境变量覆盖）----------
HTML_SRC="${HTML_SRC:-$(dirname "$0")/../昆仑洞天作品关键帧画廊.html}"
SITE_DIR="${SITE_DIR:-/var/www/kunlun-keyframes}"
NGINX_CONF="${NGINX_CONF:-/etc/nginx/conf.d/kunlun-keyframes.conf}"
DOMAIN="${DOMAIN:-www.huodouai.com}"
PUBLIC_PATH="/gallery/kunlun-keyframes/"
BACKUP_SUFFIX=".bak.$(date +%Y%m%d_%H%M%S)"
DRY_RUN="${DRY_RUN:-0}"

# SSH 公共参数
SSH_OPTS="-i ${SSH_KEY} -p ${SERVER_PORT} -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15"
SSH_CMD="ssh ${SSH_OPTS} ${SERVER_USER}@${SERVER_HOST}"
RSYNC_OPTS="-avz -e 'ssh -i ${SSH_KEY} -p ${SERVER_PORT} -o StrictHostKeyChecking=accept-new'"

echo "════════════════════════════════════════════════════════════"
echo "  昆仑洞天关键帧画廊 · 一键部署"
echo "  目标: https://${DOMAIN}${PUBLIC_PATH}"
echo "  服务器: ${SERVER_USER}@${SERVER_HOST}:${SERVER_PORT}"
echo "  本地HTML: ${HTML_SRC}"
echo "  服务器目录: ${SITE_DIR}"
[ "$DRY_RUN" = "1" ] && echo "  🔍 DRY_RUN=1 —— 仅打印命令，不实际执行"
echo "════════════════════════════════════════════════════════════"
echo ""

# ---------- 2. 本地前置检查 ----------
echo "【步骤 1/5】本地前置检查"
if [ ! -f "$HTML_SRC" ]; then
    echo "  ❌ 本地画廊文件不存在: $HTML_SRC"
    echo "     请先确认画廊已生成，或 export HTML_SRC=正确路径"
    exit 1
fi
echo "  ✅ 画廊文件存在: $(wc -c < "$HTML_SRC") 字节"

# 运行自检脚本（同目录下 preflight_check.sh）
PREFLIGHT="$(dirname "$0")/preflight_check.sh"
if [ -f "$PREFLIGHT" ]; then
    echo "  运行 preflight_check.sh ..."
    HTML_SRC="$HTML_SRC" bash "$PREFLIGHT" || {
        echo "  ❌ 自检未通过，终止部署。"
        exit 1
    }
else
    echo "  ⚠️ 未找到 preflight_check.sh，跳过自检"
fi
echo ""

# ---------- 3. 推送 HTML 到服务器 ----------
echo "【步骤 2/5】推送画廊 HTML 到服务器 (rsync)"
REMOTE_TMP="/tmp/kunlun_gallery_$(date +%s).html"
RSYNC_CMD="rsync ${RSYNC_OPTS} '${HTML_SRC}' ${SERVER_USER}@${SERVER_HOST}:${REMOTE_TMP}"
echo "  执行: $RSYNC_CMD"
if [ "$DRY_RUN" = "1" ]; then
    echo "  [DRY_RUN] 跳过实际 rsync"
else
    # shellcheck disable=SC2086
    rsync -avz -e "ssh -i ${SSH_KEY} -p ${SERVER_PORT} -o StrictHostKeyChecking=accept-new" \
        "$HTML_SRC" "${SERVER_USER}@${SERVER_HOST}:${REMOTE_TMP}"
fi
echo "  ✅ 已推送到服务器临时路径: $REMOTE_TMP"
echo ""

# ---------- 4. 服务器端：备份 + 部署 + nginx ----------
echo "【步骤 3/5】服务器端：备份旧版本 + 部署新文件"
# 远程命令脚本（heredoc，在服务器上以 root 执行）
REMOTE_SCRIPT=$(cat <<REMOTE_EOF
set -euo pipefail
echo "  [远程] 创建站点目录: ${SITE_DIR}"
sudo mkdir -p "${SITE_DIR}"

# 备份旧 index.html（若存在）
if [ -f "${SITE_DIR}/index.html" ]; then
    sudo cp "${SITE_DIR}/index.html" "${SITE_DIR}/index.html${BACKUP_SUFFIX}"
    echo "  [远程] 已备份旧文件 -> index.html${BACKUP_SUFFIX}"
fi

# 放置新文件
sudo cp "${REMOTE_TMP}" "${SITE_DIR}/index.html"
sudo chown -R www-data:www-data "${SITE_DIR}" 2>/dev/null || sudo chown -R nginx:nginx "${SITE_DIR}" 2>/dev/null || true
sudo chmod 644 "${SITE_DIR}/index.html"
echo "  [远程] 新 index.html 已就位"

# 清理临时文件
rm -f "${REMOTE_TMP}"
REMOTE_EOF
)

echo "  执行远程部署脚本..."
if [ "$DRY_RUN" = "1" ]; then
    echo "  [DRY_RUN] 远程脚本内容预览:"
    echo "$REMOTE_SCRIPT" | sed 's/^/    | /'
else
    # shellcheck disable=SC2029
    echo "$REMOTE_SCRIPT" | $SSH_CMD "bash -s"
fi
echo ""

# ---------- 5. 安装 nginx 配置 ----------
echo "【步骤 4/5】安装 nginx 配置并重载"
# 把同目录下 nginx/kunlun-keyframes.conf 推送到服务器
LOCAL_NGINX_CONF="$(dirname "$0")/nginx/kunlun-keyframes.conf"
if [ -f "$LOCAL_NGINX_CONF" ]; then
    echo "  推送 nginx 配置: $LOCAL_NGINX_CONF -> $NGINX_CONF"
    REMOTE_NGINX_TMP="/tmp/kunlun-keyframes.conf.$$"
    RSYNC_NGINX="rsync -avz -e \"ssh -i ${SSH_KEY} -p ${SERVER_PORT}\" '${LOCAL_NGINX_CONF}' ${SERVER_USER}@${SERVER_HOST}:${REMOTE_NGINX_TMP}"
    if [ "$DRY_RUN" = "1" ]; then
        echo "  [DRY_RUN] $RSYNC_NGINX"
    else
        # shellcheck disable=SC2086
        rsync -avz -e "ssh -i ${SSH_KEY} -p ${SERVER_PORT} -o StrictHostKeyChecking=accept-new" \
            "$LOCAL_NGINX_CONF" "${SERVER_USER}@${SERVER_HOST}:${REMOTE_NGINX_TMP}"
    fi

    REMOTE_NGINX_SCRIPT=$(cat <<NGINX_EOF
set -euo pipefail
# 备份旧 nginx 配置（若存在）
if [ -f "${NGINX_CONF}" ]; then
    sudo cp "${NGINX_CONF}" "${NGINX_CONF}${BACKUP_SUFFIX}"
    echo "  [远程] 已备份旧 nginx 配置 -> ${NGINX_CONF}${BACKUP_SUFFIX}"
fi
sudo cp "${REMOTE_NGINX_TMP}" "${NGINX_CONF}"
rm -f "${REMOTE_NGINX_TMP}"
echo "  [远程] nginx 配置已写入: ${NGINX_CONF}"
echo "  [远程] 校验 nginx 配置..."
sudo nginx -t
echo "  [远程] 重载 nginx..."
sudo systemctl reload nginx 2>/dev/null || sudo nginx -s reload
NGINX_EOF
    )
    if [ "$DRY_RUN" = "1" ]; then
        echo "  [DRY_RUN] 远程 nginx 脚本预览:"
        echo "$REMOTE_NGINX_SCRIPT" | sed 's/^/    | /'
    else
        # shellcheck disable=SC2029
        echo "$REMOTE_NGINX_SCRIPT" | $SSH_CMD "bash -s"
    fi
else
    echo "  ⚠️ 未找到本地 nginx 配置: $LOCAL_NGINX_CONF"
    echo "     请手动将 nginx/kunlun-keyframes.conf 上传到服务器 $NGINX_CONF"
fi
echo ""

# ---------- 6. 部署后验证 ----------
echo "【步骤 5/5】部署后验证"
VERIFY_URL="https://${DOMAIN}${PUBLIC_PATH}"
echo "  验证 URL: $VERIFY_URL"
if [ "$DRY_RUN" = "1" ]; then
    echo "  [DRY_RUN] 跳过实际验证"
else
    sleep 2
    CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$VERIFY_URL" || echo "000")
    echo "  HTTP 状态码: $CODE"
    if [ "$CODE" = "200" ]; then
        echo "  ✅ 画廊已上线: $VERIFY_URL"
    else
        echo "  ⚠️ 状态码非 200（$CODE），可能原因："
        echo "     - nginx 配置未生效（等待几秒后重试）"
        echo "     - 该路径被 SPA fallback 拦截（需检查 location 优先级）"
        echo "     - DNS/HTTPS 证书问题"
    fi
    # 检查 DID 响应头
    DID_HEADER=$(curl -sI --max-time 10 "$VERIFY_URL" | grep -i "x-did" || true)
    if [ -n "$DID_HEADER" ]; then
        echo "  ✅ DID 响应头: $DID_HEADER"
    else
        echo "  ⚠️ 未检测到 X-DID 响应头（若 nginx 配置已加，可能被上层代理覆盖）"
    fi
fi
echo ""

echo "════════════════════════════════════════════════════════════"
echo "  部署完成"
echo "  画廊地址: https://${DOMAIN}${PUBLIC_PATH}"
echo "  服务器目录: ${SITE_DIR}"
echo "  nginx 配置: ${NGINX_CONF}"
echo "  回滚: 服务器上执行"
echo "    sudo cp ${SITE_DIR}/index.html${BACKUP_SUFFIX} ${SITE_DIR}/index.html"
echo "    sudo systemctl reload nginx"
echo "  确权: DID-BR-000002 | Ω₀⊂⊙∞⊂Ω"
echo "════════════════════════════════════════════════════════════"
