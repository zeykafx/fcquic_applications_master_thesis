#!/usr/bin/env python3
"""Execute mcast_eval.ipynb locally on this machine, via jupyter nbconvert.

Start it from tmux so that ssh / VS Code disconnects cannot kill the run:

    tmux new -As nb
    python run_notebook.py | tee run.log
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--notebook", type=Path, default=HERE / "mcast_eval.ipynb")
    ap.add_argument(
        "--timeout",
        type=int,
        default=-1,
        help="per-cell timeout in seconds; -1 = no timeout (experiments run for hours)",
    )
    ap.add_argument(
        "--inplace",
        action="store_true",
        help="write the outputs into the notebook instead of an executed_<name> copy",
    )
    args = ap.parse_args()

    notebook = args.notebook.resolve()
    if not notebook.is_file():
        print(f"no such notebook: {notebook}", file=sys.stderr)
        return 1

    jupyter = shutil.which("jupyter") or str(Path.home() / ".local/bin/jupyter")
    output = notebook if args.inplace else notebook.parent / f"executed_{notebook.name}"
    cmd = [
        jupyter,
        "nbconvert",
        "--to",
        "notebook",
        "--execute",
        f"--ExecutePreprocessor.timeout={args.timeout}",
    ]
    cmd += ["--inplace"] if args.inplace else ["--output", output.name]
    cmd.append(notebook.name)
    print(f"[run] cd {notebook.parent} && {' '.join(cmd)}", flush=True)

    # nbconvert must run from the notebook directory (!pip cells, relative paths)
    code = subprocess.run(cmd, cwd=notebook.parent).returncode
    print(f"[done] exit={code} -> {output}")
    return code


if __name__ == "__main__":
    sys.exit(main())
