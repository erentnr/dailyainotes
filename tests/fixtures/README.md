# Test fixtures

Recorded responses that connector and policy tests serve through `httpx2.MockTransport`; no
test reaches the network.

| Folder | Origin |
|---|---|
| `arxiv/` | A real arXiv API response (2026-10-12), 3 entries. arXiv metadata, abstracts included, is CC0. |
| `github/` | Real GitHub REST releases for vllm-project/vllm (2026-10-12), bodies cut to 600 characters, plus one made-up prerelease. vLLM is Apache-2.0. |
| `hackernews/` | Real HN Algolia hits (2026-10-12), trimmed to the fields we read, plus one made-up "Ask HN" without a URL. |
| `rss/` | The structure of real RSS 2.0 and Atom feeds with sample text and example.com links, so no publisher's prose is stored here. `relative-links.xml` copies the shape of a feed whose item links are relative (seen 2026-10-16). |
| `pages/` | Small made-up pages, one per publisher signal the policy gate checks. |

To refresh a recorded file, fetch it with the project's User-Agent, trim it to what the tests
need, and note the date here.
