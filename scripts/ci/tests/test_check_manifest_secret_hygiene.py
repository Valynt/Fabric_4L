from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.ci.check_manifest_secret_hygiene import find_violations


class ManifestSecretHygieneTests(unittest.TestCase):
    def test_detects_all_forbidden_patterns(self) -> None:
        fixture_dir = Path(__file__).parent / 'fixtures' / 'manifest_secret_hygiene'
        violations = find_violations(sorted(fixture_dir.glob('*.yml')))
        rules = {v.rule for v in violations}

        self.assertIn('VAULT_DEV_ROOT_TOKEN_ID', rules)
        self.assertIn('inline postgres:postgres', rules)
        self.assertIn('inline redis url without auth', rules)
        self.assertIn('forbidden dev auth bypass env vars', rules)

    def test_allows_secret_ref_only_fixture(self) -> None:
        fixture = Path(__file__).parent / 'fixtures' / 'manifest_secret_hygiene' / 'valid-secret-ref.yml'
        self.assertEqual(find_violations([fixture]), [])

    def test_env_example_rejects_reusable_dev_credentials(self) -> None:
        with TemporaryDirectory() as tmpdir:
            fixture = Path(tmpdir) / '.env.example'
            fixture.write_text(
                '\n'.join(
                    [
                        'REDIS_PASSWORD=dev-redis-password',
                        'MINIO_ACCESS_KEY_ID=minioadmin',
                        'MINIO_SECRET_ACCESS_KEY=minioadmin',
                        'S3_ACCESS_KEY_ID=minioadmin',
                        'S3_SECRET_ACCESS_KEY=minioadmin',
                    ]
                ),
                encoding='utf-8',
            )

            rules = {v.rule for v in find_violations([fixture])}

        self.assertIn('reusable Redis password in .env.example', rules)
        self.assertIn('reusable MinIO credentials in .env.example', rules)

    def test_env_example_allows_blank_secret_values(self) -> None:
        with TemporaryDirectory() as tmpdir:
            fixture = Path(tmpdir) / '.env.example'
            fixture.write_text(
                '\n'.join(
                    [
                        'REDIS_PASSWORD=',
                        'MINIO_ACCESS_KEY_ID=',
                        'MINIO_SECRET_ACCESS_KEY=',
                        'S3_ACCESS_KEY_ID=',
                        'S3_SECRET_ACCESS_KEY=',
                    ]
                ),
                encoding='utf-8',
            )

            self.assertEqual(find_violations([fixture]), [])

    def test_dev_compose_defaults_must_stay_in_dev_only_compose(self) -> None:
        with TemporaryDirectory() as tmpdir:
            dev_fixture = Path(tmpdir) / 'docker-compose.dev.yml'
            deployable_fixture = Path(tmpdir) / 'docker-compose.yml'
            contents = '\n'.join(
                [
                    'services:',
                    '  keycloak:',
                    '    environment:',
                    '      KC_BOOTSTRAP_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD:-admin}',
                ]
            )
            dev_fixture.write_text(contents, encoding='utf-8')
            deployable_fixture.write_text(contents, encoding='utf-8')

            self.assertEqual(find_violations([dev_fixture]), [])
            rules = {v.rule for v in find_violations([deployable_fixture])}

        self.assertIn('dev Keycloak bootstrap admin password', rules)

    def test_deployable_dev_mode_service_requires_dev_profile(self) -> None:
        with TemporaryDirectory() as tmpdir:
            fixture = Path(tmpdir) / 'docker-compose.full.yml'
            fixture.write_text(
                '\n'.join(
                    [
                        'services:',
                        '  vault:',
                        '    image: hashicorp/vault:latest',
                        '    command: server -dev -dev-listen-address=0.0.0.0:8200',
                    ]
                ),
                encoding='utf-8',
            )

            rules = {v.rule for v in find_violations([fixture])}

        self.assertIn('dev compose service lacks dev-only profile', rules)

    def test_deployable_dev_mode_service_allows_dev_profile(self) -> None:
        with TemporaryDirectory() as tmpdir:
            fixture = Path(tmpdir) / 'docker-compose.full.yml'
            fixture.write_text(
                '\n'.join(
                    [
                        'services:',
                        '  vault:',
                        '    profiles:',
                        '      - dev  # Only start with --profile dev',
                        '    image: hashicorp/vault:latest',
                        '    command: server -dev -dev-listen-address=0.0.0.0:8200',
                    ]
                ),
                encoding='utf-8',
            )

            self.assertEqual(find_violations([fixture]), [])


if __name__ == '__main__':
    unittest.main()
