import type { ReactNode } from "react";
import type { ApiClient } from "../services/api";
import type { Storage } from "../services/storage";
import { MenuProvider } from "./menu";
import { PrefsProvider } from "./prefs";
import { RecordsProvider } from "./records";

/**
 * AppProvider is only the composition root's facade: main.tsx hands in the
 * real adapters and every consumer mounts through a domain hook
 * (useMenu / useRecords / usePrefs). Tests may mount any subset directly.
 */
export function AppProvider({
  children,
  storage,
  client,
}: {
  children: ReactNode;
  storage: Storage;
  client: ApiClient;
}) {
  return (
    <MenuProvider client={client}>
      <RecordsProvider storage={storage}>
        <PrefsProvider storage={storage}>{children}</PrefsProvider>
      </RecordsProvider>
    </MenuProvider>
  );
}
