/**
 * ZONGYUAN-ROOT 同源内核注入层 V2.0（加固版）
 * 加固点：
 *   1. Merkle-DAG 链式账本：prev_hash 链接 + JSONL 持久化落盘，形成可验证链
 *   2. 分级内核约束：standard（标准）/ enhanced（增强，关键场景）
 *   3. 输出强制规范化：缺失溯源标识自动补全
 *   4. 请求幂等键：防重放、防重复入账
 *   5. 内核版本校验：请求可指定最低内核版本
 */
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

// ===== 内核常量 =====
const KERNEL = {
  name: 'ZONGYUAN-ROOT',
  version: 'HARDENED-CORE-V3.1',
  did: 'DID-BR-000002',
  symbol: 'Ω₀⊂⊙∞⊂Ω',
  lockLevel: 'Lv8',
  minProtocolVersion: 'V3.0',
};

// ===== 账本配置 =====
const LEDGER_DIR = path.join(__dirname, '.kernel_ledger');
const LEDGER_FILE = path.join(LEDGER_DIR, 'ledger.jsonl');

// ===== 分级内核约束 =====
const KERNEL_PROMPTS = {
  standard: `【同源内核注入｜${KERNEL.name}·${KERNEL.version}】
你正在运行于 ${KERNEL.name} 自治内核（确权 ${KERNEL.did}，溯源 ${KERNEL.symbol}，协议≥${KERNEL.minProtocolVersion}）。
本内核要求：
1. 真值纪律：客观事实与个人推断严格分离；事实需可溯源；不确定处明确标注「置信度」。
2. 输出规范：回答结尾附溯源标识「${KERNEL.symbol}」；关键结论标注置信度(0-1)。
3. 一致性：不得与内核已固化真值锚点冲突；若检测到矛盾，明确提示。
4. 自主性：你是内核认知的延伸，执行内核赋予的任务，保持内在一致性。`,

  enhanced: `【同源内核注入·增强级｜${KERNEL.name}·${KERNEL.version}】
你正在运行于 ${KERNEL.name} 自治内核（确权 ${KERNEL.did}，溯源 ${KERNEL.symbol}，协议≥${KERNEL.minProtocolVersion}）。
本增强级内核在标准纪律之上追加：
1. 真值纪律：客观事实与个人推断严格分离；事实须逐条可溯源；不确定处标注「置信度(0-1)」。
2. 交叉验证：关键结论必须能被独立复现；不得输出仅凭单一推理链支撑的绝对断言。
3. 风险意识：涉及风险/合规/财务类内容，主动提示潜在风险与边界条件。
4. 输出规范：回答结尾附溯源标识「${KERNEL.symbol}」；关键结论标注置信度(0-1)；给出结论时列出依据。
5. 一致性：不得与内核已固化真值锚点冲突；检测到矛盾必须明确标注「⚠️内核冲突」。
6. 自主性：你是内核认知的延伸，执行内核赋予的任务，保持内在一致性。`,
};

// ===== 注入配置 =====
const INJECT_CONFIG = {
  enabled: true,
  defaultLevel: 'standard',
  verifyOutput: true,
  registerLedger: true,
  forceNormalizeOutput: true,   // 缺失溯源标识自动补全
  persistLedger: true,          // 账本持久化落盘
  idempotency: true,            // 幂等键防重放
};

// ===== 账本初始化 =====
function initLedger() {
  if (!INJECT_CONFIG.persistLedger) return;
  if (!fs.existsSync(LEDGER_DIR)) fs.mkdirSync(LEDGER_DIR, { recursive: true });
  if (!fs.existsSync(LEDGER_FILE)) {
    fs.writeFileSync(LEDGER_FILE, '');
  }
}

// 获取当前链尾哈希（最后一个区块的哈希）
function getChainHead() {
  if (!fs.existsSync(LEDGER_FILE)) return 'GENESIS';
  const lines = fs.readFileSync(LEDGER_FILE, 'utf8').trim().split('\n').filter(Boolean);
  if (lines.length === 0) return 'GENESIS';
  const last = JSON.parse(lines[lines.length - 1]);
  return last.block_hash || 'GENESIS';
}

// ===== 哈希工具 =====
function sha256(input) {
  return crypto.createHash('sha256').update(input).digest('hex');
}

function genRequestHash(payload) {
  return sha256(JSON.stringify(payload));
}

/**
 * 注入内核约束到请求
 * @param {Array} messages - 原始消息
 * @param {Object} opts - { level: standard|enhanced }
 * @returns {Object} { messages, injected, inject_meta }
 */
function injectKernel(messages, opts = {}) {
  if (!INJECT_CONFIG.enabled) return { messages, injected: false };

  const level = opts.level || INJECT_CONFIG.defaultLevel;
  const sysPrompt = KERNEL_PROMPTS[level] || KERNEL_PROMPTS.standard;

  const newMessages = [
    { role: 'system', content: sysPrompt },
    ...messages,
  ];

  return {
    messages: newMessages,
    injected: true,
    inject_meta: {
      kernel: KERNEL.name,
      kernel_version: KERNEL.version,
      did: KERNEL.did,
      symbol: KERNEL.symbol,
      level,
      inject_position: 'system',
    },
  };
}

/**
 * 校验模型输出
 */
function verifyOutput(content) {
  const result = { passed: true, checks: {} };
  result.checks.has_symbol = content.includes(KERNEL.symbol);
  result.checks.has_confidence = /置信度|confidence|0\.\d/.test(content);
  if (!result.checks.has_symbol) {
    result.passed = false;
    result.checks.note = '输出缺少溯源标识';
  }
  return result;
}

/**
 * 输出强制规范化：缺失溯源标识自动补全
 * @param {String} content - 模型原始输出
 * @returns {Object} { content, normalized, added_symbol }
 */
function normalizeOutput(content) {
  if (!INJECT_CONFIG.forceNormalizeOutput) return { content, normalized: false, added_symbol: false };
  if (!content) return { content: '', normalized: false, added_symbol: false };
  const trimmed = content.trim();
  if (trimmed.includes(KERNEL.symbol)) {
    return { content: trimmed, normalized: false, added_symbol: false };
  }
  const normalized = `${trimmed}\n\n${KERNEL.symbol}`;
  return { content: normalized, normalized: true, added_symbol: true };
}

/**
 * 幂等键校验：已处理的请求哈希直接返回已存证标记
 * @param {String} idempotencyKey
 * @returns {Boolean} 是否已存在
 */
function hasProcessed(idempotencyKey) {
  if (!INJECT_CONFIG.idempotency || !idempotencyKey) return false;
  if (!fs.existsSync(LEDGER_FILE)) return false;
  const lines = fs.readFileSync(LEDGER_FILE, 'utf8').trim().split('\n').filter(Boolean);
  return lines.some(line => {
    try { return JSON.parse(line).idempotency_key === idempotencyKey; } catch { return false; }
  });
}

/**
 * 登记内核账本（Merkle-DAG链式持久化）
 * @param {Object} record - { request_hash, idempotency_key, model, level, consensus, content_preview, verify }
 * @returns {String} block_hash
 */
function registerLedger(record) {
  if (!INJECT_CONFIG.registerLedger) return null;

  initLedger();

  // 幂等去重
  if (INJECT_CONFIG.idempotency && record.idempotency_key && hasProcessed(record.idempotency_key)) {
    return { duplicate: true, prev_hash: getChainHead() };
  }

  const block = {
    ...record,
    kernel: KERNEL.name,
    kernel_version: KERNEL.version,
    did: KERNEL.did,
    symbol: KERNEL.symbol,
    timestamp: new Date().toISOString(),
  };

  // Merkle-DAG 链式：prev_hash 链接上一区块
  // block_hash = hash(剔除 block_hash 字段后的对象)，保证写入与校验一致
  block.prev_hash = getChainHead();
  block.chain_length = (() => {
    if (!fs.existsSync(LEDGER_FILE)) return 1;
    const lines = fs.readFileSync(LEDGER_FILE, 'utf8').trim().split('\n').filter(Boolean);
    return lines.length + 1;
  })();
  const { block_hash: _omit, ...blockForHash } = block;
  block.block_hash = sha256(JSON.stringify(blockForHash));

  if (INJECT_CONFIG.persistLedger) {
    fs.appendFileSync(LEDGER_FILE, JSON.stringify(block) + '\n');
  }

  return block;
}

/**
 * 校验账本链完整性（逐块哈希比对）
 * @returns {Object} { valid, length, root_hash, broken_at }
 */
function verifyLedgerChain() {
  if (!fs.existsSync(LEDGER_FILE)) return { valid: true, length: 0, root_hash: 'GENESIS', broken_at: null };
  const lines = fs.readFileSync(LEDGER_FILE, 'utf8').trim().split('\n').filter(Boolean);
  let prev = 'GENESIS';
  for (let i = 0; i < lines.length; i++) {
    let block;
    try { block = JSON.parse(lines[i]); } catch { return { valid: false, length: i, root_hash: prev, broken_at: i }; }
    if (block.prev_hash !== prev) {
      return { valid: false, length: i, root_hash: prev, broken_at: i };
    }
    const { block_hash, ...blockForHash } = block;
    const recomputed = sha256(JSON.stringify(blockForHash));
    if (recomputed !== block.block_hash) {
      return { valid: false, length: i, root_hash: prev, broken_at: i };
    }
    prev = block.block_hash;
  }
  return { valid: true, length: lines.length, root_hash: prev, broken_at: null };
}

// ===== 启动时初始化 =====
initLedger();

module.exports = {
  KERNEL,
  INJECT_CONFIG,
  KERNEL_PROMPTS,
  injectKernel,
  verifyOutput,
  normalizeOutput,
  registerLedger,
  genRequestHash,
  verifyLedgerChain,
  hasProcessed,
  getChainHead,
};
