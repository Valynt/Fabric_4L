import sys

def modify_auth():
    filepath = "sdk/python/src/valuefabric/cli/auth.py"
    with open(filepath, "r") as f:
        content = f.read()

    new_imports = """
import http.server
import time
from typing import Any
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse
"""
    content = content.replace("import typing\nimport webbrowser", "import webbrowser")
    content = content.replace("def log_message(self, format: str, *args: typing.Any) -> None:", "def log_message(self, format: str, *args: Any) -> None:")
    content = content.replace("from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse", new_imports)

    with open(filepath, "w") as f:
        f.write(content)

modify_auth()
