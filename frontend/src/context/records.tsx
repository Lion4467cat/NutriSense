import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  capRecords,
  loadRecords,
  saveRecords,
  type AnalysisRecord,
} from "../services/records";
import type { Storage } from "../services/storage";

interface RecordsState {
  /** Newest-first (createdAt desc): THE ordering invariant. add/remove/clear
   * preserve it (capRecords re-sorts); selectors in services/records.ts
   * (byNewest/tally/attention) assume it — views must not re-sort for date. */
  records: AnalysisRecord[];
  addRecord: (r: AnalysisRecord) => void;
  removeRecord: (id: string) => void;
  clearRecords: () => void;
}

const Ctx = createContext<RecordsState | null>(null);

export function RecordsProvider({
  children,
  storage,
}: {
  children: ReactNode;
  storage: Storage;
}) {
  const [records, setRecords] = useState<AnalysisRecord[]>(() =>
    loadRecords(storage)
  );

  const addRecord = useCallback(
    (r: AnalysisRecord) => {
      setRecords((prev) => {
        const next = capRecords([r, ...prev]);
        saveRecords(storage, next);
        return next;
      });
    },
    [storage]
  );

  const removeRecord = useCallback(
    (id: string) => {
      setRecords((prev) => {
        const next = prev.filter((r) => r.id !== id);
        saveRecords(storage, next);
        return next;
      });
    },
    [storage]
  );

  const clearRecords = useCallback(() => {
    setRecords(() => {
      saveRecords(storage, []);
      return [];
    });
  }, [storage]);

  const value = useMemo<RecordsState>(
    () => ({ records, addRecord, removeRecord, clearRecords }),
    [records, addRecord, removeRecord, clearRecords]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useRecords(): RecordsState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useRecords must be used inside RecordsProvider");
  return ctx;
}
