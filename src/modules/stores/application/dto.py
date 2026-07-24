from dataclasses import dataclass, field


@dataclass
class ManagerInput:
    """Gerente criado junto com a loja (modelo novo: a loja é o centro)."""
    email: str
    password: str
    name: str


@dataclass
class CreateStoreInput:
    nome_fantasia: str
    fields: dict[str, object] = field(default_factory=dict)
    managers: list[ManagerInput] = field(default_factory=list)
