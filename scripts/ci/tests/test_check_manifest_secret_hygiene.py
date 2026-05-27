from __future__ import annotations

from pathlib import Path
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


if __name__ == '__main__':
    unittest.main()
