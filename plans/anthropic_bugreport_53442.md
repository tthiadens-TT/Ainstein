# Bug report — Google Drive connector: silent false-negatives on Workspace Shared Drives

**Where to file (in priority order):**
1. Comment on the existing open issue `anthropics/claude-code#53442` (adds weight; 20+ users already report it).
2. `/bug` command inside an interactive Claude Code terminal session.
3. In-app feedback (thumbs down) referencing the issue number.

---

## Title
Google Drive connector: silent false-negatives on Workspace Shared Drives (folder listing AND content search) — empty result, no error

## Summary
The Google Drive connector silently returns empty/no results for content that
demonstrably exists in a Google Workspace **Shared Drive**. The failure is
**silent**: no error, no warning. An empty result is indistinguishable from
"the folder is genuinely empty" or "the file does not exist." That silent nature
is the core problem — it is more damaging than an outright error, because it
produces confident, wrong conclusions.

This looks related to #53442 but is **broader**: it affects not only folder
listing (parentId) but also content search (fullText / title).

## Environment
- Claude Code, Anthropic-hosted Google Drive connector.
- Target: a Google Workspace **Shared Drive** (not "My Drive").
- Ground truth established via a Google **service account** (Drive API v3 with
  `supportsAllDrives=true`, `includeItemsFromAllDrives=true`, `corpora=drive`).
  The service account reads the same Shared Drive completely and correctly,
  which is how we know the connector's empty results are false.

## Observed behavior
1. `search_files` with `parentId = '<subfolder>'` on certain Shared Drive
   subfolders returns an empty list (sometimes only a `nextPageToken`, sometimes
   `{}`), no error. A sibling subfolder at the same depth returns files
   correctly, so it is inconsistent per folder.
2. `list_recent_files` never returns individual Shared Drive files, only folders.
3. `fullText` / `title` search returns **false negatives** on Shared Drive
   content. Example: a 41 KB markdown file that provably exists in the Shared
   Drive (confirmed via service account) was not returned by
   `fullText contains '<distinctive string from that file>'`.
4. Reading a file by known `fileId` works; listing the Shared Drive root works.
   So the connector partially handles Shared Drives (root + known-ID reads) but
   fails on nested listing and on reliable search.
5. A separate Drive tool, `mcp__gdrive__search`, fails on **every** input
   (including a single character) with `MCP error -32603: invalid_request`.

## Likely root cause (per #53442)
The connector omits `supportsAllDrives` / `includeItemsFromAllDrives` /
`corpora` on nested queries, silently scoping to the user corpus
(My Drive + shared-with-me), which excludes Shared Drive contents.

## Impact
Because the failure is silent, it is indistinguishable from real emptiness. Over
multiple sessions this produced repeated wrong root-cause conclusions and, in one
case, an entire multi-agent investigation whose negative findings
("files missing / migration incomplete") were themselves artifacts of this bug —
reversed only after a service-account scan proved all content was present. This
cost very substantial time and token spend. Either correct Shared Drive handling,
or a clear error instead of a silent empty, would have prevented all of it.

## Requested fixes (priority order)
1. Send `supportsAllDrives=true`, `includeItemsFromAllDrives=true`, and the
   correct `corpora` on **all** list/search operations, so Shared Drive content
   surfaces the same way "My Drive" content does.
2. If a query is scoped in a way that cannot include Shared Drives, return a
   clear warning/error instead of a silent empty result. Silent false-negatives
   are the worst possible failure mode for an AI agent.
3. Fix `mcp__gdrive__search` returning `-32603` on all inputs.
4. Document Shared Drive support and current limitations in the Google Workspace
   connector help article (Shared Drives are currently not mentioned at all).

Reference: #53442
