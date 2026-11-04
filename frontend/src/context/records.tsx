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
  persistenceWarning: boolean;
  addRecord: (r: AnalysisRecord) => void;
  updateRecord: (id: string, update: Partial<AnalysisRecord>) => void;
  removeRecord: (id: string) => void;
  clearRecords: () => boolean;
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
  const [persistenceWarning, setPersistenceWarning] = useState(false);

  const persist = useCallback((next: AnalysisRecord[]) => {
    setPersistenceWarning(!saveRecords(storage, next));
  }, [storage]);

  const addRecord = useCallback(
    (r: AnalysisRecord) => {
      const next = capRecords([r, ...records]);
      persist(next);
      setRecords(next);
    },
    [persist, records]
  );

  const updateRecord = useCallback(
    (id: string, update: Partial<AnalysisRecord>) => {
      const next = records.map((record) => record.id === id
        ? { ...record, ...update }
        : record);
      persist(next);
      setRecords(next);
    },
    [persist, records]
  );

  const removeRecord = useCallback(
    (id: string) => {
      const next = records.filter((r) => r.id !== id);
      persist(next);
      setRecords(next);
    },
    [persist, records]
  );

  const clearRecords = useCallback(() => {
    const savedEmptyList = saveRecords(storage, []);
    setRecords([]);
    let legacyRemoved = true;
    try {
      storage.remove("nutrisense.records.v1");
    } catch {
      legacyRemoved = false;
    }
    const cleared = savedEmptyList && legacyRemoved;
    setPersistenceWarning(!cleared);
    return cleared;
  }, [storage]);

  const value = useMemo<RecordsState>(
    () => ({ records, persistenceWarning, addRecord, updateRecord, removeRecord, clearRecords }),
    [records, persistenceWarning, addRecord, updateRecord, removeRecord, clearRecords]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useRecords(): RecordsState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useRecords must be used inside RecordsProvider");
  return ctx;
}
