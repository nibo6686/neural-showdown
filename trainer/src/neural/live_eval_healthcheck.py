import argparse
import json

from .live_eval_server import live_eval_diagnostics


def main() -> None:
    parser = argparse.ArgumentParser(description="Report live evaluator import, model, port, and damage-engine health.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--skip-rpc", action="store_true", help="Do not attempt the configured sim-core damage RPC.")
    args = parser.parse_args()

    diagnostics = live_eval_diagnostics(
        check_rpc=not args.skip_rpc,
        check_damage=True,
        check_port=True,
        port=args.port,
    )
    print("LIVE_EVAL_HEALTHCHECK:")
    print(json.dumps(diagnostics, indent=2, default=str))


if __name__ == "__main__":
    main()
