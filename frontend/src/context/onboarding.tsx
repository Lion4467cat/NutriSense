import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { AnimatePresence } from "framer-motion";
import OnboardingModal from "../ui/OnboardingModal";

/**
 * Profile setup (name, sex, age band, activity level, Daily goal).
 *
 * Nothing opens automatically and nothing is remembered as "already asked":
 * the profile only matters for General mode, so ModeSwitch opens this wizard
 * on every switch into General while no profile is saved, and Settings keeps
 * a manual entry point. Visibility lives here rather than in AppShell so both
 * can reach it.
 */
interface OnboardingState {
  open: boolean;
  openWizard: () => void;
  closeWizard: () => void;
}

const Ctx = createContext<OnboardingState | null>(null);

export function OnboardingProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);

  const openWizard = useCallback(() => setOpen(true), []);
  const closeWizard = useCallback(() => setOpen(false), []);

  const value = useMemo<OnboardingState>(
    () => ({ open, openWizard, closeWizard }),
    [open, openWizard, closeWizard]
  );

  return (
    <Ctx.Provider value={value}>
      {children}
      <AnimatePresence>
        {open && <OnboardingModal onClose={closeWizard} />}
      </AnimatePresence>
    </Ctx.Provider>
  );
}

export function useOnboarding(): OnboardingState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useOnboarding must be used inside OnboardingProvider");
  return ctx;
}
