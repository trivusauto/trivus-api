from dataclasses import dataclass, field


@dataclass
class CreateStoreInput:
    nome_fantasia: str
    fields: dict[str, object] = field(default_factory=dict)
