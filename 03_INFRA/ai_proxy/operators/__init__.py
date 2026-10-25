from .text_operators import TextOperators
from .image_operators import ImageOperators
from .video_operators import VideoOperators
from .audio_operators import AudioOperators
from .storage_operators import StorageOperators
from .verification_operators import VerificationOperators
from .adp_rag_operators import ADPRAGOperators
from .local_rag_operators import LocalRAGOperators

class OperatorRegistry:
    def __init__(self, config=None):
        self.config = config or {}
        self.text = TextOperators(self.config)
        self.image = ImageOperators(self.config)
        self.video = VideoOperators(self.config)
        self.audio = AudioOperators(self.config)
        self.storage = StorageOperators(self.config)
        self.verify = VerificationOperators(self.config)
        self.adp_rag = ADPRAGOperators(self.config)
        self.local_rag = LocalRAGOperators(self.config)
        self._groups = {
            "text": self.text, "image": self.image, "video": self.video,
            "audio": self.audio, "storage": self.storage, "verify": self.verify,
            "adp_rag": self.adp_rag, "local_rag": self.local_rag
        }
    def call(self, group, operator, **kwargs):
        g = self._groups.get(group)
        if not g:
            return {"error": "算子组不存在: " + group}
        op = getattr(g, operator, None)
        if not op or not callable(op):
            return {"error": "算子不存在: " + group + "." + operator}
        try:
            return op(**kwargs)
        except Exception as e:
            return {"error": "算子执行失败: " + str(e)}
    def list_all(self):
        result = {}
        for name, group in self._groups.items():
            ops = [m for m in dir(group) if not m.startswith("_") and callable(getattr(group, m))]
            result[name] = ops
        return result

_registry = None
def get_registry(config=None):
    global _registry
    if _registry is None:
        _registry = OperatorRegistry(config)
    return _registry
