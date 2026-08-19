---
id:          live
grantee:     FIXTURE
capability:  merge
scope:       nForma-AI/nForma-NEXT
granted-by:  DEV3
granted-at:  2026-08-19T20:00:00Z
expires-at:  2099-01-01T00:00:00Z
uses:        unlimited-until-expiry
revoked-at:
fixture:     true
evidence:    https://github.com/nForma-AI/nForma-NEXT/issues/26
---

⛔ NOT A GRANT. This authorizes nothing and cannot — `fixture: true` records are excluded
from every real query by `tools/grant-check.py`, which is itself one of the things the
self-test proves.

It exists because of #26: **a control ships with its known-positive, and the known-positive
must exist in the REPAIRED state.** The `LIVE` verdict needs an input that produces it
forever. A real grant cannot serve — every real grant expires by construction, so a
self-test anchored to one would go silent the moment it lapsed, which is #26's sharp
subtype exactly.

⚠ The far-future `expires-at` does not make this a standing grant. A standing grant is one
that can authorize something; this can never authorize anything. `expires-at` is required
here only so the parser sees a well-formed record — the field's rule is not weakened.
