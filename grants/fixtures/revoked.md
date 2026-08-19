---
id:          revoked
grantee:     FIXTURE
capability:  merge
scope:       nForma-AI/nForma-NEXT
granted-by:  DEV3
granted-at:  2026-08-19T20:00:00Z
expires-at:  2099-01-01T00:00:00Z
uses:        unlimited-until-expiry
revoked-at:  2026-08-19T20:00:01Z
fixture:     true
evidence:    https://github.com/nForma-AI/nForma-NEXT/issues/26
---

⛔ NOT A GRANT. The permanent known-positive for the `REVOKED` verdict.

⚠ Deliberately UNEXPIRED — `expires-at` is 2099. If this record were also expired, the
self-test could pass with the revocation check entirely unimplemented, because expiry alone
would produce the negative. **A known-positive that two independent code paths can satisfy
tests neither of them.** This one fails on revocation or it does not fail at all.
