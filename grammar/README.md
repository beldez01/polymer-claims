# polymer-grammar

The Polymer Claims **v1.3 grammar** — the next-generation claim IR derived from the
foundations spec (in git history; per-feature design docs were consolidated out of the tree 2026-06-29).

**This package is intentionally isolated from `formalclaim/` (the live v1.2 IR).** It does
not import from, and is not imported by, `polymer_formalclaim`. The v1.2 schema stays
canonical and untouched while v1.3 is built and validated here. A bridge/migration, if
ever needed, will be an explicit, separately-reviewed module — never an implicit import.
