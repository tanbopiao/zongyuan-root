# -*- coding: utf-8 -*-
"""bge-small-zh ONNX Embedding 适配器（CPU，带磁盘缓存）。

适配说明（与原始设计稿的差异，均已实测）：
  · vocab_path 既支持 tokenizers 的 tokenizer.json（推荐），也支持 vocab.txt（WordPiece 兜底）；
  · 输入张量按会话实际 input 名喂入（input_ids / attention_mask / token_type_ids）；
  · mean pooling 按 attention_mask 加权（正确于裸均值）。
"""
import hashlib

import numpy as np
import onnxruntime as ort
import tokenizers
from .base import BaseEmbeddingAdapter


class OnnxBgeAdapter(BaseEmbeddingAdapter):
    def __init__(self, onnx_path: str, vocab_path: str, cache):
        so = ort.SessionOptions()
        so.intra_op_num_threads = int(__import__("os").environ.get("FM_EMB_THREADS", "2"))
        self.sess = ort.InferenceSession(onnx_path, sess_options=so,
                                         providers=["CPUExecutionProvider"])
        self.tokenizer = self._load_tokenizer(vocab_path)
        self.input_names = [i.name for i in self.sess.get_inputs()]
        self.cache = cache
        self.dim = self._out_dim()

    def _out_dim(self):
        """从 ONNX 输出形状推断向量维度（避免硬编码 384/512 导致换模型即崩）。"""
        try:
            d = self.sess.get_outputs()[0].shape[-1]
            return int(d) if isinstance(d, int) and d > 0 else None
        except Exception:
            return None

    @staticmethod
    def _load_tokenizer(path: str):
        if str(path).endswith(".json"):
            return tokenizers.Tokenizer.from_file(path)
        # vocab.txt 兜底：WordPiece 离线构造（无 normalizer/post-processor 精调，够用于检索）
        from tokenizers import Tokenizer, models, normalizers, pre_tokenizers
        vocab = {}
        with open(path, encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                vocab[line.rstrip("\n")] = i
        tok = Tokenizer(models.WordPiece(vocab, unk_token="[UNK]"))
        tok.normalizer = normalizers.NFKC()
        tok.pre_tokenizer = pre_tokenizers.Whitespace()
        return tok

    def encode(self, text: str) -> list:
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if h in self.cache:
            return self.cache[h]
        enc = self.tokenizer.encode(text)
        ids = np.array([enc.ids], dtype=np.int64)
        mask = np.array([getattr(enc, "attention_mask", [1] * len(enc.ids))], dtype=np.int64)
        feed = {}
        for name in self.input_names:
            if name.endswith("input_ids"):
                feed[name] = ids
            elif name.endswith("attention_mask"):
                feed[name] = mask
            elif name.endswith("token_type_ids"):
                feed[name] = np.zeros_like(ids)
        out = self.sess.run(None, feed)[0]          # (1, seq, dim) 或 (1, dim)
        seq_mask = mask[0].astype(np.float32)
        if out.ndim == 3:
            seq = out[0][:len(seq_mask)]             # (seq, dim)
            m = seq_mask[:seq.shape[0]][:, None]
            vec = (seq * m).sum(axis=0) / max(float(m.sum()), 1e-6)
        else:
            vec = out[0]
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec = vec / norm
        vec_list = vec.astype(np.float32).tolist()
        if self.dim is None:
            self.dim = len(vec_list)          # 形状不可解析时以首次实算为准
        self.cache[h] = vec_list
        return vec_list
