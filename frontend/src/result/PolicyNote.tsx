import { useApp } from "../context/AppContext";
import type { AnalysisRecord } from "../services/records";
import { earlierPolicyVersion } from "../utils/policy";

/** Subtle caption for records judged under a policy other than today's. */
export default function PolicyNote({ record }: { record: AnalysisRecord }) {
  const { menu } = useApp();
  const current = menu?.policy?.policy_version;
  if (!earlierPolicyVersion(record.result?.policy?.policy_version, current)) {
    return null;
  }
  return <span className="policy-note">judged under an earlier policy</span>;
}
