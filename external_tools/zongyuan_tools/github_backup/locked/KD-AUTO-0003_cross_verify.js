/**
 * 双模型交叉验证机制
 * 基于 ZR-ASSET-0127 cross_verify.yaml 配置
 * 逻辑：关键真值由≥2个模型独立判断，共识才入账，分歧触发第三模型裁决
 */
const config = require('./config');
const PROVIDERS = {
  doubao: require('./providers/doubao'),
  zhipu: require('./providers/zhipu'),
  hunyuan: require('./providers/hunyuan'),
  nvidia: require('./providers/nvidia'),
};

// 默认验证配置（与 cross_verify.yaml 对应）
const VERIFY_LEVELS = {
  L1_routine: {
    models: ['glm-4-flash', 'nvidia-chat-light'],
    on_disagreement: 'direct_pass_with_flag',
  },
  L2_standard: {
    models: ['glm-4', 'nvidia-chat-balanced'],
    on_disagreement: 'third_arbitration',
  },
  L3_critical: {
    models: ['glm-4', 'nvidia-chat-balanced'],
    arbiter: 'nvidia-chat-flagship',
    on_disagreement: 'third_arbitration_then_human',
  },
  L4_high_risk: {
    models: ['glm-4', 'nvidia-chat-balanced'],
    arbiter: 'nvidia-chat-flagship',
    calibrator: 'nvidia-calibration',
    on_disagreement: 'arbitration_then_human',
  },
};

/**
 * 解析统一模型名为厂商配置
 */
function resolveModel(modelName) {
  const modelConfig = config.models[modelName];
  if (!modelConfig) return null;
  return { provider: modelConfig.provider, model: modelConfig.model };
}

/**
 * 调用单个模型
 */
async function callModel(modelName, messages, opts = {}) {
  const resolved = resolveModel(modelName);
  if (!resolved) throw new Error(`未知模型: ${modelName}`);
  const provider = PROVIDERS[resolved.provider];
  const result = await provider.chatCompletion({
    model: resolved.model,
    messages,
    temperature: opts.temperature ?? 0.2,
    max_tokens: opts.max_tokens ?? 512,
  });
  return result.choices?.[0]?.message?.content?.trim() || '';
}

/**
 * 语义一致性判断（简化版：归一化后比较）
 * 生产环境可对接 nvidia-calibration 做向量相似度
 */
function isAgree(a, b, threshold = 0.85) {
  if (!a || !b) return false;
  const na = a.replace(/\s+/g, '').toLowerCase();
  const nb = b.replace(/\s+/g, '').toLowerCase();
  if (na === nb) return true;
  // 简单包含关系判断（长文本场景）
  if (na.length > 20 && (na.includes(nb) || nb.includes(na))) return true;
  return false;
}

/**
 * 执行双模型交叉验证
 * @param {Object} params - { level, messages, temperature, max_tokens }
 * @returns {Object} { consensus, tags, result, model_a, model_b, arbiter, details }
 */
async function crossVerify(params) {
  const { level = 'L2_standard', messages, temperature, max_tokens } = params;
  const levelCfg = VERIFY_LEVELS[level] || VERIFY_LEVELS.L2_standard;
  const [modelA, modelB] = levelCfg.models;

  // 模型A独立判断
  const answerA = await callModel(modelA, messages, { temperature, max_tokens });
  // 模型B独立判断
  const answerB = await callModel(modelB, messages, { temperature, max_tokens });

  const agreed = isAgree(answerA, answerB);
  const result = {
    level,
    model_a: modelA,
    model_b: modelB,
    answer_a: answerA,
    answer_b: answerB,
    agreed,
    tags: [],
    result: answerA, // 默认取模型A
  };

  // 共识判定
  if (agreed) {
    result.tags.push('双模型共识');
    result.consensus = 2;
    result.result = answerA;
    return result;
  }

  // 分歧：按等级处置
  if (levelCfg.on_disagreement === 'direct_pass_with_flag') {
    result.tags.push('降级单模型-低风险分歧');
    result.consensus = 1;
    result.result = answerA;
    return result;
  }

  // 需要第三模型裁决
  if (levelCfg.arbiter) {
    const arbiter = levelCfg.arbiter;
    const arbiterPrompt = [
      { role: 'system', content: '你是真值裁决者。两个模型对同一问题给出不同答案，请判断哪个更准确，或给出最终综合答案。只输出最终答案。' },
      { role: 'user', content: `问题: ${messages[messages.length-1]?.content || ''}\n\n模型A(${modelA})答案: ${answerA}\n\n模型B(${modelB})答案: ${answerB}\n\n请给出最终裁决答案。` },
    ];
    const arbiterAnswer = await callModel(arbiter, arbiterPrompt, { temperature: 0.1, max_tokens: 512 });
    result.arbiter = arbiter;
    result.arbiter_answer = arbiterAnswer;
    result.result = arbiterAnswer;

    // 裁决与任一模型一致 → 三方共识
    if (isAgree(arbiterAnswer, answerA) || isAgree(arbiterAnswer, answerB)) {
      result.tags.push('三方共识');
      result.consensus = 3;
    } else {
      result.tags.push('需人工复核');
      result.consensus = 0;
      result.human_review_required = true;
    }
    return result;
  }

  // 无仲裁模型的分歧
  result.tags.push('需人工复核');
  result.consensus = 0;
  result.human_review_required = true;
  return result;
}

module.exports = { crossVerify, VERIFY_LEVELS };
