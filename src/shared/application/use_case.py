from abc import ABC, abstractmethod
from typing import Generic, TypeVar

Input = TypeVar("Input")
Output = TypeVar("Output")


class UseCase(ABC, Generic[Input, Output]):
    @abstractmethod
    async def execute(self, request: Input) -> Output: ...
