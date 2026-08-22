#!/usr/bin/env python3
"""Validate production Kubernetes overlays and image references.

This guard intentionally starts with static checks so it can catch broken
resource paths and unsafe image references before optional rendering tools are
installed. When ``kustomize`` is available on PATH, each discovered production
overlay is also rendered.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
KUSTOMIZATION_NAMES = ("kustomization.yaml", "kustomization.yml", "Kustomization")
PRODUCTION_OVERLAYS = [
    ROOT / "k8s" / "envs" / "prod",
    ROOT / "k8s" / "overlays" / "production",
]
PRODUCTION_OVERLAYS.extend(sorted((ROOT / "k8s" / "deployments").glob("prod-*")))

SERVICE_IMAGE_NAMES = {
    "apps/web",
    "services/api",
    "services/layer1-ingestion",
    "services/layer2-extraction",
    "services/layer2-5-signal-refinery",
    "services/layer3-knowledge",
    "services/layer4-agents",
    "services/layer5-ground-truth",
    "services/layer6-benchmarks",
}
MUTABLE_TAGS = {"latest", "main", "master", "develop", "dev", "staging", "production", "stable", "edge", "nightly"}
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
PLACEHOLDER_DIGEST_RE = re.compile(r"^sha256:([0-9a-f])\1{63}$")


@dataclass(frozen=True)
class ResourceRef:
    api_version: str
    kind: str
    namespace: str
    name: str

    def display(self) -> str:
        ns = f" namespace={self.namespace}" if self.namespace else ""
        return f"{self.api_version} {self.kind}/{self.name}{ns}"


class ValidationError(Exception):
    pass


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def find_kustomization(directory: Path) -> Path:
    for name in KUSTOMIZATION_NAMES:
        candidate = directory / name
        if candidate.exists():
            return candidate
    raise ValidationError(f"{rel(directory)} has no kustomization.yaml")


def load_yaml_file(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_yaml_documents(path: Path) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for doc in yaml.safe_load_all(path.read_text(encoding="utf-8")):
        if isinstance(doc, dict):
            docs.append(doc)
    return docs


def resolve_resource_files(kustomization_dir: Path, seen_dirs: set[Path] | None = None) -> list[Path]:
    seen_dirs = seen_dirs or set()
    kustomization_dir = kustomization_dir.resolve()
    if kustomization_dir in seen_dirs:
        return []
    seen_dirs.add(kustomization_dir)

    kustomization = find_kustomization(kustomization_dir)
    data = load_yaml_file(kustomization)
    files: list[Path] = []
    for resource in data.get("resources") or []:
        resource_path = (kustomization_dir / resource).resolve()
        if not resource_path.exists():
            raise ValidationError(f"{rel(kustomization)} references missing resource {resource}")
        if resource_path.is_dir():
            files.extend(resolve_resource_files(resource_path, seen_dirs))
            continue
        if resource_path.suffix not in {".yaml", ".yml"}:
            raise ValidationError(f"{rel(kustomization)} references non-YAML resource {resource}")
        files.append(resource_path)
    return files


def resource_id(doc: dict[str, Any]) -> ResourceRef | None:
    metadata = doc.get("metadata") or {}
    api_version = doc.get("apiVersion")
    kind = doc.get("kind")
    name = metadata.get("name")
    if not all(isinstance(value, str) and value for value in (api_version, kind, name)):
        return None
    namespace = metadata.get("namespace") if isinstance(metadata.get("namespace"), str) else ""
    return ResourceRef(api_version, kind, namespace, name)


def validate_no_duplicate_resources(overlay: Path, files: list[Path]) -> list[str]:
    failures: list[str] = []
    seen: dict[ResourceRef, Path] = {}
    for file_path in files:
        for doc in load_yaml_documents(file_path):
            ref = resource_id(doc)
            if ref is None:
                continue
            previous = seen.get(ref)
            if previous is not None:
                failures.append(
                    f"{rel(overlay)} defines {ref.display()} more than once: {rel(previous)} and {rel(file_path)}"
                )
            else:
                seen[ref] = file_path
    return failures


def image_tag(image: str) -> str | None:
    # Digest-pinned images are immutable regardless of tag-like path segments.
    if "@sha256:" in image:
        return None
    last_slash = image.rfind("/")
    last_colon = image.rfind(":")
    if last_colon > last_slash:
        return image[last_colon + 1 :]
    return None


def validate_image_reference(image: str, source: str) -> list[str]:
    failures: list[str] = []
    if not image:
        failures.append(f"{source} has an empty image reference")
        return failures
    digest_match = re.search(r"@sha256:([0-9a-f]{64})$", image)
    if digest_match:
        digest = f"sha256:{digest_match.group(1)}"
        if PLACEHOLDER_DIGEST_RE.fullmatch(digest):
            failures.append(f"{source} uses placeholder digest {digest}")
        return failures
    tag = image_tag(image)
    if tag is None:
        # Kustomize image placeholders are allowed only when they are rewritten by
        # the overlay images block. Direct registry references must carry a tag or digest.
        if image not in SERVICE_IMAGE_NAMES:
            failures.append(f"{source} is not tag- or digest-pinned: {image}")
        return failures
    if tag in MUTABLE_TAGS:
        failures.append(f"{source} uses mutable production tag {image}")
    return failures


def iter_container_images(value: Any) -> list[str]:
    images: list[str] = []
    if isinstance(value, dict):
        for key in ("containers", "initContainers", "ephemeralContainers"):
            entries = value.get(key)
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, dict) and isinstance(entry.get("image"), str):
                        images.append(entry["image"])
        for child in value.values():
            images.extend(iter_container_images(child))
    elif isinstance(value, list):
        for child in value:
            images.extend(iter_container_images(child))
    return images


def validate_raw_resource_images(files: list[Path]) -> list[str]:
    failures: list[str] = []
    for file_path in files:
        for doc in load_yaml_documents(file_path):
            for image in iter_container_images(doc):
                failures.extend(validate_image_reference(image, f"{rel(file_path)} image"))
    return failures


def validate_kustomization_images(kustomization: Path) -> list[str]:
    failures: list[str] = []
    data = load_yaml_file(kustomization)
    images = data.get("images") or []
    if not isinstance(images, list):
        return [f"{rel(kustomization)} images must be a list"]

    image_names = {entry.get("name") for entry in images if isinstance(entry, dict)}
    missing = sorted(SERVICE_IMAGE_NAMES - image_names)
    if (kustomization.parent / "../../base").resolve().exists() and any(
        resource in {"../../base", "../../base/"} for resource in (data.get("resources") or [])
    ):
        for name in missing:
            failures.append(f"{rel(kustomization)} missing production image override for {name}")

    for entry in images:
        if not isinstance(entry, dict):
            failures.append(f"{rel(kustomization)} contains a non-object images entry: {entry!r}")
            continue
        name = entry.get("name")
        digest = entry.get("digest")
        new_tag = entry.get("newTag")
        new_name = entry.get("newName")
        source = f"{rel(kustomization)} images[{name}]"
        if not isinstance(name, str) or not name:
            failures.append(f"{source} is missing name")
            continue
        if isinstance(new_name, str) and image_tag(new_name):
            failures.append(f"{source} newName must not include a tag: {new_name}")
        if name in SERVICE_IMAGE_NAMES:
            if new_tag is not None:
                failures.append(f"{source} must use digest, not newTag")
            if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
                failures.append(f"{source} must use a sha256 digest")
            elif PLACEHOLDER_DIGEST_RE.fullmatch(digest):
                failures.append(f"{source} uses placeholder digest {digest}")
        elif isinstance(new_tag, str):
            if new_tag in MUTABLE_TAGS:
                failures.append(f"{source} uses mutable production newTag {new_tag}")
    return failures


def render_with_kustomize(overlay: Path) -> list[str]:
    kustomize = shutil.which("kustomize")
    if not kustomize:
        return [f"SKIP kustomize render for {rel(overlay)} because kustomize is not installed"]
    result = subprocess.run(
        [kustomize, "build", "--load-restrictor=LoadRestrictionsNone", str(overlay)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        return [f"{rel(overlay)} failed kustomize build: {result.stderr.strip()}"]

    rendered_yaml = result.stdout
    kubeconform = shutil.which("kubeconform")
    if not kubeconform:
        return [f"SKIP kubeconform validation for {rel(overlay)} because kubeconform is not installed"]

    kc_result = subprocess.run(
        [
            kubeconform,
            "-strict",
            "-ignore-missing-schemas",
            "-kubernetes-version",
            "1.30.0",
            "-summary",
        ],
        input=rendered_yaml,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if kc_result.returncode != 0:
        err_msg = kc_result.stderr.strip() or kc_result.stdout.strip()
        return [f"{rel(overlay)} failed kubeconform schema validation: {err_msg}"]

    return []


def main() -> int:
    failures: list[str] = []
    warnings: list[str] = []
    for overlay in PRODUCTION_OVERLAYS:
        if not overlay.exists():
            failures.append(f"Missing production overlay directory: {rel(overlay)}")
            continue
        try:
            kustomization = find_kustomization(overlay)
            files = resolve_resource_files(overlay)
        except ValidationError as exc:
            failures.append(str(exc))
            continue
        failures.extend(validate_no_duplicate_resources(overlay, files))
        failures.extend(validate_raw_resource_images(files))
        failures.extend(validate_kustomization_images(kustomization))
        render_results = render_with_kustomize(overlay)
        for item in render_results:
            if item.startswith("SKIP "):
                warnings.append(item)
            else:
                failures.append(item)

    if warnings:
        print("WARN Kubernetes production overlay validation warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    if failures:
        print("FAIL Kubernetes production overlay validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print(f"PASS Kubernetes production overlay validation passed for {len(PRODUCTION_OVERLAYS)} overlay(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
