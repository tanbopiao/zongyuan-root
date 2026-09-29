"""
资产校验模块
"""
import hashlib
import zipfile
import json
from pathlib import Path
from dataclasses import dataclass


@dataclass
class VerifyResult:
    """校验结果"""
    sha256: str
    size: int
    valid: bool
    error: str = ""

    def __repr__(self):
        status = "✓ 通过" if self.valid else "✗ 失败"
        return f"<VerifyResult sha256={self.sha256[:16]}... valid={status}>"


@dataclass
class Watermark:
    """溯源水印"""
    order_id: str = ""
    user_did: str = ""
    timestamp: int = 0
    asset_name: str = ""

    def __repr__(self):
        return f"<Watermark order_id={self.order_id} user={self.user_did}>"


class AssetVerifier:
    """
    资产校验器

    用法:
        verifier = AssetVerifier()
        result = verifier.verify_file("asset.zip")
        watermark = verifier.read_watermark("asset.zip")
    """

    @staticmethod
    def compute_sha256(filepath: str) -> str:
        """计算文件SHA256"""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def verify_file(self, filepath: str, expected_sha256: str = None) -> VerifyResult:
        """校验文件完整性"""
        path = Path(filepath)
        if not path.exists():
            return VerifyResult(sha256="", size=0, valid=False, error="文件不存在")

        sha256 = self.compute_sha256(filepath)
        size = path.stat().st_size

        if expected_sha256:
            valid = (sha256.lower() == expected_sha256.lower())
            error = "" if valid else f"哈希不匹配: 期望 {expected_sha256[:16]}..., 实际 {sha256[:16]}..."
        else:
            valid = True
            error = ""

        return VerifyResult(sha256=sha256, size=size, valid=valid, error=error)

    @staticmethod
    def read_watermark(filepath: str) -> Watermark:
        """读取资产包中的溯源水印"""
        path = Path(filepath)

        # zip包内查找asset_watermark.json
        if path.suffix == ".zip":
            try:
                with zipfile.ZipFile(filepath, "r") as zf:
                    if "asset_watermark.json" in zf.namelist():
                        with zf.open("asset_watermark.json") as f:
                            data = json.loads(f.read().decode("utf-8"))
                            return Watermark(
                                order_id=data.get("order_id", ""),
                                user_did=data.get("user_did", ""),
                                timestamp=data.get("timestamp", 0),
                                asset_name=data.get("asset_name", "")
                            )
            except Exception:
                pass

        # 同目录查找水印文件
        wm_path = path.parent / "asset_watermark.json"
        if wm_path.exists():
            with open(wm_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return Watermark(
                    order_id=data.get("order_id", ""),
                    user_did=data.get("user_did", ""),
                    timestamp=data.get("timestamp", 0),
                    asset_name=data.get("asset_name", "")
                )

        return Watermark()

    @staticmethod
    def create_watermark(output_path: str, order_id: str, user_did: str, asset_name: str = "") -> str:
        """创建溯源水印文件"""
        wm = {
            "order_id": order_id,
            "user_did": user_did,
            "timestamp": int(__import__("time").time()),
            "asset_name": asset_name
        }
        wm_path = Path(output_path) / "asset_watermark.json"
        with open(wm_path, "w", encoding="utf-8") as f:
            json.dump(wm, f, ensure_ascii=False, indent=2)
        return str(wm_path)
