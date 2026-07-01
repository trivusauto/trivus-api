from dataclasses import dataclass


@dataclass
class Store:
    id: str
    nome_fantasia: str
    razao_social: str | None = None
    cnpj: str | None = None
    crm_enabled: bool = False
    zapi_webhook_enabled: bool = False
    webhook_token: str | None = None
    active: bool = True

    def display_name(self) -> str:
        return self.nome_fantasia or self.razao_social or "Loja"
