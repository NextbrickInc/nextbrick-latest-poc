// ─── store/hooks.ts ───────────────────────────────────────────────────────────
// Typed versions of useDispatch and useSelector for this app's store.
// Always use these instead of the raw react-redux versions to get full
// TypeScript inference across all slices.
import { useDispatch, useSelector } from "react-redux";
import type { AppDispatch, RootState } from "./index";

export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector = <T>(selector: (state: RootState) => T): T =>
    useSelector(selector);
