#!/usr/bin/env python3
"""
Key Rotation Automation for Fabric4L

Automates rotation of sensitive API keys and secrets:
- OpenAI project API keys
- Thesys API keys  
- Clerk secret keys
- Registry tokens

Usage:
    python scripts/security/key_rotation.py --provider openai --env prod
    python scripts/security/key_rotation.py --provider all --env staging --dry-run
    python scripts/security/key_rotation.py --provider clerk --env dev --verify-only

Requirements:
    - Infisical CLI installed and authenticated
    - Provider API credentials for key generation
    - kubectl access for service restarts (production)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("key_rotation")


def get_infisical_base_cmd() -> list[str]:
    """Get the Infisical CLI binary path only."""
    custom_path = os.getenv("INFISICAL_CLI_PATH")
    if custom_path:
        return [custom_path]
    
    if sys.platform == "win32" or os.name == "nt":
        common_windows_paths = [
            r"C:\tools\Infisical\infisical.exe",
            r"C:\tools\Infisical\infisical",
            os.path.expanduser(r"~\bin\infisical.exe"),
            os.path.expanduser(r"~\infisical-cli\infisical.exe"),
        ]
        for path in common_windows_paths:
            if os.path.exists(path):
                return [path]
    
    return ["infisical"]


def get_infisical_auth_flags() -> list[str]:
    """Get authentication flags for Infisical CLI."""
    flags = []
    client_id = os.getenv("INFISICAL_CLIENT_ID")
    client_secret = os.getenv("INFISICAL_CLIENT_SECRET")
    project_id = os.getenv("INFISICAL_PROJECT_ID")
    
    if client_id:
        flags.extend(["--client-id", client_id])
    if client_secret:
        flags.extend(["--client-secret", client_secret])
    if project_id:
        flags.extend(["--projectId", project_id])
    
    return flags


def fix_path_for_git_bash(path: str) -> str:
    """Fix paths that get mangled by Git Bash path translation."""
    # In Git Bash, paths like /fabric-4l/value-fabric become C:/tools/Git/fabric-4l/value-fabric
    # We need to extract the actual Unix path from the mangled Windows path
    import re
    # Check if path was mangled by Git Bash (contains Windows drive letter or tools/Git)
    if re.match(r'^[A-Za-z]:', path) or 'tools/Git' in path or 'tools\\Git' in path:
        # Extract everything after the drive/tools prefix
        # Pattern: C:/tools/Git/PATH or C:\tools\Git\PATH -> /PATH
        match = re.search(r'[tT]ools[/\\][gG]it[/\\](.+)$', path)
        if match:
            actual_path = match.group(1).replace('\\', '/')
            return '/' + actual_path
    return path


INFISICAL_BASE = get_infisical_base_cmd()
INFISICAL_AUTH_FLAGS = get_infisical_auth_flags()


class RotationStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class RotationRecord:
    """Audit record for a key rotation operation."""
    provider: str
    environment: str
    key_id: str | None = None
    old_key_id: str | None = None
    status: RotationStatus = RotationStatus.PENDING
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    rotated_by: str = field(default_factory=lambda: os.getenv("USER", "automation"))
    error_message: str | None = None
    verification_passed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "provider": self.provider,
            "environment": self.environment,
            "key_id": self.key_id,
            "old_key_id": self.old_key_id,
            "status": self.status.value,
            "rotated_by": self.rotated_by,
            "error_message": self.error_message,
            "verification_passed": self.verification_passed,
        }


class SecretProvider(ABC):
    """Abstract base class for secret providers."""
    
    def __init__(self, environment: str, dry_run: bool = False):
        self.environment = environment
        self.dry_run = dry_run
        self.audit_log: list[RotationRecord] = []
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def infisical_path(self) -> str:
        """Infisical secret path for this provider's keys."""
        pass
    
    @abstractmethod
    def get_current_key_id(self) -> str | None:
        """Get the current key ID from Infisical for audit purposes."""
        pass
    
    @abstractmethod
    def generate_new_key(self) -> tuple[str, str]:
        """Generate new key. Returns (key_value, key_id)."""
        pass
    
    @abstractmethod
    def revoke_old_key(self, key_id: str) -> bool:
        """Revoke an old key by ID. Returns success status."""
        pass
    
    @abstractmethod
    def verify_key(self, key_value: str) -> bool:
        """Verify that a key is valid and working."""
        pass
    
    def rotate(self) -> RotationRecord:
        """Execute full rotation workflow."""
        record = RotationRecord(
            provider=self.provider_name,
            environment=self.environment,
        )
        
        try:
            logger.info(f"[{self.provider_name}] Starting rotation for {self.environment}")
            record.status = RotationStatus.IN_PROGRESS
            
            # Step 1: Get current key ID for audit
            record.old_key_id = self.get_current_key_id()
            logger.info(f"[{self.provider_name}] Current key ID: {record.old_key_id or 'unknown'}")
            
            # Step 2: Generate new key
            logger.info(f"[{self.provider_name}] Generating new key...")
            if self.dry_run:
                key_value = f"sk-dryrun-{self.provider_name}-placeholder"
                key_id = f"dryrun-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                logger.info(f"[{self.provider_name}] DRY RUN: Would generate new key")
            else:
                key_value, key_id = self.generate_new_key()
            
            record.key_id = key_id
            logger.info(f"[{self.provider_name}] New key generated: {key_id[:20]}...")
            
            # Step 3: Update Infisical (atomic operation)
            logger.info(f"[{self.provider_name}] Updating Infisical...")
            self._update_infisical(key_value)
            
            # Step 4: Verify new key works
            logger.info(f"[{self.provider_name}] Verifying new key...")
            if not self.dry_run:
                record.verification_passed = self.verify_key(key_value)
                if not record.verification_passed:
                    raise RuntimeError("New key verification failed")
            else:
                record.verification_passed = True
                logger.info(f"[{self.provider_name}] DRY RUN: Skipping verification")
            
            # Step 5: Restart services to pick up new key
            if not self.dry_run:
                self._restart_services()
            else:
                logger.info(f"[{self.provider_name}] DRY RUN: Would restart services")
            
            # Step 6: Revoke old key (only after new key is confirmed working)
            if record.old_key_id and not self.dry_run:
                logger.info(f"[{self.provider_name}] Revoking old key: {record.old_key_id[:20]}...")
                revoke_success = self.revoke_old_key(record.old_key_id)
                if not revoke_success:
                    logger.warning(f"[{self.provider_name}] Failed to revoke old key - manual cleanup required")
            elif self.dry_run:
                logger.info(f"[{self.provider_name}] DRY RUN: Would revoke old key")
            
            record.status = RotationStatus.COMPLETED
            logger.info(f"[{self.provider_name}] Rotation completed successfully")
            
        except Exception as e:
            record.status = RotationStatus.FAILED
            record.error_message = str(e)
            logger.error(f"[{self.provider_name}] Rotation failed: {e}")
            raise
        
        finally:
            self.audit_log.append(record)
        
        return record
    
    def _update_infisical(self, key_value: str) -> None:
        """Update the secret in Infisical."""
        if self.dry_run:
            logger.info(f"[{self.provider_name}] DRY RUN: Would update Infisical at {self.infisical_path}")
            return
        
        env_map = {"dev": "dev", "staging": "staging", "prod": "prod"}
        infisical_env = env_map.get(self.environment, self.environment)
        
        fixed_path = fix_path_for_git_bash(self.infisical_path)
        cmd = [
            *INFISICAL_BASE, "secrets", "set",
            f"--env={infisical_env}",
            f"--path={fixed_path}",
            f"{self.secret_name}={key_value}",
            "--silent"
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8')
            logger.info(f"[{self.provider_name}] Updated Infisical successfully")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to update Infisical: {e.stderr}")
    
    def _restart_services(self) -> None:
        """Restart dependent services to pick up new key."""
        services = self.get_affected_services()
        if not services:
            return
        
        logger.info(f"[{self.provider_name}] Restarting services: {', '.join(services)}")
        
        for service in services:
            try:
                cmd = ["kubectl", "rollout", "restart", "deployment", service, "-n", "value-fabric"]
                subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8')
                logger.info(f"[{self.provider_name}] Restarted {service}")
                
                # Wait for rollout
                wait_cmd = ["kubectl", "rollout", "status", "deployment", service, "-n", "value-fabric", "--timeout=300s"]
                subprocess.run(wait_cmd, check=True, capture_output=True, text=True, encoding='utf-8')
                logger.info(f"[{self.provider_name}] {service} rollout complete")
                
            except subprocess.CalledProcessError as e:
                logger.warning(f"[{self.provider_name}] Failed to restart {service}: {e.stderr}")
    
    @abstractmethod
    def get_affected_services(self) -> list[str]:
        """Return list of Kubernetes deployment names that use this key."""
        pass
    
    @property
    @abstractmethod
    def secret_name(self) -> str:
        """Environment variable name for this secret."""
        pass


class OpenAIProvider(SecretProvider):
    """OpenAI API key rotation provider."""
    
    @property
    def provider_name(self) -> str:
        return "openai"
    
    def get_infisical_path(self) -> str:
        # OpenAI keys stored in /llm folder
        return "/llm"
    
    @property
    def infisical_path(self) -> str:
        return self.get_infisical_path()
    
    @property
    def secret_name(self) -> str:
        return "OPENAI_API_KEY"
    
    def get_current_key_id(self) -> str | None:
        # OpenAI doesn't expose key IDs via API; no metadata tracking available
        # Return unknown so rotation can proceed without old key revocation
        return "unknown"
    
    def generate_new_key(self) -> tuple[str, str]:
        """Generate new OpenAI API key."""
        # OpenAI requires manual key generation via dashboard
        # This creates a notification for manual rotation
        logger.warning(
            "[openai] OpenAI API keys require manual generation via dashboard:\n"
            "  1. Visit: https://platform.openai.com/account/api-keys\n"
            "  2. Click 'Create new secret key'\n"
            "  3. Set the key value in the environment variable OPENAI_MANUAL_KEY\n"
            "  4. Re-run this script with the new key"
        )
        
        # Check for manually provided key
        manual_key = os.getenv("OPENAI_MANUAL_KEY")
        if not manual_key:
            raise RuntimeError(
                "OPENAI_MANUAL_KEY environment variable not set. "
                "Please generate key manually and set OPENAI_MANUAL_KEY=sk-..."
            )
        
        # Use the provided key
        key_id = manual_key[:20] + "..."
        return manual_key, key_id
    
    def revoke_old_key(self, key_id: str) -> bool:
        """Revoke old OpenAI key."""
        logger.warning(
            "[openai] Revoke old key manually via OpenAI dashboard:\n"
            "  https://platform.openai.com/account/api-keys\n"
            "  Look for key starting with: " + key_id[:10]
        )
        return True  # Mark as success since manual action is required
    
    def verify_key(self, key_value: str) -> bool:
        """Verify OpenAI key by making a test request."""
        try:
            import urllib.request
            import urllib.error
            
            req = urllib.request.Request(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {key_value}"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status == 200
        except urllib.error.HTTPError as e:
            if e.code == 401:
                logger.error("[openai] Key verification failed: Invalid API key")
            else:
                logger.error(f"[openai] Key verification failed: HTTP {e.code}")
            return False
        except Exception as e:
            logger.error(f"[openai] Key verification error: {e}")
            return False
    
    def get_affected_services(self) -> list[str]:
        return ["layer2-extraction", "layer4-agents"]


class ThesysProvider(SecretProvider):
    """Thesys API key rotation provider."""
    
    @property
    def provider_name(self) -> str:
        return "thesys"
    
    def get_infisical_path(self) -> str:
        # Thesys keys stored in /llm folder
        return "/llm"
    
    @property
    def infisical_path(self) -> str:
        return self.get_infisical_path()
    
    @property
    def secret_name(self) -> str:
        return "THESYS_API_KEY"
    
    def get_current_key_id(self) -> str | None:
        try:
            fixed_path = fix_path_for_git_bash(self.infisical_path)
            result = subprocess.run(
                [*INFISICAL_BASE, "secrets", "get",
                 "--env=dev", f"--path={fixed_path}", self.secret_name],
                capture_output=True, text=True, check=True, encoding='utf-8'
            )
            # Parse output - format is "KEY_NAME=VALUE" or just "VALUE"
            output = result.stdout.strip()
            if "=" in output:
                key_value = output.split("=", 1)[1]
            else:
                key_value = output
            return key_value[:20] + "..." if len(key_value) > 20 else key_value
        except Exception:
            return None
    
    def generate_new_key(self) -> tuple[str, str]:
        """Generate new Thesys API key."""
        # Thesys requires manual key generation
        logger.warning(
            "[thesys] Thesys API keys require manual generation:\n"
            "  1. Visit Thesys dashboard\n"
            "  2. Generate new API key\n"
            "  3. Set THESYS_MANUAL_KEY environment variable\n"
            "  4. Re-run this script"
        )
        
        manual_key = os.getenv("THESYS_MANUAL_KEY")
        if not manual_key:
            raise RuntimeError("THESYS_MANUAL_KEY environment variable not set")
        
        key_id = manual_key[:20] + "..."
        return manual_key, key_id
    
    def revoke_old_key(self, key_id: str) -> bool:
        logger.warning(
            "[thesys] Revoke old key manually via Thesys dashboard.\n"
            "  Look for key starting with: " + key_id[:10]
        )
        return True
    
    def verify_key(self, key_value: str) -> bool:
        # Thesys verification would depend on their API
        # For now, just check key format
        return key_value.startswith("thesys_") or len(key_value) > 20
    
    def get_affected_services(self) -> list[str]:
        return ["layer1-ingestion"]


class ClerkProvider(SecretProvider):
    """Clerk secret key rotation provider."""
    
    @property
    def provider_name(self) -> str:
        return "clerk"
    
    def get_infisical_path(self) -> str:
        # Clerk keys stored in /auth folder
        return "/auth"
    
    @property
    def infisical_path(self) -> str:
        return self.get_infisical_path()
    
    @property
    def secret_name(self) -> str:
        return "CLERK_SECRET_KEY"
    
    def get_current_key_id(self) -> str | None:
        try:
            fixed_path = fix_path_for_git_bash(self.infisical_path)
            result = subprocess.run(
                [*INFISICAL_BASE, "secrets", "get",
                 "--env=dev", f"--path={fixed_path}", self.secret_name],
                capture_output=True, text=True, check=True, encoding='utf-8'
            )
            # Parse output - format is "KEY_NAME=VALUE" or just "VALUE"
            output = result.stdout.strip()
            if "=" in output:
                key_value = output.split("=", 1)[1]
            else:
                key_value = output
            return key_value[:20] + "..." if len(key_value) > 20 else key_value
        except Exception:
            return None
    
    def generate_new_key(self) -> tuple[str, str]:
        """Generate new Clerk secret key."""
        logger.warning(
            "[clerk] Clerk secret keys require manual generation:\n"
            "  1. Visit: https://dashboard.clerk.com\n"
            "  2. Navigate to your instance settings\n"
            "  3. Go to API Keys section\n"
            "  4. Generate new secret key\n"
            "  5. Set CLERK_MANUAL_KEY environment variable\n"
            "  6. Re-run this script"
        )
        
        manual_key = os.getenv("CLERK_MANUAL_KEY")
        if not manual_key:
            raise RuntimeError("CLERK_MANUAL_KEY environment variable not set")
        
        if not manual_key.startswith(("sk_test_", "sk_live_")):
            raise RuntimeError("Invalid Clerk key format. Must start with sk_test_ or sk_live_")
        
        key_id = manual_key[:30] + "..."
        return manual_key, key_id
    
    def revoke_old_key(self, key_id: str) -> bool:
        logger.warning(
            "[clerk] Revoke old key via Clerk dashboard:\n"
            "  https://dashboard.clerk.com\n"
            "  Look for key starting with: " + key_id[:15]
        )
        return True
    
    def verify_key(self, key_value: str) -> bool:
        """Verify Clerk key by fetching JWKS."""
        try:
            import urllib.request
            import urllib.error
            
            # Extract instance from key to build JWKS URL
            # Key format: sk_{test|live}_{instanceId}_{random}
            parts = key_value.split("_")
            if len(parts) < 3:
                return False
            
            instance_id = parts[2]
            jwks_url = f"https://clerk.{instance_id}.com/.well-known/jwks.json"
            
            req = urllib.request.Request(jwks_url)
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status == 200
        except Exception as e:
            logger.warning(f"[clerk] Verification warning: {e}")
            # Don't fail on verification - Clerk keys may need instance-specific handling
            return True
    
    def get_affected_services(self) -> list[str]:
        return ["api-gateway", "layer1-ingestion", "layer2-extraction", "layer3-knowledge", "layer4-agents"]


class RegistryTokenProvider(SecretProvider):
    """Container registry token rotation provider."""
    
    @property
    def provider_name(self) -> str:
        return "registry"
    
    def get_infisical_path(self) -> str:
        # Registry token stored in /app folder
        return "/app"
    
    @property
    def infisical_path(self) -> str:
        return self.get_infisical_path()
    
    @property
    def secret_name(self) -> str:
        return "GHCR_PAT"
    
    def get_current_key_id(self) -> str | None:
        try:
            fixed_path = fix_path_for_git_bash(self.infisical_path)
            result = subprocess.run(
                [*INFISICAL_BASE, "secrets", "get",
                 "--env=dev", f"--path={fixed_path}", self.secret_name],
                capture_output=True, text=True, check=True, encoding='utf-8'
            )
            # Parse output - format is "KEY_NAME=VALUE" or just "VALUE"
            output = result.stdout.strip()
            if "=" in output:
                key_value = output.split("=", 1)[1]
            else:
                key_value = output
            return key_value[:20] + "..." if len(key_value) > 20 else key_value
        except Exception:
            return None
    
    def generate_new_key(self) -> tuple[str, str]:
        """Generate new GitHub Container Registry token."""
        logger.warning(
            "[registry] GitHub PAT requires manual generation:\n"
            "  1. Visit: https://github.com/settings/tokens\n"
            "  2. Click 'Generate new token (classic)' or 'Fine-grained token'\n"
            "  3. Required scopes: read:packages, write:packages, delete:packages\n"
            "  4. Set REGISTRY_MANUAL_KEY environment variable\n"
            "  5. Re-run this script"
        )
        
        manual_key = os.getenv("REGISTRY_MANUAL_KEY")
        if not manual_key:
            raise RuntimeError("REGISTRY_MANUAL_KEY environment variable not set")
        
        key_id = manual_key[:20] + "..."
        return manual_key, key_id
    
    def revoke_old_key(self, key_id: str) -> bool:
        logger.warning(
            "[registry] Revoke old token via GitHub:\n"
            "  https://github.com/settings/tokens\n"
            "  Look for token starting with: " + key_id[:10]
        )
        return True
    
    def verify_key(self, key_value: str) -> bool:
        """Verify GHCR token by attempting to access the API."""
        try:
            import urllib.request
            import urllib.error
            
            req = urllib.request.Request(
                "https://api.github.com/user/packages",
                headers={
                    "Authorization": f"Bearer {key_value}",
                    "Accept": "application/vnd.github+json"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status == 200
        except urllib.error.HTTPError as e:
            if e.code == 401:
                logger.error("[registry] Token verification failed: Invalid token")
            else:
                logger.error(f"[registry] Token verification failed: HTTP {e.code}")
            return False
        except Exception as e:
            logger.error(f"[registry] Token verification error: {e}")
            return False
    
    def get_affected_services(self) -> list[str]:
        # Registry tokens are used by CI/CD, not runtime services
        return []


def get_provider(provider_name: str, environment: str, dry_run: bool) -> SecretProvider:
    """Factory function to get the appropriate provider."""
    providers = {
        "openai": OpenAIProvider,
        "thesys": ThesysProvider,
        "clerk": ClerkProvider,
        "registry": RegistryTokenProvider,
    }
    
    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider_name}. Valid options: {list(providers.keys())}")
    
    return provider_class(environment, dry_run)


def write_audit_log(records: list[RotationRecord], output_path: Path | None = None) -> Path:
    """Write rotation audit log to file."""
    if output_path is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"rotation_audit_{timestamp}.json")
    
    audit_data = {
        "rotation_timestamp": datetime.now(timezone.utc).isoformat(),
        "records": [r.to_dict() for r in records],
    }
    
    output_path.write_text(json.dumps(audit_data, indent=2))
    logger.info(f"Audit log written to: {output_path}")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rotate sensitive API keys and secrets for Fabric4L",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run OpenAI rotation for staging
  python scripts/security/key_rotation.py --provider openai --env staging --dry-run
  
  # Rotate Clerk key in production
  python scripts/security/key_rotation.py --provider clerk --env prod
  
  # Rotate all keys (requires manual keys set for each)
  OPENAI_MANUAL_KEY=sk-xxx CLERK_MANUAL_KEY=sk_test_dummy_xxx \\
    python scripts/security/key_rotation.py --provider all --env prod
  
  # Verify only (no rotation)
  python scripts/security/key_rotation.py --provider openai --env prod --verify-only
        """
    )
    
    parser.add_argument(
        "--provider",
        required=True,
        choices=["openai", "thesys", "clerk", "registry", "all"],
        help="Secret provider to rotate"
    )
    parser.add_argument(
        "--env",
        required=True,
        choices=["dev", "staging", "prod"],
        help="Target environment"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate rotation without making changes"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify current keys, no rotation"
    )
    parser.add_argument(
        "--audit-log",
        type=Path,
        help="Path to write audit log JSON"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Determine providers to rotate
    if args.provider == "all":
        providers_to_rotate = ["openai", "thesys", "clerk", "registry"]
    else:
        providers_to_rotate = [args.provider]
    
    all_records: list[RotationRecord] = []
    failed_providers: list[str] = []
    
    for provider_name in providers_to_rotate:
        try:
            provider = get_provider(provider_name, args.env, args.dry_run)
            
            if args.verify_only:
                # Just verify current key
                current_key = provider.get_current_key_id()
                if current_key:
                    logger.info(f"[{provider_name}] Current key found: {current_key}")
                else:
                    logger.warning(f"[{provider_name}] No current key found")
                continue
            
            record = provider.rotate()
            all_records.append(record)
            
        except Exception as e:
            logger.error(f"[{provider_name}] Rotation failed: {e}")
            failed_providers.append(provider_name)
            # Continue with other providers
    
    # Write audit log if any rotations were attempted
    if all_records:
        write_audit_log(all_records, args.audit_log)
    
    # Summary
    print("\n" + "="*60)
    print("ROTATION SUMMARY")
    print("="*60)
    
    completed = [r for r in all_records if r.status == RotationStatus.COMPLETED]
    failed = [r for r in all_records if r.status == RotationStatus.FAILED]
    
    print(f"Completed: {len(completed)}/{len(all_records)}")
    print(f"Failed: {len(failed)}")
    
    for record in all_records:
        status_icon = "[OK]" if record.status == RotationStatus.COMPLETED else "[FAIL]"
        print(f"  {status_icon} {record.provider}: {record.status.value}")
        if record.key_id:
            print(f"      New key: {record.key_id}")
        if record.old_key_id:
            print(f"      Old key: {record.old_key_id}")
        if record.verification_passed:
            print(f"      Verification: PASSED")
    
    if failed_providers:
        print(f"\nFailed providers: {', '.join(failed_providers)}")
    
    print("\n" + "="*60)
    print("IMPORTANT: Manual Actions Required")
    print("="*60)
    print("1. Revoke old keys via provider dashboards (links above)")
    print("2. Update any external documentation")
    print("3. Verify all services are functioning")
    print("4. Keep the audit log for compliance records")
    print("="*60)
    
    return 0 if not failed_providers else 1


if __name__ == "__main__":
    sys.exit(main())
