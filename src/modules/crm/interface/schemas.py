from pydantic import BaseModel


class CreateTemplateRequest(BaseModel):
    name: str
    stages: list[str] = []


class CreateStageRequest(BaseModel):
    funnel_id: str
    name: str
    sort_order: int = 0


class RenameRequest(BaseModel):
    name: str


class CreateLeadRequest(BaseModel):
    store_id: str
    stage_id: str
    funil: str | None = None
    nome: str | None = None
    telefone: str | None = None
    cidade: str | None = None
    modelo: str | None = None
    ano: str | None = None
    assigned_to: str | None = None


class UpdateLeadRequest(BaseModel):
    funil: str | None = None
    nome: str | None = None
    telefone: str | None = None
    cidade: str | None = None
    modelo: str | None = None
    ano: str | None = None
    assigned_to: str | None = None
    vendedor_id: str | None = None
    observacoes: str | None = None
    bairro: str | None = None
    veiculo: str | None = None
    cor: str | None = None
    combustivel: str | None = None
    quilometragem: str | None = None
    transmissao: str | None = None
    lid: str | None = None
    qualificado: bool | None = None
    origem_mkt: str | None = None
    urgencia_venda: str | None = None
    tem_financiamento: bool | None = None


class MoveLeadRequest(BaseModel):
    to_stage_id: str


class AgendamentoRequest(BaseModel):
    data_agendamento: str | None = None
    hora_agendamento: str | None = None


class CompareceuRequest(BaseModel):
    compareceu: bool


class FechamentoRequest(BaseModel):
    receita: str | None = None
    despesa: str | None = None
    rentabilidade: str | None = None


class CoolingRuleIn(BaseModel):
    hours_threshold: int
    card_color: str = "#facc15"
    message: str = "Lead esfriando"
