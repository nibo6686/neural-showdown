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
    smoke = diagnostics.get("damage_engine_smoke") if isinstance(diagnostics.get("damage_engine_smoke"), dict) else {}
    rpc = diagnostics.get("sim_core_damage_rpc") if isinstance(diagnostics.get("sim_core_damage_rpc"), dict) else {}
    checks = {
        "checkpoints_present": bool(
            ((diagnostics.get("selected_checkpoints") or {}).get("value") or {}).get("exists")
            and ((diagnostics.get("selected_checkpoints") or {}).get("action_ranker") or {}).get("exists")
        ),
        "damage_smoke": bool(smoke.get("ok")),
        "sim_core_reachable_or_unconfigured": bool(rpc.get("reachable") or not rpc.get("configured")),
    }
    summary = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}
    print("LIVE_EVAL_HEALTHCHECK_SUMMARY:")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
