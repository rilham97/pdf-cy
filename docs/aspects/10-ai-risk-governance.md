# 10 AI Risk

Payload key: `sections.ai_risk_governance` · Module: [s10_ai_risk_governance.py](../../cyberrank_report/sections/s10_ai_risk_governance.py) · Shared rules: [README](README.md)

Demerit rule H. Section renamed from *"AI Issues"* / *"AI risk and governance"* to **AI Risk** (owner decision 2026-11-24).

Supports two payload shapes:
- **Structured AI Risk payload (Concept B, owner-approved 2026-11-24):** mirrors the new customer AI Risk view with `risk_level`, `use_of_ai`, `capabilities[]`, optional `ai_providers[]`, `high_risk_uses[]` (EU AI Act Annex III), and `governance` (`ai_policy`, `iso_42001`). Empty/absent optional sub-sections are automatically omitted so there are no empty boxes or repetitive text.
- **Legacy `narrative_observation` payload:** preserved verbatim for older payloads and RF-04 context-only mode when `state` is `not_assessed` / `not_applicable` / `unavailable`.

---

## Layout (top to bottom — Structured AI Risk / Concept B)

1. Eyebrow `10 · ASSESSMENT DETAILS`, H1 `title` or `"AI Risk"` (brain icon), `intro_source`.
2. State chip + verdict (`summary`, or generated fallback `verdict()` when absent).
3. State card (no-result states, `partial`, `pending_review`; skipped on `clear` when no custom reason is sent so there is no repetitive card).
4. **3-column Posture Strip:**
   - Tile 1: **`AI risk level`** (`Low | Medium | High | Critical`) + `Scale: Low · Medium · High · Critical`
   - Tile 2: **`Use of AI`** (`Unlikely | Possible | Likely | Almost certain`) + `Scale: Unlikely · Possible · Likely · Almost certain`
   - Tile 3: **`EU AI Act high-risk`** (clause e.g. `Annex III 4(a)` when detected, or `None found`)
5. **H2 `Observed AI use`** *(omitted completely if none of quote, capabilities, or AI providers exist)* — `key_value_list` in exact order:
   1. `Public evidence` (verbatim quote + clickable URL) *(only if quote present)*
   2. `Observed capabilities` (bordered sapphire tags) *(only if `capabilities[]` non-empty)*
   3. `AI providers` (bordered navy tags) *(only if `ai_providers[]` non-empty — combined here, no separate section, no AI models)*
6. **H2 `High-risk use · EU AI Act`** *(omitted completely when `high_risk_uses[]` is empty)* — orange-accented neutral card showing each category, `Annex III …` clause, verbatim evidence quote, and clickable source URL.
7. **H2 `AI governance`** *(shown as a 3-column table when `Use of AI != Unlikely` OR at least one control is found)*: `Control · Status · Public evidence` (`AI policy`, `ISO 42001 certificate` with clickable URLs).
   - **When `Use of AI == Unlikely` AND neither governance control is found:** no governance table and no repetitive card — prints one concise check-scope note below the posture strip.
8. Scope note at bottom.

---

## From the system (dynamic payload fields — Structured AI Risk)

> Both `snake_case` and `camelCase` field aliases are accepted.

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `title` | H1 + Contents + Section 01 label | `"AI Risk"` |
| `intro_source` | Intro under H1 | Omitted |
| `state` | Chip, card, body/no-body (`findings` or `clear` for assessed; `not_assessed`/`unavailable` + `reason_code` for no-result) | Validation error (exit 1) |
| `summary` | Opener verdict, verbatim | Generated automatically by `verdict()` |
| `risk_level` (alias `riskLevel`) | Posture Tile 1 (`Low`, `Medium`, `High`, `Critical`); Section 01 result line (`<Level> AI risk`) | Defaults to `"Low"` |
| `use_of_ai.level` (alias `useOfAi.level`) | Posture Tile 2 (`Unlikely`, `Possible`, `Likely`, `Almost certain`); controls whether `AI governance` table expands or collapses | Defaults to `"Unlikely"` |
| `use_of_ai.quote` (aliases `evidence_quote`, `evidenceQuote`) | First row (`Public evidence`) in `Observed AI use`, quoted verbatim | Row omitted |
| `use_of_ai.source_url` (aliases `sourceUrl`, `url`) | Clickable monospace URL under the quote in `Public evidence` | URL omitted |
| `capabilities[]` (aliases `capability_tags`, `capabilityTags`) | Second row (`Observed capabilities`) in `Observed AI use` as sapphire tags (e.g. `LLM text generation`, `Image, audio or video generation`, `Biometric identification`, `Emotion recognition`, `Scoring or ranking people`) | Row omitted |
| `ai_providers[]` (alias `aiProviders[]`) | Third row (`AI providers`) in `Observed AI use` as navy tags (e.g. `OpenAI`, `Anthropic`). Optional — backend stores providers only, not models. | Row omitted |
| `high_risk_uses[]` (alias `highRiskUses[]`) | Dedicated `High-risk use · EU AI Act` card + Tile 3 clause (`high_risk_uses[0].clause`) + Section 01 qualifier | Entire `High-risk use` section omitted; Tile 3 prints `"None found"` |
| `high_risk_uses[].category` (alias `title`) | Bold card header (e.g. `Recruitment, screening & candidate ranking`) | `"EU AI Act high-risk use"` |
| `high_risk_uses[].clause` (aliases `reference`, `annex_clause`) | Right-aligned amber clause tag + Tile 3 value (e.g. `Annex III 4(a)`) | `"Annex III"` |
| `high_risk_uses[].quote` / `source_url` | Verbatim quote + clickable monospace URL inside the high-risk card | Omitted |
| `governance.ai_policy` (alias `aiPolicy`) | Row 1 of `AI governance`: `{found: bool, label?, note?, url?}` | Treated as `found: false` (`"Not found on the vendor's website"`) |
| `governance.iso_42001` (alias `iso42001`) | Row 2 of `AI governance`: `{found: bool, label?, note?, url?}` (e.g. `note: "Registry listing"`, `url: "https://..."`) | Treated as `found: false` (`"Not found on the vendor's website or in certification body registers"`) |

*(Legacy `narrative_observation` fields remain supported when none of the structured fields above are present — see `s10_ai_risk_governance.py:_observations`.)*

---

## Hardcoded in the generator (static text & labels)

| Exact static text / label | Where it prints |
|---|---|
| `"AI Risk"` | Default H1 / section title |
| `"AI risk level"`, `"Scale: Low · Medium · High · Critical"` | Posture Tile 1 label & scale caption |
| `"Use of AI"`, `"Scale: Unlikely · Possible · Likely · Almost certain"` | Posture Tile 2 label & scale caption |
| `"EU AI Act high-risk detected"` / `"EU AI Act high-risk (Annex III)"`, `"None found"` | Posture Tile 3 label & empty value |
| `"Observed AI use"` | H2 (only when at least one of quote / capabilities / providers is present) |
| `"Public evidence"`, `"Observed capabilities"`, `"AI providers"` | Fixed row labels & order in `Observed AI use` |
| `"High-risk use · EU AI Act"` | H2 (only when `high_risk_uses[]` is non-empty) |
| `"AI governance"`, `"Control"`, `"Status"`, `"Public evidence"` | H2 and table headers |
| `"Found"`, `"Not found"` | Status chips in `AI governance` table |
| `"AI policy"`, `"AI policy published"`, `"ISO 42001 certificate"` | Default governance control labels |
| `"Not found on the vendor's website"`, `"Not found on the vendor's website or in certification body registers"` | Default missing evidence notes in `AI governance` |
| `"Scope note: Assessment is based on publicly accessible pages and certification registers; internal or private AI tools are not visible to external checks."` | Bottom note when AI governance table is shown |
| `"Checked public website pages and certification registers: no AI capabilities, AI providers, AI policy, ISO 42001 certificate, or EU AI Act Annex III high-risk use was found. Internal or private AI tools are outside external visibility."` | Concise single note in the No AI Usage (`Unlikely` + no governance) case |
| `"Run the AI risk module for this organisation. It evaluates observed AI use, capabilities, EU AI Act high-risk classification and public AI governance controls."` | Default `not_assessed` card next step |

---

## Conditional rules (if / else)

| Condition | What prints |
|---|---|
| Any structured AI Risk key present (`risk_level`, `use_of_ai`, `capabilities`, `ai_providers`, `high_risk_uses`, `governance`) | **Structured Concept B layout** (`_build_structured`). |
| None of the structured keys present | **Legacy `narrative_observation` layout** (backward-compatible). |
| `use_of_ai.quote`, `capabilities[]`, and `ai_providers[]` all empty | `Observed AI use` heading & block completely omitted. |
| `ai_providers[]` empty | `AI providers` row omitted from `Observed AI use`. |
| `high_risk_uses[]` empty | `High-risk use · EU AI Act` heading & card completely omitted; Tile 3 shows `"None found"`. |
| `use_of_ai.level == "Unlikely"` AND both `ai_policy.found` and `iso_42001.found` are `false` | `AI governance` table omitted AND default `clear` state card skipped; prints only the 3-tile posture strip + 1 concise check-scope note. |
| `use_of_ai.level != "Unlikely"` OR at least one governance control is `found: true` | Full `AI governance` table (both rows: `AI policy` and `ISO 42001 certificate`) prints, followed by scope note. |
| `state` in `not_assessed` / `not_applicable` / `unavailable` | State card only (plus legacy context block if `narrative_observation` is present). |

---

## Computed by the generator

| Value | Rule |
|---|---|
| Fallback `verdict()` | Composed from `risk_level`, `use_of_ai.level`, `high_risk_uses[].clause`, and found governance controls when `summary` is absent. |
| Section 01 Executive overview result line (`s01_executive_overview.py:_ai_risk`) | Structured payload → `<Risk level> AI risk · <Annex III clause>` (if high-risk) or `<Risk level> AI risk · <Use of AI> AI use`. Legacy payload → `N AI risk finding(s)`. |
| URL wrapping | `tech_lines` breaks long registry/evidence URLs cleanly at `/ . - _ ? = &` without mid-word breaks. |

---

## Example JSON payloads (for backend devs)

### Case A — AI Detected (with High-Risk Use + Providers + Governance)
```json
"ai_risk_governance": {
  "title": "AI Risk",
  "state": "findings",
  "risk_level": "Medium",
  "use_of_ai": {
    "level": "Almost certain",
    "quote": "The IDE mirrors a modern developer setup, with inline assistance and a chat panel.",
    "source_url": "https://www.example.com/products/interview"
  },
  "capabilities": ["LLM text generation", "Scoring or ranking people"],
  "ai_providers": ["OpenAI", "Anthropic"],
  "high_risk_uses": [
    {
      "category": "Recruitment, screening & candidate ranking",
      "clause": "Annex III 4(a)",
      "quote": "Screening candidates helps rapidly and accurately identify candidate skills.",
      "source_url": "https://www.example.com/products/screen"
    }
  ],
  "governance": {
    "ai_policy": {
      "found": true,
      "url": "https://www.example.com/about-us/responsible-ai"
    },
    "iso_42001": {
      "found": false
    }
  }
}
```

### Case B — No AI Usage (`Unlikely`, no evidence)
```json
"ai_risk_governance": {
  "title": "AI Risk",
  "state": "clear",
  "risk_level": "Low",
  "use_of_ai": { "level": "Unlikely" },
  "capabilities": [],
  "ai_providers": [],
  "high_risk_uses": [],
  "governance": {
    "ai_policy": { "found": false },
    "iso_42001": { "found": false }
  }
}
```

## Backend checklist

- **Required:** `state` (`findings` when AI signals/risks found, `clear` when `Unlikely` with no findings, `not_assessed`/`unavailable` + `reason_code` when module did not run).
- **Structured AI Risk fields:** send `risk_level`, `use_of_ai`, `capabilities[]`, `ai_providers[]` (empty list `[]` if none — never send fake values), `high_risk_uses[]` (`[]` if none), and `governance.{ai_policy, iso_42001}`.
- **Omit `summary` if you want auto-generated verdict:** or send a custom one-sentence `summary` to override it verbatim.
- **No `AI issues` metric needed:** Section 01 reads `risk_level`, `use_of_ai.level`, and `high_risk_uses[]` directly.
- **No AI models field:** only `ai_providers[]` is rendered.
