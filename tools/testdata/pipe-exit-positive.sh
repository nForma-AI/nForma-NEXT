#!/usr/bin/env bash
# KNOWN-POSITIVE fixture for tools/pipe-exit-scan.py. Not run; scanned.
#
# ⛔ Every line below is a REAL idiom from a real incident in this repo, not an
# invented shape. A scanner whose failing path has never fired is not a scanner,
# and a fixture invented to match the regex proves only that the regex matches
# itself.
#
# ⚠ These three comment lines mention `${PIPESTATUS[0]}` and `| tail; echo $?`
# deliberately. They MUST NOT be reported: a comment is a mention. If the scanner
# ever fires on this block, comment-stripping has regressed.

# instance 1 — DEVOPS. Read tail's status; nearly filed a working validator as
# an entrypoint that cannot exit non-zero.
python3 scripts/validate-recipe.py | tail -6; echo "exit=$?"

# instance 2 — TEAMLEAD. Empty in zsh. Printed `exit=` having measured nothing.
python3 tools/fleet-identity.py | head -20; echo "exit=${PIPESTATUS[0]}"

# instance 3 — DEV2, in a role warned about it in the same message.
python3 tool.py | sed -n '1,5p'; echo "EXIT=${PIPESTATUS[0]}"

# the correct form, which must NOT be reported
python3 scripts/validate-recipe.py > /tmp/out 2>&1
echo "exit=$?"
