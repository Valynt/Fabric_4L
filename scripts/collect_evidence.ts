#!/usr/bin/env tsx
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdir, readdir, readFile, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

type EvidenceRequirement = {
  id: string;
  name: string;
  control_ids: string[];
  summary_file: string;
  source_patterns: string[];
};

type EvidenceManifest = {
  schema_version: string;
  pipeline: string;
  default_output_dir: string;
  retention_years: number;
  immutability: {
    published_marker: string;
    overwrite_policy: string;
    hash_algorithm: string;
  };
  required_templates: string[];
  required_evidence: EvidenceRequirement[];
};

type SourceMatch = {
  path: string;
  size_bytes: number;
  sha256: string;
  mtime_utc: string;
};

type EvidenceGap = {
  evidence_id: string;
  severity: "info" | "warning";
  reason: string;
  expected_patterns: string[];
};

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const manifestPath = path.join(repoRoot, "compliance", "evidence", "evidence_manifest.json");
const latestPointerPath = path.join(repoRoot, "artifacts", "compliance", "evidence", "LATEST");

function toRepoPath(target: string): string {
  return path.relative(repoRoot, target).replace(/\\/g, "/");
}

function utcTimestampForPath(date = new Date()): string {
  return date.toISOString().replace(/\.\d{3}Z$/, "Z").replace(/:/g, "-");
}

function utcTimestamp(date = new Date()): string {
  return date.toISOString().replace(/\.\d{3}Z$/, "Z");
}

async function readJson<T>(target: string): Promise<T> {
  return JSON.parse(await readFile(target, "utf8")) as T;
}

async function writeJson(target: string, value: unknown): Promise<void> {
  await mkdir(path.dirname(target), { recursive: true });
  await writeFile(target, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

async function sha256File(target: string): Promise<string> {
  return createHash("sha256").update(await readFile(target)).digest("hex");
}

function git(args: string[], fallback = "unknown"): string {
  try {
    const output = execFileSync("git", args, { cwd: repoRoot, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
    return output.trim() || fallback;
  } catch {
    return fallback;
  }
}

async function walkFiles(root: string): Promise<string[]> {
  if (!existsSync(root)) {
    return [];
  }
  let entries;
  try {
    entries = await readdir(root, { withFileTypes: true });
  } catch {
    return [];
  }
  const files: string[] = [];
  for (const entry of entries) {
    const fullPath = path.join(root, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === "node_modules" || entry.name === ".git" || entry.name === ".pnpm-store") {
        continue;
      }
      files.push(...await walkFiles(fullPath));
    } else if (entry.isFile()) {
      files.push(fullPath);
    }
  }
  return files;
}

function patternMatches(repoPath: string, pattern: string): boolean {
  const normalized = repoPath.replace(/\\/g, "/");
  const lowerPath = normalized.toLowerCase();
  const lowerPattern = pattern.toLowerCase();

  if (!pattern.includes("*")) {
    return lowerPath === lowerPattern;
  }
  if (lowerPattern.startsWith("artifacts/**/*")) {
    const needle = lowerPattern.replace("artifacts/**/*", "");
    return lowerPath.startsWith("artifacts/") && lowerPath.includes(needle.replace(/\*/g, ""));
  }
  if (lowerPattern.startsWith("artifacts/**/*.") && lowerPattern.length > "artifacts/**/*.".length) {
    const ext = lowerPattern.slice("artifacts/**/*".length).replace(/\*/g, "");
    return lowerPath.startsWith("artifacts/") && lowerPath.endsWith(ext);
  }
  return lowerPath.includes(lowerPattern.replace(/\*\*/g, "").replace(/\*/g, ""));
}

async function findSources(patterns: string[]): Promise<SourceMatch[]> {
  const candidateRoots = ["artifacts", "apps/web/coverage", ".github/workflows", "docs", "package.json", "pnpm-lock.yaml"];
  const candidates = new Set<string>();

  for (const root of candidateRoots) {
    const fullRoot = path.join(repoRoot, root);
    if (!existsSync(fullRoot)) {
      continue;
    }
    const rootStat = await stat(fullRoot);
    if (rootStat.isFile()) {
      candidates.add(fullRoot);
    } else {
      for (const file of await walkFiles(fullRoot)) {
        candidates.add(file);
      }
    }
  }

  const matches: SourceMatch[] = [];
  for (const candidate of [...candidates].sort()) {
    const repoPath = toRepoPath(candidate);
    if (!patterns.some((pattern) => patternMatches(repoPath, pattern))) {
      continue;
    }
    const info = await stat(candidate);
    matches.push({
      path: repoPath,
      size_bytes: info.size,
      sha256: await sha256File(candidate),
      mtime_utc: info.mtime.toISOString(),
    });
  }
  return matches;
}

async function writeSummary(
  bundleDir: string,
  requirement: EvidenceRequirement,
  generatedAt: string,
): Promise<{ file: string; count: number; gap?: EvidenceGap }> {
  const sources = await findSources(requirement.source_patterns);
  const payload = {
    schema_version: "1.0",
    generated_at_utc: generatedAt,
    evidence_id: requirement.id,
    evidence_name: requirement.name,
    control_ids: requirement.control_ids,
    source_patterns: requirement.source_patterns,
    source_count: sources.length,
    sources,
    sanitized: true,
  };
  const outputPath = path.join(bundleDir, requirement.summary_file);
  await writeJson(outputPath, payload);

  const gap = sources.length === 0
    ? {
        evidence_id: requirement.id,
        severity: "warning" as const,
        reason: "no_matching_source_artifacts_found",
        expected_patterns: requirement.source_patterns,
      }
    : undefined;

  return { file: requirement.summary_file, count: sources.length, gap };
}

async function writeReleaseMetadata(bundleDir: string, generatedAt: string): Promise<void> {
  const lockfile = path.join(repoRoot, "pnpm-lock.yaml");
  const packageJson = await readJson<{ name: string; version: string; packageManager?: string }>(path.join(repoRoot, "package.json"));
  await writeJson(path.join(bundleDir, "release-metadata.json"), {
    schema_version: "1.0",
    generated_at_utc: generatedAt,
    git_sha: git(["rev-parse", "HEAD"]),
    git_branch: git(["rev-parse", "--abbrev-ref", "HEAD"]),
    git_status_porcelain: git(["status", "--short"], ""),
    package_name: packageJson.name,
    package_version: packageJson.version,
    package_manager: packageJson.packageManager ?? "unknown",
    pnpm_lock_sha256: existsSync(lockfile) ? await sha256File(lockfile) : "missing",
    sanitized: true,
  });
}

async function listBundleFiles(bundleDir: string): Promise<{ path: string; size_bytes: number; sha256: string }[]> {
  const files = (await walkFiles(bundleDir))
    .map((file) => ({ file, repoPath: path.relative(bundleDir, file).replace(/\\/g, "/") }))
    .filter(({ repoPath }) => repoPath !== "bundle-manifest.json")
    .sort((a, b) => a.repoPath.localeCompare(b.repoPath));

  const result = [];
  for (const { file, repoPath } of files) {
    const info = await stat(file);
    result.push({ path: repoPath, size_bytes: info.size, sha256: await sha256File(file) });
  }
  return result;
}

async function build(): Promise<void> {
  const sourceManifest = await readJson<EvidenceManifest>(manifestPath);
  const generatedAt = utcTimestamp();
  const gitSha = git(["rev-parse", "HEAD"]);
  const bundleId = `${utcTimestampForPath()}-${gitSha.slice(0, 12)}`;
  const outputRoot = path.join(repoRoot, sourceManifest.default_output_dir);
  const bundleDir = path.join(outputRoot, bundleId);

  if (existsSync(bundleDir)) {
    throw new Error(`Evidence bundle already exists and will not be overwritten: ${toRepoPath(bundleDir)}`);
  }

  await mkdir(outputRoot, { recursive: true });
  await mkdir(bundleDir, { recursive: false });

  const summaries = [];
  const gaps: EvidenceGap[] = [];
  for (const requirement of sourceManifest.required_evidence) {
    if (requirement.summary_file === "release-metadata.json") {
      await writeReleaseMetadata(bundleDir, generatedAt);
    } else {
      const summary = await writeSummary(bundleDir, requirement, generatedAt);
      summaries.push({ evidence_id: requirement.id, file: summary.file, source_count: summary.count });
      if (summary.gap) {
        gaps.push(summary.gap);
      }
    }
  }

  await writeJson(path.join(bundleDir, "evidence-gaps.json"), {
    schema_version: "1.0",
    generated_at_utc: generatedAt,
    gaps,
  });

  await writeJson(path.join(bundleDir, "PUBLISHED.json"), {
    schema_version: "1.0",
    published_at_utc: generatedAt,
    immutability_policy: sourceManifest.immutability.overwrite_policy,
    note: "Do not edit this bundle in place. Generate a new timestamped bundle for corrections.",
  });

  const bundleFiles = await listBundleFiles(bundleDir);
  await writeJson(path.join(bundleDir, "bundle-manifest.json"), {
    schema_version: "1.0",
    pipeline: sourceManifest.pipeline,
    generated_at_utc: generatedAt,
    bundle_id: bundleId,
    git_sha: gitSha,
    git_branch: git(["rev-parse", "--abbrev-ref", "HEAD"]),
    controls_mapping: "compliance/evidence/controls_mapping.md",
    source_manifest: "compliance/evidence/evidence_manifest.json",
    retention_years: sourceManifest.retention_years,
    summaries,
    evidence_gap_count: gaps.length,
    files: bundleFiles,
  });

  await writeFile(latestPointerPath, `${bundleId}\n`, "utf8");
  console.log(JSON.stringify({ bundle_id: bundleId, bundle_path: toRepoPath(bundleDir), evidence_gap_count: gaps.length }, null, 2));
}

async function validateSourceFiles(manifest: EvidenceManifest): Promise<string[]> {
  const errors: string[] = [];
  if (manifest.schema_version !== "1.0") {
    errors.push("evidence_manifest.json schema_version must be 1.0");
  }
  if (manifest.immutability.hash_algorithm !== "sha256") {
    errors.push("evidence_manifest.json must use sha256 hashing");
  }
  for (const template of manifest.required_templates) {
    if (!existsSync(path.join(repoRoot, template))) {
      errors.push(`Missing required template: ${template}`);
    }
  }
  for (const requirement of manifest.required_evidence) {
    if (!requirement.id || !requirement.summary_file || requirement.control_ids.length === 0) {
      errors.push(`Invalid evidence requirement: ${JSON.stringify(requirement)}`);
    }
  }
  const controlsMapping = await readFile(path.join(repoRoot, "compliance/evidence/controls_mapping.md"), "utf8");
  for (const requiredReference of ["docs/reference/compliance.md", "docs/compliance/evidence-inventory-matrix.md"]) {
    if (!controlsMapping.includes(requiredReference)) {
      errors.push(`controls_mapping.md must reference ${requiredReference}`);
    }
  }
  return errors;
}

async function validateLatestBundle(manifest: EvidenceManifest): Promise<string[]> {
  if (!existsSync(latestPointerPath)) {
    return [];
  }
  const latest = (await readFile(latestPointerPath, "utf8")).trim();
  if (!latest) {
    return ["LATEST evidence pointer is empty"];
  }
  const bundleDir = path.join(repoRoot, manifest.default_output_dir, latest);
  const errors: string[] = [];
  if (!existsSync(bundleDir)) {
    return [`LATEST evidence bundle does not exist: ${toRepoPath(bundleDir)}`];
  }
  for (const requiredFile of ["PUBLISHED.json", "bundle-manifest.json", "evidence-gaps.json"]) {
    if (!existsSync(path.join(bundleDir, requiredFile))) {
      errors.push(`Latest bundle missing ${requiredFile}`);
    }
  }
  const bundleManifestPath = path.join(bundleDir, "bundle-manifest.json");
  if (!existsSync(bundleManifestPath)) {
    return errors;
  }
  const bundleManifest = await readJson<{ files?: { path: string; sha256: string }[] }>(bundleManifestPath);
  for (const file of bundleManifest.files ?? []) {
    const target = path.join(bundleDir, file.path);
    if (!existsSync(target)) {
      errors.push(`Manifest references missing file: ${file.path}`);
      continue;
    }
    const actual = await sha256File(target);
    if (actual !== file.sha256) {
      errors.push(`SHA-256 mismatch for ${file.path}`);
    }
  }
  return errors;
}

async function validate(): Promise<void> {
  const sourceManifest = await readJson<EvidenceManifest>(manifestPath);
  const errors = [
    ...await validateSourceFiles(sourceManifest),
    ...await validateLatestBundle(sourceManifest),
  ];
  if (errors.length > 0) {
    console.error("Compliance evidence validation failed:");
    for (const error of errors) {
      console.error(` - ${error}`);
    }
    process.exitCode = 1;
    return;
  }
  console.log("Compliance evidence validation passed.");
}

const command = process.argv[2] ?? "build";
if (command === "build") {
  await build();
} else if (command === "validate") {
  await validate();
} else {
  console.error("Usage: collect_evidence.ts <build|validate>");
  process.exitCode = 2;
}
