from value_fabric.layer1.api import main


def test_upload_size_limit_is_enforced():
    assert main.MAX_UPLOAD_FILE_SIZE_BYTES <= 10 * 1024 * 1024


def test_upload_approved_mime_types_are_allowlist_only():
    assert 'application/pdf' in main.APPROVED_UPLOAD_MIME_TYPES
    assert 'application/x-msdownload' not in main.APPROVED_UPLOAD_MIME_TYPES
