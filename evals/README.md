# The eval set

30 questions for Ask the notes, over a frozen corpus of 40 notes in 8 catalog topics.

**Every note here is fictional.** The companies, places, products and numbers are invented, so the set tests retrieval and citations without reproducing anyone's reporting or making claims about real people.

- `corpus.jsonl`: one published note per line (slug, topic, date, title, body with `[n]` markers, why it matters).
- `questions.jsonl`: 22 questions that one note answers (`expected` is its slug), 4 of them paraphrased so they share no name with the note, and 8 that no note answers (`expected` is null).
- `baseline.json`: the scores a change must not fall below.

`uv run dan evals run` loads the corpus into a scratch database (`dailyainotes_eval`, dropped afterwards), embeds it with the local model and asks every question:

- `recall_at_5`: the expected note is among Ask's sources.
- `mrr`: how high it ranks (1 / its rank, averaged).
- `not_enough_when_uncovered`: a question no note answers finds no source, so Ask says "not enough" without calling a model.

CI runs it on every pull request, with no model. `--judge` also has the Ask model answer each covered question and a judge from another model family (`LLM_JUDGE`) say whether the answer keeps to the notes it cites (`faithfulness`); the worker runs that nightly with `--record`, which saves the scores in `eval_runs`.

`--update-baseline` rewrites `baseline.json`. A commit that changes it says why.
