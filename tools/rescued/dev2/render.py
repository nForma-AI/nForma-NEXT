import importlib.util, sys, logging, io
root = sys.argv[1]
sys.path.insert(0, root + "/scripts")
import ci_chronic_skip_guard as g
runs = [{"id": i, "created_at": f"2026-07-14T0{i}:00:00Z"} for i in (1, 2, 3)]
jobs = [{"name": n, "conclusion": "skipped"} for n in
        ("C0: Pod Recovery (gcp)", "C0: Pod Recovery (dfc)", "C0: Pod Recovery (lat)")]
buf = io.StringIO()
h = logging.StreamHandler(buf); logging.getLogger("ci_chronic_skip_guard").addHandler(h)
logging.getLogger("ci_chronic_skip_guard").setLevel(logging.INFO)
code, lines = g.run_guard(repo="o/r", runs_fetcher=lambda: runs, jobs_fetcher=lambda r: jobs, enforcing=False)
sys.stdout.write("SUMMARY\n" + "\n".join(lines) + "\nLOGS\n" + buf.getvalue())
