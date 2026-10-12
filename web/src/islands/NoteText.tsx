import { useState } from "react";

import { CitedText } from "../components/ui/CitedText";
import type { NoteDetail } from "../lib/api/client";

/** The note's text with citation chips that open their source in place. */
export default function NoteText({ note }: { note: NoteDetail }) {
  const [open, setOpen] = useState<number | null>(null);
  const toggle = (marker: number) => setOpen(open === marker ? null : marker);
  return (
    <div className="reading">
      <CitedText text={note.body} citations={note.citations} open={open} onToggle={toggle} />
      <div className="label" style={{ marginTop: "var(--space-6)" }}>
        Why it matters
      </div>
      <CitedText
        text={note.why_it_matters}
        citations={note.citations}
        open={open}
        onToggle={toggle}
      />
    </div>
  );
}
