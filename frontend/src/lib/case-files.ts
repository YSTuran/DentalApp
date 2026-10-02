import type { CaseFileKind, CaseFileVersion } from "../types/case";

export function latestCaseFile(
  files: CaseFileVersion[],
  kind: CaseFileKind,
): CaseFileVersion | null {
  return files.reduce<CaseFileVersion | null>((latest, file) => {
    if (file.kind !== kind) return latest;
    return latest === null || file.version_number > latest.version_number ? file : latest;
  }, null);
}
