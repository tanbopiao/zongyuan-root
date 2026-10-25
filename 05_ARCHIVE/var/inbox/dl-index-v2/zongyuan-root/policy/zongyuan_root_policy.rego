# ZONGYUAN-ROOT 三层相变策略 ｜ CONTRACT-OP-V1.0 ｜ DID-BR-000002
# 逻辑态 → 算子态 → 执行态：仅 OPA 放行的算子态契约可流入执行态
package zongyuan_root

default allow = false
default layer_lock = false

# 执行态放行条件：契约版本/DID/签名/op_id 白名单齐备
allow {
  input.contract_version == "CONTRACT-OP-V1.0"
  input.did == "DID-BR-000002"
  input.ontology_signature == "Ω₀⊂⊙∞⊂Ω"
  op_whitelisted(input.operator_list)
}

op_whitelisted(ops) {
  ops[_].op_id == "OP-AXIOM-CHECK-001"
}
op_whitelisted(ops) {
  ops[_].op_id == "SELF_CHECK_AXIOM"
}
op_whitelisted(ops) {
  ops[_].op_id == "OP-DEMO-PROBE-001"
}
op_whitelisted(ops) {
  ops[_].op_id == "OP-DEMO-FAIL-001"
}
op_whitelisted(ops) {
  ops[_].op_id == "OP-WORKER-TICK-001"
}

# 越层拦截：逻辑态直接指令（无契约信封）一律拒绝 → 轻锁档
layer_lock {
  input.kind == "logic_layer_direct"
}
op_whitelisted(ops) {
  ops[_].op_id == "OP-BRAIN-AUDIT-001"
}
