import { useState } from "react";

import { Share } from "./Icons";

/** The system's share sheet where there is one; otherwise the link goes to the clipboard. */
export function ShareButton({ title, className }: { title: string; className: string }) {
  const [status, setStatus] = useState("");
  const share = async () => {
    const url = location.href;
    try {
      if (navigator.share) {
        await navigator.share({ title, url });
        return;
      }
      await navigator.clipboard.writeText(url);
      setStatus("Link copied");
    } catch (error) {
      if ((error as Error).name !== "AbortError") setStatus("Couldn't share. Copy the address instead.");
    }
  };
  return (
    <>
      <button type="button" className={className} onClick={() => void share()} aria-label="Share this note">
        <Share />
      </button>
      <span className="share-status" role="status">
        {status}
      </span>
    </>
  );
}
