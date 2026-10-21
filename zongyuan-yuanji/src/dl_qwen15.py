from modelscope import snapshot_download
import sys
p = snapshot_download("Qwen/Qwen2.5-1.5B-Instruct", local_dir="/root/zongyuan-yuanji/weights/yuanjihengyi_full_v1")
print("DONE:", p)
