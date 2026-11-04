import { useEffect, useRef, useState } from "react";

export const MAX_MEAL_IMAGE_BYTES = 12 * 1024 * 1024;

type CaptureState =
  | { phase: "empty"; file: null; error: null }
  | { phase: "ready" | "submitting"; file: File; error: null }
  | { phase: "failed"; file: File | null; error: string };

const EMPTY: CaptureState = { phase: "empty", file: null, error: null };

export function captureFileError(file: File): string | null {
  const supportedType = file.type === "image/jpeg" || file.type === "image/png";
  const missingType = file.type.length === 0;
  const supportedExtension = /\.(jpe?g|png)$/i.test(file.name);
  if (!supportedType && !(missingType && supportedExtension)) {
    return "That file type isn't supported — please choose an image (JPEG or PNG).";
  }
  if (file.size === 0) return "That image is empty. Choose a different JPEG or PNG photo.";
  if (file.size > MAX_MEAL_IMAGE_BYTES) {
    return "That image is larger than 12 MB. Choose a smaller photo and retry.";
  }
  return null;
}

/** Owns photo selection, preview cleanup, validation and submit transitions. */
export function useMealCapture() {
  const [state, setState] = useState<CaptureState>(EMPTY);
  const [preview, setPreview] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const submitting = useRef(false);
  const file = state.file;

  useEffect(() => {
    if (!file) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const selectFile = (next: File | null | undefined) => {
    if (!next || submitting.current || state.phase === "submitting") return;
    const error = captureFileError(next);
    setState(error
      ? { phase: "failed", file: null, error }
      : { phase: "ready", file: next, error: null });
  };

  const begin = () => {
    if (state.phase !== "ready" || submitting.current) return null;
    submitting.current = true;
    setState({ phase: "submitting", file: state.file, error: null });
    return state.file;
  };

  const complete = () => {
    submitting.current = false;
    setState((current) => current.phase === "submitting"
      ? { phase: "ready", file: current.file, error: null }
      : current);
  };

  const fail = (error: string) => {
    submitting.current = false;
    setState((current) => ({ phase: "failed", file: current.file, error }));
  };

  const dismissError = () => {
    setState((current) => current.phase === "failed"
      ? current.file
        ? { phase: "ready", file: current.file, error: null }
        : EMPTY
      : current);
  };

  const clear = () => {
    if (!submitting.current) setState(EMPTY);
  };

  return {
    phase: state.phase,
    file,
    preview,
    error: state.error,
    dragging,
    setDragging,
    selectFile,
    begin,
    complete,
    fail,
    dismissError,
    clear,
  };
}
