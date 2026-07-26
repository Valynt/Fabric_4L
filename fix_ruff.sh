sed -i -e '3d;4d' tests/ci/test_pip_audit_workflow.py
sed -i '4i import subprocess\nimport sys' tests/ci/test_pip_audit_workflow.py
