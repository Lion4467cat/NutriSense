import { FALLBACK_POLICY } from "../types/api";

/**
 * A record was "judged under an earlier policy" when its stored
 * policy_version differs from the one the backend serves today. Migrated v1
 * records have no policy block at all → their version reads "unknown".
 */
export function earlierPolicyVersion(
  recordPolicyVersion: string | null | undefined,
  currentPolicyVersion: string | null | undefined
): boolean {
  const stored = recordPolicyVersion || "unknown";
  const current = currentPolicyVersion || FALLBACK_POLICY.policy_version;
  return stored !== current;
}
