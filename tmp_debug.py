import socket
from unittest.mock import patch

with patch.object(socket, 'getaddrinfo', return_value=[(None, None, None, None, ('127.0.0.1', 0))]):
    from layer1_ingestion.compliance.url_safety import validate_url_safety, URLSafetyError
    try:
        validate_url_safety('http://127.0.0.1:8001/')
        print('NO EXCEPTION - validate_url_safety did not raise!')
    except URLSafetyError as e:
        print(f'URLSafetyError raised: {e.reason_code}')
    except Exception as e:
        print(f'Other exception: {type(e).__name__}: {e}')
