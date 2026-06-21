import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TRAINER_SRC = REPO_ROOT / "trainer" / "src"
if str(TRAINER_SRC) not in sys.path:
    sys.path.insert(0, str(TRAINER_SRC))

from neural.randbats_meta_prior_audit import audit_manifest, render_markdown


DEFAULT_REPORT = (
    REPO_ROOT
    / "artifacts"
    / "training_plan"
    / "randbats_meta_prior_public_prefix_audit.md"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--prior-source", type=Path, required=True)
    parser.add_argument("--split", default="test")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    manifest = args.manifest.resolve()
    prior_source = args.prior_source.resolve()
    summary = audit_manifest(
        manifest_path=manifest,
        prior_source_path=prior_source,
        split=args.split,
        limit=args.limit,
    )
    command = (
        "python scripts/audit_randbats_meta_prior_public_prefixes.py "
        f"--manifest {args.manifest} --prior-source {args.prior_source} "
        f"--split {args.split} --limit {args.limit}"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_markdown(summary, command), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"report={args.output}")


if __name__ == "__main__":
    main()
