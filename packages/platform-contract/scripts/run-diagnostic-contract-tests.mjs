import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import ts from "typescript";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const TEST_SHIMS = path.join(ROOT, "src/typescript/test-shims.d.ts");

const EXPECTED_EXPORTS = {
  ".": "./src/typescript/index.ts",
  "./agent-result": "./src/typescript/agent-result.ts",
  "./authorization-snapshot": "./src/typescript/authorization-snapshot.ts",
  "./routing": "./src/typescript/routing.ts",
  "./stores": "./src/typescript/stores.ts",
};

const NEGATIVE_CASES = [
  {
    file: "src/typescript/negative/invalid-route-tier.ts",
    expectedSubstrings: ['"owner"', "RouteTier"],
  },
  {
    file: "src/typescript/negative/invalid-access-decision.ts",
    expectedSubstrings: ["Property 'reason' is missing"],
  },
  {
    file: "src/typescript/negative/invalid-store-setter.ts",
    expectedSubstrings: ["Argument of type 'number'", "parameter of type 'string'"],
  },
  {
    file: "src/typescript/negative/missing-barrel-export.ts",
    expectedSubstrings: ["has no exported member 'MissingExport'"],
  },
  {
    file: "src/typescript/negative/missing-subpath-export.ts",
    expectedSubstrings: ["has no exported member 'MissingRoutingExport'"],
  },
  {
    file: "src/typescript/negative/invalid-authorization-snapshot.ts",
    expectedSubstrings: [
      '"unknown_role"',
      "Type 'AuthorizationSnapshot' is not assignable to type 'null'",
    ],
  },
];

function assertExportMap() {
  const packageJson = JSON.parse(
    fs.readFileSync(path.join(ROOT, "package.json"), "utf8"),
  );

  for (const [key, value] of Object.entries(EXPECTED_EXPORTS)) {
    if (packageJson.exports?.[key] !== value) {
      throw new Error(
        `Export map mismatch for '${key}'. Expected '${value}' but found '${packageJson.exports?.[key] ?? "<missing>"}'.`,
      );
    }
  }
}

function loadCompilerOptions() {
  const configPath = path.join(ROOT, "tsconfig.json");
  const config = ts.readConfigFile(configPath, ts.sys.readFile);
  if (config.error) {
    throw new Error(
      ts.flattenDiagnosticMessageText(config.error.messageText, "\n"),
    );
  }

  const parsed = ts.parseJsonConfigFileContent(config.config, ts.sys, ROOT);
  if (parsed.errors.length > 0) {
    throw new Error(
      parsed.errors
        .map((error) =>
          ts.flattenDiagnosticMessageText(error.messageText, "\n"),
        )
        .join("\n"),
    );
  }

  return parsed.options;
}

function formatDiagnostics(diagnostics) {
  return diagnostics.map((diagnostic) => {
    const message = ts.flattenDiagnosticMessageText(
      diagnostic.messageText,
      "\n",
    );
    const file = diagnostic.file
      ? path.relative(ROOT, diagnostic.file.fileName)
      : "<config>";
    return `${file}: ${message}`;
  });
}

function assertNegativeDiagnostics() {
  const options = loadCompilerOptions();
  const failures = [];

  for (const testCase of NEGATIVE_CASES) {
    const absoluteFile = path.join(ROOT, testCase.file);
    const program = ts.createProgram({
      rootNames: [TEST_SHIMS, absoluteFile],
      options: {
        ...options,
        noEmit: true,
      },
    });
    const diagnostics = formatDiagnostics(ts.getPreEmitDiagnostics(program));
    const joined = diagnostics.join("\n");

    if (diagnostics.length === 0) {
      failures.push(
        `${testCase.file}: expected diagnostics, but compilation succeeded.`,
      );
      continue;
    }

    for (const snippet of testCase.expectedSubstrings) {
      if (!joined.includes(snippet)) {
        failures.push(
          `${testCase.file}: expected diagnostic snippet '${snippet}'.\nActual diagnostics:\n${joined}`,
        );
      }
    }
  }

  if (failures.length > 0) {
    throw new Error(failures.join("\n\n"));
  }
}

assertExportMap();
assertNegativeDiagnostics();
console.log("Platform contract diagnostic checks passed.");
