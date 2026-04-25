"""Diagnostic script to measure memory and latency event accumulation."""

import json
import sys
from pathlib import Path

# Add trainer to path
sys.path.insert(0, str(Path(__file__).parent / "trainer" / "src"))

from neural.config import load_config, resolve_process_spec
from neural.env_client import SimCoreClient
from neural.runtime import load_runtime_options, choose_timeout, MINIMAL_STEP_OPTIONS


def diagnose_accumulation(config_path: str, num_cycles: int = 100) -> None:
    """Run diagnostic cycles to show memory accumulation."""
    config = load_config(config_path)
    command, cwd = resolve_process_spec(config)
    runtime = load_runtime_options(config)

    client = SimCoreClient(command, cwd)

    print(f"Starting diagnostic: {num_cycles} cycles, {runtime.num_envs} envs")
    print("=" * 80)

    max_events = 0
    try:
        for cycle in range(num_cycles):
            # Create environment
            env_id = client.create_env(
                format_name="gen9randombattle",
                players={"p1": {"controller": "external"}, "p2": {"controller": "random"}},
                timeout_sec=choose_timeout(runtime, "create_env"),
            )

            # Reset
            result = client.reset(
                env_id,
                options=MINIMAL_STEP_OPTIONS,
                timeout_sec=choose_timeout(runtime, "reset"),
            )

            # Take a few steps
            for step_idx in range(3):
                if result.get("terminated"):
                    break
                request = result.get("requests", {}).get("p1")
                if not request:
                    break
                actions = request.get("legal_actions", {}).get("actions", [])
                if not actions or not actions[0]:
                    break
                action = actions[0]["choice"]
                result = client.step(
                    env_id,
                    {"p1": action},
                    options=MINIMAL_STEP_OPTIONS,
                    timeout_sec=choose_timeout(runtime, "step"),
                )

            # Close without taking latency events explicitly
            # (to show if drain in close_slots is working)
            client.close_env(env_id, timeout_sec=choose_timeout(runtime, "close_env"))

            # Drain latency events for this closed environment (like close_slots does)
            client.take_latency_events(env_id)

            # Measure accumulation
            latency_count = len(client._latency_events)
            max_events = max(max_events, latency_count)
            pending_count = len(client._pending)

            if cycle % 20 == 0:
                print(
                    f"Cycle {cycle:3d}: latency_events={latency_count:6d} (max={max_events:6d}), pending={pending_count:3d}"
                )

            # Print warning if accumulating too much
            if latency_count > 500:
                print(f"⚠️  WARNING: Latency events accumulated to {latency_count}!")
                print("   This indicates potential memory leak if events not being drained.")
                break

    except Exception as e:
        print(f"Error during cycle {cycle}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()
        print("=" * 80)
        print(f"Final state: latency_events={len(client._latency_events)}, pending={len(client._pending)}")
        print(f"Peak latency events: {max_events}")
        if max_events < 100:
            print("✅ Memory leak is FIXED - latency events stayed bounded!")
        else:
            print("⚠️  Warning: latency events grew significantly")


if __name__ == "__main__":
    config = "./configs/gen9randombattle_eval.windows.eval1000-stable.yaml"
    diagnose_accumulation(config, num_cycles=100)
