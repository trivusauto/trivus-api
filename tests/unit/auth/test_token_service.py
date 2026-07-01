from src.modules.auth.infrastructure.token_service import JwtTokenService

svc = JwtTokenService(secret="test-secret", expires_minutes=60)


def test_issue_and_verify() -> None:
    token = svc.issue({"sub": "u1", "role": "admin"})
    claims = svc.verify(token)
    assert claims["sub"] == "u1"
    assert claims["role"] == "admin"
