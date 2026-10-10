import { useMenu } from "../context/menu";
import type { AnalysisRecord } from "../services/records";
import { earlierPolicyVersion } from "../utils/policy";

/** Subtle caption for records judged under a policy other than today's.
 *  Only claims "earlier" when the menu seam reports today's policy ready. */
export default function PolicyNote({ record }: { record: AnalysisRecord }) {
  const { menu, policyState } = useMenu();
  if (policyState !== "ready") return null;
  const current = menu?.policy?.policy_version;
  if (!earlierPolicyVersion(record.result?.policy?.policy_version, current)) {
    return null;
  }
  return <span className="policy-note">judged under an earlier policy</span>;
}
