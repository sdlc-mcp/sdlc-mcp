# Merge Strategy Test Matrix

## Conventions

- Strategy is configured per-scope in config YAML (e.g., `strategy: append`)
- Default strategy is `overwrite` (backwards compatible)
- Scopes can declare `vars` (rendered via Jinja2 after merge resolution, independent of strategy)

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

## Vars (Jinja2 rendering)

| # | Scenario | What to verify |
|---|---|---|
| 1 | Basic `{{ var }}` substitution | Var replaced in content |
| 2 | Multiple vars | Each replaced correctly |
| 3 | `default()` filter, no var provided | Default value used |
| 4 | `default()` filter, var provided | Provided value overrides default |
| 5 | Undefined var, no default | Renders as empty string |
| 6 | Vars apply to all files | All content items rendered |
| 7 | Different repos get different vars | Per-repo scope vars resolve correctly |
| 8 | No vars in hierarchy | Content passes through unchanged |
| 9 | Vars accumulate across scopes | Multiple scopes contribute vars |
| 10 | Later vars override earlier | Most specific scope wins |
| 11 | `{% if var %}` conditional, var present | Conditional block rendered |
| 12 | `{% if var %}` conditional, var absent | Conditional block omitted |
| 13 | Vars with append strategy | Vars render after append merging |
| 14 | Vars with merge-append strategy | Vars render after merge-append merging |

## Cross-cutting: Mixed strategies across levels

### Pairwise strategy transitions

| # | Transition | What to verify |
|---|---|---|
| 1 | append → overwrite | Overwrite wipes the appended result |
| 2 | merge-append → overwrite | Overwrite wipes the merged result |
| 3 | overwrite → append | Append adds to the overwritten version |
| 4 | overwrite → merge-append | Merge-append into the overwritten version |
| 5 | append → merge-append | Merge-append into the appended result |
| 6 | merge-append → append | Append after the merge-appended result |

### Multi-level mixed strategies

| # | Scenario | What to verify |
|---|---|---|
| 7 | Three levels: append → merge-append → overwrite | Overwrite at end wipes everything |

## Cross-cutting: General

| # | Scenario | What to verify |
|---|---|---|
| 1 | Strategy per-file, different strategies for different files | File A overwrite, file B merge-append, same config |
| 2 | No strategy specified | Default is overwrite, backwards compatible |
| 3 | Discovery tools surface strategy | `list_tools_for_repo` shows merge strategy per tool |
| 4 | Invalid strategy value | Graceful error or fallback to overwrite |
| 5 | Org prefix stripping with non-overwrite strategies | `acme/api-gateway` vs `api-gateway` same result |
