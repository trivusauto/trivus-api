from dataclasses import dataclass
from src.modules.auth.domain.entities import User


@dataclass
class LoginCommand:
    email: str
    password: str


@dataclass
class AuthResult:
    access_token: str
    user: User
