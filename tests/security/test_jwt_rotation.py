import os
from uuid import uuid4

import jwt
from value_fabric.shared.identity.jwt import decode_jwt

RSA_PRIVATE = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDGHKuZ9fxqkYI+
IwnncnQf4xTF8s2dhL7Rw8p7YAjM09kGt8dve5Qj/+rJtn6V9pD4P0V0NbR/Jf+f
3Cgy9fM+lcIazMd3v8bDrQqXQXx03lJGbWwT5v8WF0XgrQm9X2KqmN+eCI/4nbVC
fQwWSTNwMBM5Rq4oeb5V/Nx5N0UtNO83mQBu7aVcXahff7sIGgl9TM5h5epPkrEw
xo7u4cgBM0hdR6FHkjNif0a3b5EadQhbbBjiAoj4RDAeWlGMVj5jY4Fhqx3wryuw
6E9b75Y6WrX/m5CWxW7Hm75E9Sx2xgdyIgx3aE4pRHM6FSrG8jTD2kr+rHHQnY1A
TjHhOJXnAgMBAAECggEAWHCxW5QOx6z7VxhJQ+atK2YPJ2QggLx+IaoW7AK+kTHQ
NcgQp9A7OEIhTjbAgAjh4hSllZSyf8pSkNytANyx0P8EiFf4dqPNq14N6y+h2H7Q
4YsF3vavQcvOTicud3lww8P0HWixTeCQLx5D53jM0fVnMW2bfP9N0BhyU0Nsi2eI
1ecx53aEx4n3CCQqSxNVAOgsc7NOB6Qkec6Tqf2Hlv0JJs3h6Y8I5E9i65C6mcx/
WgSmnBhdPA4AO6dQxhlw0R3sVAFiPKY+9fdv6v8wPF28+fY6YQOY4pCx8PiENpkv
5GwS4zqRj4Qq5h4d6YuKv4j6A+2zL7tB1RyvMY54wQKBgQDwZxuCtW4wLfX1cQnZ
szXVhcr4qTmPbNf9j88qGjQJtoAaI4obPUh3LhWDKQ0EmZ8JP4Vp0T0+rGQvl9Rh
HYic+UzDqw8UgM7ns+9l6fA0V2+fKf6Gh/e7e5h3qUTeA1Cj7v4RcF8Z8hho5Us7
xS8b4xzA4g0jWss4oPs4xWjjvwKBgQDRzVv2DdwNaTQ4xPj5vL3y0MdvMIt3X5kO
MHW6c64OQIz4qgJtBKi5mWFsqkNwls6xl6h+ApM1hWn2OTbSVJMNq4Hlmu9I7OTk
6hfJQ6BWIHIaTwCrlQJAYTdqZylS1QbUpA9RL5RANtpY5NnWn43wU16uAZ20E8Pz
YErY0N2pQwKBgQCVVCWjlTQjNIdI09TL0S9jbUfN7nU3aKAKjS9x+2kihtGZLUSg
2l9TeXlT0K0jagLmk7nPe3siigQGNy5jIhXQkR5UvYjEq8QnGhQG1mklWZpcqwS+
4aQ7rA+/NwPxX2/0AlU8mF6LQzjk7r2fv6xV8P3CFNLC6myJ6r5ak8fQIQKBgHo4
G9aPFSqQqIF7PyIR4j7l1pZ7rwXxPIi+6M6Fh4hU+5F2xO9l4CLPuEn0tVwQ1h7p
PjQ+fWrETqKQinb0K4W9K8w+3f71Kv7Yx8G8z90wTGJn4vYQpU1O4tZPxT2A0Fxr
xE5j2iTTfnZOBjNul/wH0dGgd+z+4Y0AuPhNY7GjAoGAGw8r6riX5UahmVn3s9kx
VXj9SpVmA2j7JkAFsMwFoW10w9TL9x2wsRx8lQzfYgU8ynN1DP5fZVW7eQeugX2f
6y14Y6n1oRXhYMByn+G0efxjV4A0yQ6v4lUG8h0G7wDqZL5XH6/YQ9G9hMGCblq+
WmD+2qxhI4YwCnGJ0FekI98=
-----END PRIVATE KEY-----"""
RSA_PUBLIC = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxhyrmfX8apGCPiMJ53J0
H+MUxfLNnYS+0cPKe2AIzNPZBrfHb3uUI//qybZ+lf aQ+D9FdDW0fyX/n9woMvXz
PpXCGszHd7/Gw60Kl0F8dN5SRm1sE+b/FhdF4K0JvV9iqpjfngiP+J21Qn0MFkkz
cDATOUauKHm+VfzceTdFLTTvN5kAbu2lXF2oX3+7CBoJfUzOYeXqT5KxMMaO7uHI
ATNIXUehR5IzYn9Gt2+RGnUIW2wY4gKI+EQwHlpRjFY+Y2OBYasd8K8rsOhPW++W
Olq1/5uQlsVux5u+RPUsdsYHciIMd2hOKURzOhUqxvI0w9pK/qxx0J2NQE4x4TiV
5wIDAQAB
-----END PUBLIC KEY-----""".replace(" ", "")


def _set_hs_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_SECRET", "a" * 64)
    monkeypatch.setenv("JWT_ACTIVE_KID", "k1")
    monkeypatch.setenv("JWT_PREVIOUS_KID", "k0")
    monkeypatch.setenv("JWT_PREVIOUS_SECRET", "b" * 64)
    monkeypatch.setenv("JWT_ISSUER", "value-fabric-internal")
    monkeypatch.setenv("JWT_AUDIENCE", "value-fabric-services")


def test_rotation_accepts_previous_key(monkeypatch):
    _set_hs_env(monkeypatch)
    token = jwt.encode(
        {"tenant_id": str(uuid4()), "iss": "value-fabric-internal", "aud": "value-fabric-services", "exp": 4102444800},
        "b" * 64,
        algorithm="HS256",
        headers={"kid": "k0"},
    )
    assert decode_jwt(token) is not None


def test_invalid_kid_rejected(monkeypatch):
    _set_hs_env(monkeypatch)
    token = jwt.encode(
        {"tenant_id": str(uuid4()), "iss": "value-fabric-internal", "aud": "value-fabric-services", "exp": 4102444800},
        "a" * 64,
        algorithm="HS256",
        headers={"kid": "nope"},
    )
    assert decode_jwt(token) is None


def test_stale_key_rejected(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("JWT_SECRET", "a" * 64)
    monkeypatch.setenv("JWT_ISSUER", "value-fabric-internal")
    monkeypatch.setenv("JWT_AUDIENCE", "value-fabric-services")
    monkeypatch.delenv("JWT_PREVIOUS_KID", raising=False)
    token = jwt.encode(
        {"tenant_id": str(uuid4()), "iss": "value-fabric-internal", "aud": "value-fabric-services", "exp": 4102444800},
        "b" * 64,
        algorithm="HS256",
        headers={"kid": "k0"},
    )
    assert decode_jwt(token) is None
