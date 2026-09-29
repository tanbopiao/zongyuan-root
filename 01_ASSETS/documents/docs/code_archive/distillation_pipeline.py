#!/usr/bin/env python3
"""
ZONGYUAN-ROOT 三维算力蒸馏训练流水线
生成训练配置 + 评估脚本 + 部署方案
注意：训练在本地电脑执行，服务器仅做推理部署
确权: DID-BR-000002 | 溯源: Ω₀⊂⊙∞⊂Ω | MR-053
"""
import json
import os
import sys
from datetime import datetime

BASE = "/opt/ZONGYUAN-ROOT"
DATASET_DIR = os.path.join(BASE, "data/distillation_dataset")
OUTPUT_DIR = os.path.join(BASE, "distillation_output")

def load_dataset():
    """加载MR-052蒸馏数据集"""
    samples = []
    if not os.path.exists(DATASET_DIR):
        print("数据集目录不存在: %s" % DATASET_DIR)
        return samples
    for f in sorted(os.listdir(DATASET_DIR)):
        if f.endswith('.jsonl'):
            with open(os.path.join(DATASET_DIR, f)) as fp:
                for line in fp:
                    line = line.strip()
                    if line:
                        samples.append(json.loads(line))
    return samples

def check_readiness(samples):
    """检查蒸馏就绪状态"""
    print("=" * 50)
    print("三维算力蒸馏就绪检查")
    print("=" * 50)
    print("训练样本数: %d条" % len(samples))
    
    # 按等级统计
    levels = {}
    for s in samples:
        lvl = s.get("metadata", {}).get("level", "unknown")
        levels[lvl] = levels.get(lvl, 0) + 1
    print("等级分布: %s" % json.dumps(levels, ensure_ascii=False))
    
    # 教师模型统计
    teachers = {}
    for s in samples:
        t = s.get("metadata", {}).get("teacher_model", "unknown")
        teachers[t] = teachers.get(t, 0) + 1
    print("教师模型: %s" % json.dumps(teachers, ensure_ascii=False))
    
    # 就绪判断
    ready = len(samples) >= 300
    print("\n最低门槛: 300条")
    print("当前状态: %s" % ("✅ 已就绪，可以开始训练" if ready else "⏳ 未就绪，还需%d条" % (300 - len(samples))))
    print("预计达标: 约%d天后" % max(1, (300 - len(samples)) // 20 + 1))
    return ready

def generate_training_config(samples):
    """生成LoRA训练配置（在本地电脑执行）"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    config = {
        "task": "ZONGYUAN-ROOT_ops_analysis_distillation",
        "base_model": "qwen2.5-0.5b-instruct",
        "method": "LoRA",
        "lora_r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.05,
        "quantization": "4bit",
        "dataset_size": len(samples),
        "train_test_split": 0.9,
        "num_epochs": 3,
        "batch_size": 4,
        "learning_rate": 1e-4,
        "max_seq_length": 512,
        "teacher_model": list(teachers.keys())[0] if samples else "zhipu",
        "output_dir": "./output/zongyuan_distilled_v1",
        "evaluation": {
            "metrics": ["accuracy", "ppl", "latency", "memory"],
            "pass_criteria": {
                "accuracy": ">=85% of teacher",
                "latency": "<=2s",
                "memory": "<=1.5GB"
            }
        }
    }
    
    config_path = os.path.join(OUTPUT_DIR, "training_config.json")
    with open(config_path, 'w') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    # 生成训练命令
    train_cmd = """# 在本地电脑执行（需要GPU或足够内存）
pip install peft transformers accelerate datasets bitsandbytes

python3 train_lora.py \\
  --base_model qwen2.5-0.5b-instruct \\
  --dataset distillation_dataset/ \\
  --lora_r 16 --lora_alpha 32 \\
  --epochs 3 --batch_size 4 \\
  --learning_rate 1e-4 \\
  --output ./output/zongyuan_distilled_v1

# 训练完成后评估
python3 evaluate.py --model ./output/zongyuan_distilled_v1 --test_set test.json

# 评估通过后，转换为GGUF并推送到服务器
python3 convert_to_gguf.py --model ./output/zongyuan_distilled_v1 --out qwen2.5-0.5b-zongyuan-distilled-q4.gguf
scp qwen2.5-0.5b-zongyuan-distilled-q4.gguf zongyuan-cloud:/opt/ZONGYUAN-ROOT/models/
"""
    
    cmd_path = os.path.join(OUTPUT_DIR, "train_commands.sh")
    with open(cmd_path, 'w') as f:
        f.write(train_cmd)
    
    print("\n训练配置已生成: %s" % config_path)
    print("训练命令已生成: %s" % cmd_path)
    return config

def generate_evaluation_script():
    """生成评估脚本"""
    eval_script = '''#!/usr/bin/env python3
"""蒸馏模型评估脚本 - 对比教师模型和学生模型"""
import json
import time
import urllib.request

TEST_CASES = [
    {"input": "内存85%，磁盘60%，负载2.5，失败服务2个", "expected_level": "警告"},
    {"input": "内存45%，磁盘30%，负载0.5，失败服务0个", "expected_level": "健康"},
    {"input": "内存92%，磁盘85%，负载5.0，失败服务5个", "expected_level": "危险"},
]

def call_model(api_url, model_name, prompt):
    payload = {"model": model_name, "messages": [{"role": "user", "content": prompt}], "max_tokens": 200}
    start = time.time()
    req = urllib.request.Request(api_url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        result = json.loads(r.read())
    latency = time.time() - start
    return result["choices"][0]["message"]["content"], latency

def main():
    print("蒸馏模型评估")
    print("=" * 40)
    student_url = "http://127.0.0.1:8081/v1/chat/completions"
    teacher_url = "http://127.0.0.1:8021/v1/chat/completions"
    
    results = []
    for i, case in enumerate(TEST_CASES):
        print("\\n测试用例 %d: %s" % (i+1, case["input"][:40]))
        s_resp, s_lat = call_model(student_url, "qwen2.5-0.5b", "分析服务器状态：" + case["input"])
        t_resp, t_lat = call_model(teacher_url, "zhipu", "分析服务器状态：" + case["input"])
        print("  学生模型(%.1fs): %s" % (s_lat, s_resp[:60]))
        print("  教师模型(%.1fs): %s" % (t_lat, t_resp[:60]))
        results.append({"case": i, "student_latency": s_lat, "teacher_latency": t_lat, "speedup": t_lat/s_lat if s_lat > 0 else 0})
    
    print("\\n" + "=" * 40)
    print("评估汇总:")
    avg_speedup = sum(r["speedup"] for r in results) / len(results)
    print("  平均加速比: %.1fx" % avg_speedup)
    print("  学生模型平均延迟: %.2fs" % (sum(r["student_latency"] for r in results)/len(results)))
    print("  教师模型平均延迟: %.2fs" % (sum(r["teacher_latency"] for r in results)/len(results)))

if __name__ == "__main__":
    main()
'''
    eval_path = os.path.join(OUTPUT_DIR, "evaluate_distilled_model.py")
    with open(eval_path, 'w') as f:
        f.write(eval_script)
    print("评估脚本已生成: %s" % eval_path)

if __name__ == '__main__':
    samples = load_dataset()
    ready = check_readiness(samples)
    generate_training_config(samples)
    generate_evaluation_script()
    print("\n" + "=" * 50)
    print("三维算力蒸馏流水线就绪")
    print("MR-053 | DID-BR-000002 | Ω₀⊂⊙∞⊂Ω")
