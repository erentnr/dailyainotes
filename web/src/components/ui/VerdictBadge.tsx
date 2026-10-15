import { verdictOf } from "../../lib/format";
import { Check, Cross, Half } from "./Icons";

interface Counts {
  claims: number;
  supported: number;
  unsupported: number;
}

const LOOK = {
  verified: { className: "verdict verdict-ok", icon: <Check />, word: "Verified" },
  partial: { className: "verdict verdict-warn", icon: <Half />, word: "Partly verified" },
  unsupported: { className: "verdict verdict-bad", icon: <Cross />, word: "Unsupported claims" },
} as const;

/** The fact-check's verdict as an icon and a word, never color alone. */
export function VerdictBadge({ counts, detail = false }: { counts: Counts; detail?: boolean }) {
  const verdict = verdictOf(counts);
  if (verdict === "unchecked") return null;
  const { className, icon, word } = LOOK[verdict];
  return (
    <span className={className} title={`${counts.supported} of ${counts.claims} claims supported`}>
      {icon}
      {word}
      {detail && ` · ${counts.supported}/${counts.claims} supported`}
    </span>
  );
}
