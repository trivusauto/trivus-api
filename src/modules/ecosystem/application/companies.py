from src.modules.ecosystem.infrastructure.repositories import CompanyRepository


class ListCompaniesUseCase:
    def __init__(self, companies: CompanyRepository) -> None:
        self._companies = companies

    async def execute(self) -> list[dict[str, object]]:
        return await self._companies.list_all()


class CreateCompanyUseCase:
    def __init__(self, companies: CompanyRepository) -> None:
        self._companies = companies

    async def execute(self, data: dict[str, object]) -> dict[str, object]:
        return await self._companies.create(data)


class UpdateCompanyUseCase:
    def __init__(self, companies: CompanyRepository) -> None:
        self._companies = companies

    async def execute(self, company_id: str, data: dict[str, object]) -> dict[str, object]:
        return await self._companies.update(company_id, data)
