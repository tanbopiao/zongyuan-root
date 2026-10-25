"""Schema 强约束 + 值域校验 —— 方案 §二.2

每个 EID 挂载业务 Schema: 字段/类型/单位/合法值域/枚举白名单。
Ω-Refer 仲裁层复用这套 Schema 做参数校验, 越界直接熔断(param_invalid)。
示例: 产量不能为负数; 工单状态只允许【待投产/生产中/完工/作废】。
"""
from __future__ import annotations

from dataclasses import dataclass, field


class SchemaError(ValueError):
    """值域/类型/枚举越界 —— 由 gateway 转译为 FuseMask=[param_invalid]。"""

    def __init__(self, msg: str, field_name: str = ""):
        super().__init__(msg)
        self.field_name = field_name


@dataclass
class FieldDef:
    name: str
    type: str = "string"          # string | number | int | bool | datetime
    required: bool = True
    unit: str = ""                # 业务单位(如 kg / 件), 仅元数据
    min: float | None = None      # 数值下界(产量不能为负 → min=0)
    max: float | None = None
    enum: list | None = None      # 枚举白名单(工单状态四态)


@dataclass
class EntitySchema:
    entity_type: str
    fields: dict[str, FieldDef] = field(default_factory=dict)

    def add(self, fd: FieldDef) -> "EntitySchema":
        self.fields[fd.name] = fd
        return self

    # ---- 校验入口(方案 Step3.3: 录入字段类型/值域/枚举白名单) ----
    def validate(self, record: dict) -> dict:
        """校验并返回规范化记录; 越界抛 SchemaError(→param_invalid 熔断)。"""
        out: dict = {}
        for fname, fd in self.fields.items():
            if fname not in record:
                if fd.required:
                    raise SchemaError(f"缺失必填字段: {fname}", fname)
                continue
            v = record[fname]
            if v is None:
                if fd.required:
                    raise SchemaError(f"字段空值(空值阻断): {fname}", fname)
                continue
            v = self._check_type(fname, fd, v)
            if fd.enum is not None and v not in fd.enum:
                raise SchemaError(
                    f"枚举越界: {fname}={v!r} 不在白名单 {fd.enum}", fname)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                if fd.min is not None and v < fd.min:
                    raise SchemaError(f"值域越界: {fname}={v} < {fd.min}", fname)
                if fd.max is not None and v > fd.max:
                    raise SchemaError(f"值域越界: {fname}={v} > {fd.max}", fname)
            out[fname] = v
        return out

    def _check_type(self, fname: str, fd: FieldDef, v):
        t = fd.type
        if t in ("number", "int", "float"):
            try:
                iv = float(v)
            except (TypeError, ValueError):
                raise SchemaError(f"类型不匹配: {fname} 需数值, 得到 {v!r}", fname)
            if t == "int" and not float(iv).is_integer():
                raise SchemaError(f"类型不匹配: {fname} 需整数, 得到 {v!r}", fname)
            return int(iv) if t == "int" else iv
        if t == "bool":
            if not isinstance(v, bool):
                raise SchemaError(f"类型不匹配: {fname} 需布尔, 得到 {v!r}", fname)
            return v
        if t == "string":
            if not isinstance(v, str):
                raise SchemaError(f"类型不匹配: {fname} 需字符串, 得到 {v!r}", fname)
            return v
        return v
