# Merge Strategy Test Matrix

## Conventions

- Strategy is configured per-scope in config YAML (e.g., `strategy: append`)
- Default strategy is `overwrite` (backwards compatible)
- Template filler syntax uses `@NAME` blocks: `@NAME` starts a block, content runs until the next `@NAME` or end of file
- Template placeholder sigils: `{FOO}` (first filler), `{!FOO}` (last filler), `{?FOO}` (first filler, strip if empty), `{!?FOO}` (last filler, strip if empty)

## Strategy 1: Overwrite (existing, default)

| # | Test | Scopes | What to verify |
|---|---|---|---|
| 1 | Single scope, one file | 1 unscoped | Content passes through unchanged |
| 2 | Most specific wins | 2 unscoped + 1 scoped | Scoped overrides unscoped |
| 3 | Unique content passes through | 2 unscoped + 1 scoped | Files without conflicts pass through |
| 4 | Provenance tracking | 2 unscoped + 1 scoped | Provenance records winning scope |
| 5 | Unknown repo | 2 unscoped + 1 scoped | Unknown repo gets unscoped content only |
| 6 | Three unscoped, same file | 3 unscoped | Last unscoped wins |
| 7 | Five scopes mixed (2 unscoped, repo A, repo B, repo A) | 5 mixed | Correct winner per repo across N layers |

## Strategy 2: Append

| # | Scenario | What to verify |
|---|---|---|
| 1 | Two scopes, same file, second appends | Content concatenated in order |
| 2 | Three scopes, same file, all append | All three concatenated in scope order |
| 3 | Disjoint files across scopes | Both pass through unchanged |
| 4 | Mixed shared and unique files | Shared appended, unique pass through |
| 5 | Unknown repo | Only unscoped content appended |
| 6 | Multi-branch: different repos get different appends | api-gateway gets api's append, web-app gets frontend's |
| 7 | File exists only in scoped scope, not in base | Append to nothing — what happens? |
| 8 | Five scopes (2 unscoped, repo A, repo B, repo A), all append | Repo A gets 4 layers concatenated, repo B gets 3, no repo gets 2 |

## Strategy 3: Merge-append

### Basic heading matching

| # | Scenario | What to verify |
|---|---|---|
| 1 | Matching `##` heading, two scopes | Content appended under matching `##` |
| 2 | Matching `###` under same `##` | Appended under correct `##` > `###` path |
| 3 | Same `###` name under different `##` parents | Only appends under correct parent path |
| 4 | No matching heading — new section | Team section appended at end of doc |
| 5 | Body text under `##`, no subsections | Team body text appended after org body text |
| 6 | Team provides `##` with body and `###` children | Body appends under `##`, subsection appends under `###` |
| 7 | Team provides only `###`, no `##` body | Only `###` content appended, `##` body untouched |

### Hierarchy depth

| # | Scenario | What to verify |
|---|---|---|
| 8 | `####` under `###` under `##` | Matches 3-deep heading path |
| 9 | Org has `##` > `###`, team adds new `####` under existing `###` | New `####` appended under matching `###` |
| 10 | Team adds entirely new `##` with `###` children | Whole new tree appended at end |

### N-level cascading

| # | Scenario | What to verify |
|---|---|---|
| 11 | Three scopes all merge-append to same `##` | All three bodies present in order |
| 12 | Three scopes, each appends to different `###` | Each `###` gets only its relevant append |
| 13 | Middle scope adds new `###`, bottom scope appends to it | Div's new section present, team's content under it |

### Multi-branch with repos

| # | Scenario | What to verify |
|---|---|---|
| 14 | Five scopes (2 unscoped, repo A, repo B, repo A), all merge-append | Repo A gets 4 layers merged, repo B gets 3, no repo gets 2 |
| 15 | Different repos append under different headings | api team under `## Testing`, frontend under `## Deploy` |
| 16 | Two scoped scopes for same repo, each appends under different `###` | Both `###` sections get their appends |

### Untouched content

| # | Scenario | What to verify |
|---|---|---|
| 17 | Org sections team doesn't mention | Untouched |
| 18 | Content between headings preserved | Non-heading paragraphs stay in place |
| 19 | Frontmatter preserved | YAML frontmatter not affected |
| 20 | Disjoint files across scopes | Both pass through unchanged |

### Edge cases

| # | Scenario | What to verify |
|---|---|---|
| 21 | File exists only in scoped scope, not in base | Merge-append to nothing |
| 22 | Empty section in team file | Nothing appended under that heading |
| 23 | Team file has heading org doesn't have | Treated as new section, appended at end |

## Strategy 4: Template

### Basic substitution

| # | Scenario | What to verify |
|---|---|---|
| 1 | Single `{FOO}` placeholder, team fills it | Placeholder replaced inline |
| 2 | Multiple placeholders, team fills all | Each replaced correctly |
| 3 | Multiple placeholders, team fills some | Filled replaced, unfilled left |
| 4 | Team provides section with no matching placeholder | Extra content — ignored or appended at end (TBD) |
| 5 | Placeholder in middle of a paragraph | Inline replacement, surrounding text intact |
| 6 | Same placeholder appears twice in org file | Both instances replaced |
| 7 | Placeholder name collision with markdown heading | `{COVERAGE}` vs `## COVERAGE` — no confusion |
| 8 | File exists only in scoped scope with template strategy | Template to nothing |
| 9 | Nested placeholder — filled content contains new placeholder | Next scope can resolve it (cascading) |
| 10 | Empty section for a placeholder | Placeholder replaced with empty string |

### N-level cascading

| # | Scenario | What to verify |
|---|---|---|
| 11 | Org placeholder, division fills it | Division content replaces placeholder |
| 12 | Org placeholder, division leaves it, team fills it | Placeholder survives division, team fills it |
| 13 | Division introduces new placeholder in its content, team fills it | Cascading placeholder creation and filling |
| 14 | Each level fills different placeholders | Each filled by correct level |
| 15 | Division fills `{!FOO}`, team also fills `{!FOO}` | Last filler wins (team) |
| 16 | Three scopes all try to fill `{FOO}` | First filler wins |

### Sigil behavior — `{FOO}` first filler wins

| # | Scenario | What to verify |
|---|---|---|
| 17 | Two scopes fill same `{FOO}` | First filler wins, second ignored |
| 18 | Three scopes fill same `{FOO}` | First filler wins, second and third ignored |
| 19 | `{FOO}` unfilled by any scope | Left in output as literal `{FOO}` |

### Sigil behavior — `{!FOO}` last filler wins

| # | Scenario | What to verify |
|---|---|---|
| 20 | Two scopes fill same `{!FOO}` | Last filler wins |
| 21 | Three scopes fill same `{!FOO}` | Last filler wins, first two replaced |
| 22 | Only middle scope fills `{!FOO}` | Middle value stands |
| 23 | `{!FOO}` unfilled by any scope | Left in output as literal `{!FOO}` |

### Sigil behavior — `{?FOO}` first filler, strip if empty

| # | Scenario | What to verify |
|---|---|---|
| 24 | Two scopes fill same `{?FOO}` | First filler wins |
| 25 | Three scopes fill same `{?FOO}` | First filler wins |
| 26 | `{?FOO}` unfilled by any scope | Stripped from output |

### Sigil behavior — `{!?FOO}` last filler, strip if empty

| # | Scenario | What to verify |
|---|---|---|
| 27 | Two scopes fill same `{!?FOO}` | Last filler wins |
| 28 | Three scopes fill same `{!?FOO}` | Last filler wins |
| 29 | `{!?FOO}` unfilled by any scope | Stripped from output |

### Multi-branch with repos (template)

| # | Scenario | What to verify |
|---|---|---|
| 30 | Five scopes, `{FOO}` placeholder | Repo A: first matching filler. Repo B: different filler. No repo: only unscoped. |
| 31 | Five scopes, `{!FOO}` placeholder | Repo A: scope 5 wins. Repo B: scope 4 wins. No repo: scope 2 wins. |
| 32 | Different repos fill same `{!FOO}` differently | api-gateway gets api's value, web-app gets frontend's |

### Mixed placeholders in one file

| # | Scenario | What to verify |
|---|---|---|
| 33 | `{FOO}` and `{!BAR}` in same file | First-filler and last-filler independently |
| 34 | `{?FOO}` and `{!?BAR}`, neither filled | Both stripped |
| 35 | `{FOO}` and `{?BAR}`, one filled one not | `{FOO}` present, `{?BAR}` stripped |

## Cross-cutting: Mixed strategies across levels

### Pairwise strategy transitions

| # | Transition | What to verify |
|---|---|---|
| 1 | append → overwrite | Overwrite wipes the appended result |
| 2 | merge-append → overwrite | Overwrite wipes the merged result |
| 3 | template → overwrite | Overwrite wipes the filled template |
| 4 | overwrite → append | Append adds to the overwritten version |
| 5 | overwrite → merge-append | Merge-append into the overwritten version |
| 6 | append → merge-append | Merge-append into the appended result |
| 7 | merge-append → append | Append after the merge-appended result |
| 8 | template → merge-append | Filled template gets heading-level appends |
| 9 | template → append | Filled template gets content concatenated |
| 10 | append → template | Template fills placeholders in appended result |

### Multi-level mixed strategies

| # | Scenario | What to verify |
|---|---|---|
| 11 | Three levels: append → merge-append → overwrite | Overwrite at end wipes everything |
| 12 | Three levels: template → append → merge-append | Each strategy applies to accumulated result |
| 13 | Five scopes with mixed strategies and repos | Full branching with strategy changes at each level |

## Cross-cutting: General

| # | Scenario | What to verify |
|---|---|---|
| 1 | Strategy per-file, different strategies for different files | File A overwrite, file B merge-append, same config |
| 2 | No strategy specified | Default is overwrite, backwards compatible |
| 3 | Discovery tools surface strategy | `list_tools_for_repo` shows merge strategy per tool |
| 4 | Invalid strategy value | Graceful error or fallback to overwrite |
| 5 | Org prefix stripping with non-overwrite strategies | `acme/api-gateway` vs `api-gateway` same result |
