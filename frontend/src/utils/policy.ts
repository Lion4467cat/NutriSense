/**
 * A record was "judged under an earlier policy" when its stored
 * policy_version differs from the one the backend serves today. Migrated v1
 * records have no policy block at all → their version reads "unknown".
 *
 * No current version in hand (menu loading or failed) → make no claim.
 */
export function earlierPolicyVersion(
  recordPolicyVersion: string | null | undefined,
  currentPolicyVersion: string | null | undefined
): boolean {
  if (!currentPolicyVersion) return false;
  const stored = recordPolicyVersion || "unknown";
  return stored !== currentPolicyVersion;
}
