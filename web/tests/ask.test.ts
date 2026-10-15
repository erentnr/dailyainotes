import { describe, expect, it } from "vitest";

import { daysLabel, daysOf, scopeLabel, shortfall, suggestedQuestions } from "../src/lib/ask";

describe("Ask's date range", () => {
  const today = "2026-10-15";
  const none = { from: "", to: "" };

  it("counts today among the last 7 or 30 days, and leaves all time open", () => {
    expect(daysOf("7d", today, none)).toEqual({ since: "2026-10-09" });
    expect(daysOf("30d", today, none)).toEqual({ since: "2026-09-16" });
    expect(daysOf("all", today, none)).toEqual({});
  });

  it("takes picked dates in either order, or one end only", () => {
    expect(daysOf("custom", today, { from: "2026-10-12", to: "2026-10-01" })).toEqual({
      since: "2026-10-01",
      until: "2026-10-12",
    });
    expect(daysOf("custom", today, { from: "", to: "2026-10-01" })).toEqual({ until: "2026-10-01" });
    expect(daysOf("custom", today, none)).toEqual({});
  });

  it("names the days and the topics an answer searched", () => {
    expect(daysLabel({ since: "2026-10-09", until: "2026-10-15" })).toBe("9 Oct 2026 – 15 Oct 2026");
    expect(daysLabel({})).toBe("Any day");
    expect(scopeLabel([], "7d", { since: "2026-10-09" })).toBe("All topics · Last 7 days");
    expect(scopeLabel(["Formula 1", "Tennis"], "custom", { since: "2026-10-01" })).toBe(
      "Formula 1, Tennis · From 1 Oct 2026",
    );
  });

  it("says what was searched when the notes fall short, and nothing more", () => {
    expect(shortfall(["Formula 1"], "7d", { since: "2026-10-09" })).toBe(
      "None of the notes on Formula 1 from the last 7 days cover it.",
    );
    expect(shortfall([], "custom", { since: "2026-10-01", until: "2026-10-05" })).toBe(
      "None of the notes from 1 Oct 2026 to 5 Oct 2026 cover it.",
    );
    expect(shortfall([], "all", {})).toBe("No published note covers it.");
  });

  it("suggests one question per topic, at most four", () => {
    const questions = suggestedQuestions(["A", "B", "C", "D", "E"]);

    expect(questions).toHaveLength(4);
    expect(questions[0]).toBe("What's new in A this week?");
  });
});
