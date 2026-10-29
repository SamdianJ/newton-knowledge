"""Rebuild unified offline knowledge; physics and downloads are never implicit."""

import argparse
import subprocess
import sys
from pathlib import Path
import json
from maintenance import verify_sources
from plan_p0 import ROOT, SRC

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--legacy-records",
        action="store_true",
        help="Also re-extract the original VBD/MuJoCo/Kamino structured records and handbooks.",
    )
    args = parser.parse_args()
    failures = verify_sources(
        SRC,
        json.loads((ROOT / "manifests/source-lock.json").read_text(encoding="utf-8")),
    )
    if failures:
        raise ValueError(
            "Pinned source changed; do not regenerate from mixed versions: "
            + str(failures[:8])
        )
    steps = (
        [
            "extract_sources.py",
            "model_and_cases.py",
            "curated.py",
            "author_docs.py",
            "extend_solvers.py",
            "build_index.py",
        ]
        if args.legacy_records
        else []
    )
    steps += ["author_platform.py"]
    if (HERE / "author_extensions.py").exists():
        steps.append("author_extensions.py")
    steps += ["build_solid_replays.py", "build_platform.py"]
    for name in steps:
        subprocess.run(
            [sys.executable, "-B", "-X", "utf8", str(HERE / name)], check=True
        )
    print(
        "Unified snapshot published. Run phase-specific acceptance checks; no physics was executed."
    )


if __name__ == "__main__":
    main()
