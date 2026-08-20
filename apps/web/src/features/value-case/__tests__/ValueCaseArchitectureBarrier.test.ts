import { describe, it, expect } from "vitest";
import * as fs from "fs";
import * as path from "path";

describe("Value Case Architecture Barrier", () => {
  const presentationDir = path.resolve(__dirname, "../presentation");
  const componentsDir = path.resolve(__dirname, "../components");

  function getSourceFiles(dir: string): string[] {
    if (!fs.existsSync(dir)) return [];
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    const files: string[] = [];
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        files.push(...getSourceFiles(fullPath));
      } else if (entry.isFile() && (entry.name.endsWith(".ts") || entry.name.endsWith(".tsx"))) {
        files.push(fullPath);
      }
    }
    return files;
  }

  it("ensures presentation view models and components never import raw API schemas or typed client", () => {
    const files = [...getSourceFiles(presentationDir), ...getSourceFiles(componentsDir)];
    expect(files.length).toBeGreaterThan(0);

    const forbiddenImports = [
      "@/api/typedClient",
      "../api/valueCaseApi",
      "/api/valueCaseApi",
      "ApiBusinessCaseDto",
      "ValueCaseArtifactsInputDto",
    ];

    for (const file of files) {
      const content = fs.readFileSync(file, "utf8");
      for (const forbidden of forbiddenImports) {
        expect(
          content.includes(forbidden),
          `File ${path.basename(file)} contains forbidden direct DTO/API import: "${forbidden}"`
        ).toBe(false);
      }
    }
  });
});
