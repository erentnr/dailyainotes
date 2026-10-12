import { verdictOf } from "../../lib/format";
import { Check, Cross, Half } from "./Icons";

interface Counts {
  claims: number;
  supported: number;
  unsupported: number;
}

const LOOK = {
  verified: { className: "verdict verdict-ok", icon: <Check />, word: "Verified" },
  partial: { className: "verdict verdict-warn", icon: <Half />, word: "Partially verified" },
  unsupported: { className: "verdict verdict-bad", icon: <Cross />, word: "Unsupported" },
} as const;

export function VerdictBadge(counts: Counts) {
  const verdict = verdictOf(counts);
  if (verdict === "unchecked") return null;
  const { className, icon, word } = LOOK[verdict];
  return (
    <span className={className} title={`${counts.supported} of ${counts.claims} claims supported`}>
      {icon}
      {word}
    </span>
  );
}
