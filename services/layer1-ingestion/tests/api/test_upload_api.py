from value_fabric.layer1.api import main


def test_malware_scanner_adapter_contract():
    adapter = main.MalwareScannerAdapter()
    assert hasattr(adapter, 'scan')


def test_upload_route_registered():
    assert any(getattr(r, 'path', '') == '/api/v1/ingestion/uploads' for r in main.router.routes)
