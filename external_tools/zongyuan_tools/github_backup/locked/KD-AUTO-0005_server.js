/**
 * AIOS Proxy - 统一多模型API代理服务
 * 整合：豆包(火山方舟) / 智普AI / 腾讯混元
 * 提供 OpenAI 兼容接口：POST /v1/chat/completions
 */
const http = require('http');
const config = require('./config');
const doubao = require('./providers/doubao');
const zhipu = require('./providers/zhipu');
const hunyuan = require('./providers/hunyuan');
const nvidia = require('./providers/nvidia');
const crossVerify = require('./cross_verify');
const kernel = require('./kernel_inject');

// 厂商适配器映射
const PROVIDERS = {
  doubao,
  zhipu,
  hunyuan,
  nvidia,
};

// 调用统计
const stats = {
  totalRequests: 0,
  successCount: 0,
  errorCount: 0,
  byProvider: {},
  startTime: new Date().toISOString(),
};

/**
 * 解析JSON请求体
 */
function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', (chunk) => { body += chunk; });
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (e) {
        reject(new Error('JSON解析失败'));
      }
    });
    req.on('error', reject);
  });
}

/**
 * 发送JSON响应
 */
function sendJSON(res, statusCode, data) {
  res.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  });
  res.end(JSON.stringify(data, null, 2));
}

/**
 * API密钥认证
 */
function authMiddleware(req, res) {
  // 健康检查和模型列表不需要认证
  if (req.url === '/health' || req.url === '/v1/models') return true;

  const authHeader = req.headers['authorization'] || '';
  const token = authHeader.replace('Bearer ', '').trim();
  if (token !== config.server.apiKey) {
    sendJSON(res, 401, { error: { message: '未授权：API密钥无效', type: 'auth_error' } });
    return false;
  }
  return true;
}

/**
 * 带重试的调用
 */
async function callWithRetry(providerName, params, retries = config.request.maxRetries) {
  const provider = PROVIDERS[providerName];
  if (!provider) throw new Error(`未知厂商: ${providerName}`);

  for (let attempt = 1; attempt <= retries + 1; attempt++) {
    try {
      const result = await provider.chatCompletion(params);
      return result;
    } catch (e) {
      if (attempt <= retries) {
        console.log(`[重试] ${providerName} 第${attempt}次失败: ${e.message}，${config.request.retryDelay}ms后重试`);
        await new Promise(r => setTimeout(r, config.request.retryDelay));
      } else {
        throw e;
      }
    }
  }
}

/**
 * 路由模型到厂商
 */
function resolveModel(modelName) {
  const modelConfig = config.models[modelName];
  if (!modelConfig) {
    // 尝试模糊匹配
    const lower = modelName.toLowerCase();
    for (const [key, val] of Object.entries(config.models)) {
      if (lower.includes(key.toLowerCase()) || key.toLowerCase().includes(lower)) {
        return { provider: val.provider, model: val.model };
      }
    }
    return null;
  }
  return { provider: modelConfig.provider, model: modelConfig.model };
}

/**
 * 处理交叉验证请求
 */
async function handleCrossVerify(req, res) {
  stats.totalRequests++;
  const startTime = Date.now();

  try {
    const body = await parseBody(req);
    const { level = 'L2_standard', messages, temperature, max_tokens } = body;

    if (!messages || !Array.isArray(messages) || messages.length === 0) {
      sendJSON(res, 400, { error: { message: '缺少必填参数: messages', type: 'invalid_request' } });
      stats.errorCount++;
      return;
    }

    if (!Object.keys(crossVerify.VERIFY_LEVELS).includes(level)) {
      sendJSON(res, 400, {
        error: {
          message: `不支持的验证等级: ${level}`,
          type: 'invalid_level',
          available_levels: Object.keys(crossVerify.VERIFY_LEVELS),
        }
      });
      stats.errorCount++;
      return;
    }

    if (config.logging.logRequests) {
      console.log(`[交叉验证] level=${level} msgs=${messages.length}`);
    }

    const result = await crossVerify.crossVerify({ level, messages, temperature, max_tokens });

    stats.successCount++;
    const duration = Date.now() - startTime;
    console.log(`[交叉验证成功] ${level} consensus=${result.consensus} ${duration}ms`);

    sendJSON(res, 200, result);
  } catch (e) {
    stats.errorCount++;
    console.error(`[交叉验证错误] ${e.message}`);
    sendJSON(res, 502, {
      error: {
        message: `交叉验证失败: ${e.message}`,
        type: 'upstream_error',
      }
    });
  }
}

/**
 * 处理聊天补全请求
 */
async function handleChatCompletion(req, res) {
  stats.totalRequests++;
  const startTime = Date.now();

  try {
    const body = await parseBody(req);
    const { model, messages, temperature, max_tokens, stream } = body;

    if (!model || !messages) {
      sendJSON(res, 400, { error: { message: '缺少必填参数: model, messages', type: 'invalid_request' } });
      stats.errorCount++;
      return;
    }

    // 路由模型
    const resolved = resolveModel(model);
    if (!resolved) {
      sendJSON(res, 400, {
        error: {
          message: `不支持的模型: ${model}`,
          type: 'model_not_found',
          available_models: Object.keys(config.models),
        }
      });
      stats.errorCount++;
      return;
    }

    if (config.logging.logRequests) {
      console.log(`[请求] model=${model} → provider=${resolved.provider} resolved=${resolved.model} msgs=${messages.length}`);
    }

    // ===== 同源内核注入（加固版：分级约束 + 幂等）=====
    const injectOpts = {};
    if (body.kernel_disable !== true) {
      // 分级约束：默认standard，请求可指定enhanced
      if (body.kernel_level === 'enhanced' || body.kernel_enhanced === true) {
        injectOpts.level = 'enhanced';
      }
      const injected = kernel.injectKernel(messages, injectOpts);
      const requestHash = kernel.genRequestHash({ model, messages, resolved });
      const idemKey = body.idempotency_key || null;
      // 请求级注入记录（幂等键在 output 阶段才用于去重，避免同请求误判）
      kernel.registerLedger({
        request_hash: requestHash,
        model,
        provider: resolved.provider,
        level: injected.inject_meta.level,
        action: 'kernel_inject',
        content_preview: (messages[messages.length-1]?.content || '').slice(0, 100),
        verify: { passed: true },
      });
      // 用注入后的消息替换
      body.messages = injected.messages;
      // 附加注入元信息到响应
      body._kernel_meta = { ...injected.inject_meta, request_hash: requestHash, idempotency_key: idemKey };
    }

    // 流式响应分支
    if (stream) {
      res.writeHead(200, {
        'Content-Type': 'text/event-stream; charset=utf-8',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'X-Accel-Buffering': 'no',
      });

      const adapter = PROVIDERS[resolved.provider];
      let fullContent = '';
      const streamMessages = body.messages || messages;

      try {
        await adapter.streamChat(resolved.model, streamMessages, { temperature, max_tokens }, (delta, done) => {
          if (delta) {
            fullContent += delta;
            const chunk = {
              id: `chatcmpl-${Date.now()}`,
              object: 'chat.completion.chunk',
              created: Math.floor(Date.now() / 1000),
              model: model,
              provider: resolved.provider,
              choices: [{ index: 0, delta: { content: delta }, finish_reason: null }],
            };
            res.write(`data: ${JSON.stringify(chunk)}\n\n`);
          }
          if (done) {
            // 流式输出规范化：缺失溯源标识自动补全
            let finalContent = fullContent;
            if (body._kernel_meta) {
              const norm = kernel.normalizeOutput(fullContent);
              finalContent = norm.content;
              if (norm.added_symbol) {
                const symChunk = {
                  id: `chatcmpl-${Date.now()}`,
                  object: 'chat.completion.chunk',
                  created: Math.floor(Date.now() / 1000),
                  model: model,
                  choices: [{ index: 0, delta: { content: norm.content.slice(fullContent.length) }, finish_reason: null }],
                };
                res.write(`data: ${JSON.stringify(symChunk)}\n\n`);
              }
              // 流式校验+存证
              const verifyResult = kernel.verifyOutput(finalContent);
              kernel.registerLedger({
                request_hash: body._kernel_meta.request_hash,
                idempotency_key: body._kernel_meta.idempotency_key,
                model,
                provider: resolved.provider,
                level: body._kernel_meta.level,
                action: 'kernel_output_stream',
                content_preview: finalContent.slice(0, 100),
                verify: verifyResult,
                consensus: null,
              });
              console.log(`[流式内核校验] ${resolved.provider} symbol=${verifyResult.checks.has_symbol} len=${finalContent.length}`);
            }
            const finalChunk = {
              id: `chatcmpl-${Date.now()}`,
              object: 'chat.completion.chunk',
              created: Math.floor(Date.now() / 1000),
              model: model,
              choices: [{ index: 0, delta: {}, finish_reason: 'stop' }],
            };
            res.write(`data: ${JSON.stringify(finalChunk)}\n\n`);
            res.write('data: [DONE]\n\n');
            res.end();
          }
        });

        stats.successCount++;
        stats.byProvider[resolved.provider] = (stats.byProvider[resolved.provider] || 0) + 1;
        const duration = Date.now() - startTime;
        console.log(`[流式成功] ${resolved.provider} ${resolved.model} ${duration}ms chars=${fullContent.length}`);
      } catch (e) {
        stats.errorCount++;
        console.error(`[流式错误] ${e.message}`);
        const errChunk = { error: { message: `上游流式错误: ${e.message}`, type: 'upstream_error' } };
        res.write(`data: ${JSON.stringify(errChunk)}\n\n`);
        res.write('data: [DONE]\n\n');
        res.end();
      }
      return;
    }

    // 非流式：调用厂商API（使用注入后的消息）
    const result = await callWithRetry(resolved.provider, {
      model: resolved.model,
      messages: body.messages || messages,
      temperature,
      max_tokens,
      stream,
    });

    // ===== 内核输出校验 + 存证（加固版：规范化 + 幂等 + 链式哈希）=====
    let kernelMeta = body._kernel_meta || null;
    if (kernelMeta) {
      let outContent = result.choices?.[0]?.message?.content || '';
      // 输出强制规范化：缺失溯源标识自动补全
      const norm = kernel.normalizeOutput(outContent);
      if (norm.added_symbol) {
        result.choices[0].message.content = norm.content;
        outContent = norm.content;
      }
      const verifyResult = kernel.verifyOutput(outContent);
      const ledgerBlock = kernel.registerLedger({
        request_hash: kernelMeta.request_hash,
        idempotency_key: kernelMeta.idempotency_key,
        model,
        provider: resolved.provider,
        level: kernelMeta.level,
        action: 'kernel_output',
        content_preview: outContent.slice(0, 100),
        verify: verifyResult,
        consensus: null,
      });
      kernelMeta.output_verify = verifyResult;
      kernelMeta.normalized = norm.normalized;
      if (ledgerBlock && !ledgerBlock.duplicate) {
        kernelMeta.ledger_hash = ledgerBlock.block_hash;
        kernelMeta.prev_hash = ledgerBlock.prev_hash;
        kernelMeta.chain_length = ledgerBlock.chain_length;
      } else if (ledgerBlock && ledgerBlock.duplicate) {
        kernelMeta.duplicate = true;
        kernelMeta.ledger_hash = ledgerBlock.prev_hash;
      }
      // 结果附加内核元信息
      result._kernel = kernelMeta;
    }

    // 统计
    stats.successCount++;
    stats.byProvider[resolved.provider] = (stats.byProvider[resolved.provider] || 0) + 1;

    const duration = Date.now() - startTime;
    console.log(`[成功] ${resolved.provider} ${resolved.model} ${duration}ms tokens=${result.usage?.total_tokens || 0}`);

    sendJSON(res, 200, result);
  } catch (e) {
    stats.errorCount++;
    console.error(`[错误] ${e.message}`);
    sendJSON(res, 502, {
      error: {
        message: `上游API错误: ${e.message}`,
        type: 'upstream_error',
      }
    });
  }
}

// 创建HTTP服务器
const server = http.createServer(async (req, res) => {
  // CORS预检
  if (req.method === 'OPTIONS') {
    sendJSON(res, 200, {});
    return;
  }

  // 路由
  if (req.method === 'GET' && req.url === '/health') {
    sendJSON(res, 200, {
      status: 'ok',
      service: 'aios-proxy',
      version: '1.0.0',
      uptime: process.uptime(),
      providers: Object.keys(config.providers),
      models: Object.keys(config.models),
      kernel: {
        name: kernel.KERNEL.name,
        version: kernel.KERNEL.version,
        did: kernel.KERNEL.did,
        symbol: kernel.KERNEL.symbol,
        inject_enabled: kernel.INJECT_CONFIG.enabled,
        cross_verify_levels: Object.keys(crossVerify.VERIFY_LEVELS),
      },
    });
    return;
  }

  if (req.method === 'GET' && req.url === '/v1/models') {
    sendJSON(res, 200, {
      object: 'list',
      data: Object.entries(config.models).map(([id, val]) => ({
        id,
        object: 'model',
        provider: val.provider,
        created: Math.floor(Date.now() / 1000),
      })),
    });
    return;
  }

  if (req.method === 'GET' && req.url === '/stats') {
    sendJSON(res, 200, {
      ...stats,
      uptime_seconds: Math.floor(process.uptime()),
    });
    return;
  }

  if (req.method === 'POST' && req.url === '/v1/chat/completions') {
    if (!authMiddleware(req, res)) return;
    await handleChatCompletion(req, res);
    return;
  }

  if (req.method === 'POST' && req.url === '/v1/cross-verify') {
    if (!authMiddleware(req, res)) return;
    await handleCrossVerify(req, res);
    return;
  }

  // 内核账本链校验（Merkle-DAG完整性验证）
  if (req.method === 'GET' && req.url === '/v1/kernel/ledger') {
    if (!authMiddleware(req, res)) return;
    const chain = kernel.verifyLedgerChain();
    sendJSON(res, 200, {
      kernel: kernel.KERNEL.name,
      version: kernel.KERNEL.version,
      symbol: kernel.KERNEL.symbol,
      ledger: chain,
      head: kernel.getChainHead(),
      ledger_file: kernel.INJECT_CONFIG.persistLedger ? '.kernel_ledger/ledger.jsonl' : null,
    });
    return;
  }

  // 内核协议状态总览
  if (req.method === 'GET' && req.url === '/v1/kernel/status') {
    if (!authMiddleware(req, res)) return;
    sendJSON(res, 200, {
      kernel: kernel.KERNEL,
      inject: {
        enabled: kernel.INJECT_CONFIG.enabled,
        default_level: kernel.INJECT_CONFIG.defaultLevel,
        levels: Object.keys(kernel.KERNEL_PROMPTS),
        force_normalize: kernel.INJECT_CONFIG.forceNormalizeOutput,
        idempotency: kernel.INJECT_CONFIG.idempotency,
      },
      ledger: kernel.verifyLedgerChain(),
      cross_verify_levels: Object.keys(crossVerify.VERIFY_LEVELS),
    });
    return;
  }

  // 404
  sendJSON(res, 404, { error: { message: '接口不存在', type: 'not_found' } });
});

// 启动服务
server.listen(config.server.port, config.server.host, () => {
  console.log('========================================');
  console.log('  AIOS Proxy 多模型统一代理服务');
  console.log('========================================');
  console.log(`  监听: http://${config.server.host}:${config.server.port}`);
  console.log(`  健康检查: http://${config.server.host}:${config.server.port}/health`);
  console.log(`  模型列表: http://${config.server.host}:${config.server.port}/v1/models`);
  console.log(`  聊天接口: http://${config.server.host}:${config.server.port}/v1/chat/completions`);
  console.log(`  API密钥: ${config.server.apiKey}`);
  console.log(`  已接入厂商: ${Object.keys(config.providers).join(', ')}`);
  console.log(`  已接入模型: ${Object.keys(config.models).join(', ')}`);
  console.log('========================================');
});

// 优雅退出
process.on('SIGTERM', () => {
  console.log('收到SIGTERM，正在关闭...');
  server.close(() => process.exit(0));
});
process.on('SIGINT', () => {
  console.log('收到SIGINT，正在关闭...');
  server.close(() => process.exit(0));
});
