import re, yaml
from pathlib import Path
_GH_SHELL = re.compile(r"(?:^|[\s;&|(`$])gh\s+[a-z]", re.MULTILINE)
_GH_ARGV  = re.compile(r"""[\[(]\s*["']gh["']\s*,""")
for f, jname, sname in [(".github/workflows/k8s-monitoring-apply.yml","diff-and-gate","kubectl diff (review surface)"),
                        (".github/workflows/nightly-full-e2e.yml","full-e2e-tests","Setup Instructions")]:
    wf = yaml.safe_load(Path(f).read_text())
    for st in wf["jobs"][jname]["steps"]:
        if (st.get("name") or "") == sname:
            run = st.get("run") or ""
            print(f"######## {f} :: {sname}")
            for i, line in enumerate(run.splitlines(), 1):
                if _GH_SHELL.search(line) or _GH_ARGV.search(line):
                    print(f"  hit L{i}: {line}")
            print()
