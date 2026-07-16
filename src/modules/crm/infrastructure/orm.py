from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.infrastructure.database import Base


class FunnelModel(Base):
    __tablename__ = "crm_funnels"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    store_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    name: Mapped[str] = mapped_column(String)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)
    template_source_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)


class StageModel(Base):
    __tablename__ = "crm_funnel_stages"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    funnel_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    name: Mapped[str] = mapped_column(String)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    template_stage_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)


class CoolingRuleModel(Base):
    __tablename__ = "crm_stage_cooling_rules"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    stage_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    hours_threshold: Mapped[int] = mapped_column(Integer)
    card_color: Mapped[str] = mapped_column(String, default="#facc15")
    message: Mapped[str] = mapped_column(String, default="Lead esfriando")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class StageHistoryModel(Base):
    __tablename__ = "crm_lead_stage_history"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    lead_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    stage_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ActivityModel(Base):
    __tablename__ = "crm_activity_log"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    store_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    actor_user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    action: Mapped[str] = mapped_column(String)
    entity_type: Mapped[str | None] = mapped_column(String, nullable=True)
    entity_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)


class LeadModel(Base):
    __tablename__ = "crm_funnel_leads"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    store_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    stage_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    assigned_to: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    vendedor_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    agendado_por: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    campaign_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    funil: Mapped[str | None] = mapped_column(String, nullable=True)
    qualificado: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    origem_mkt: Mapped[str | None] = mapped_column(String, nullable=True)
    urgencia_venda: Mapped[str | None] = mapped_column(String, nullable=True)
    nome: Mapped[str | None] = mapped_column(String, nullable=True)
    telefone: Mapped[str | None] = mapped_column(String, nullable=True)
    lid: Mapped[str | None] = mapped_column(String, nullable=True)
    bairro: Mapped[str | None] = mapped_column(String, nullable=True)
    cidade: Mapped[str | None] = mapped_column(String, nullable=True)
    modelo: Mapped[str | None] = mapped_column(String, nullable=True)
    veiculo: Mapped[str | None] = mapped_column(String, nullable=True)
    ano: Mapped[str | None] = mapped_column(String, nullable=True)
    cor: Mapped[str | None] = mapped_column(String, nullable=True)
    combustivel: Mapped[str | None] = mapped_column(String, nullable=True)
    quilometragem: Mapped[str | None] = mapped_column(String, nullable=True)
    transmissao: Mapped[str | None] = mapped_column(String, nullable=True)
    valor_tabela_fipe: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    tem_financiamento: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    saldo_quitacao: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    valor_pretendido: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    valor_compra: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    data_comprado: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_agendamento: Mapped[date | None] = mapped_column(Date, nullable=True)
    hora_agendamento: Mapped[str | None] = mapped_column(String, nullable=True)
    data_marcacao_agendamento: Mapped[date | None] = mapped_column(Date, nullable=True)
    compareceu_agendamento: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    data_compareceu: Mapped[date | None] = mapped_column(Date, nullable=True)
    fechou_negocio: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    data_fechou_negocio: Mapped[date | None] = mapped_column(Date, nullable=True)
    receita: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    despesa: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    rentabilidade: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
