from value_fabric.layer1.api import main


def test_upload_contract_configured():
    route = next(r for r in main.router.routes if getattr(r, 'path', '').endswith('/uploads'))
    assert 'POST' in route.methods
    assert route.response_model is main.FileUploadResponse


def test_upload_response_model_fields():
    fields = set(main.FileUploadResponse.model_fields.keys())
    assert {'job_id','raw_content_id','status','processing_status','reason_code'} <= fields
