import unittest

from neural.latency import summarize_rpc_events, summarize_samples


class LatencySummaryTest(unittest.TestCase):
    def test_summarize_samples_handles_percentiles(self):
        summary = summarize_samples([1.0, 2.0, 3.0, 4.0])
        self.assertEqual(summary["count"], 4)
        self.assertAlmostEqual(summary["mean_ms"], 2.5)
        self.assertAlmostEqual(summary["p50_ms"], 2.5)
        self.assertAlmostEqual(summary["p95_ms"], 3.85)
        self.assertAlmostEqual(summary["max_ms"], 4.0)

    def test_summarize_rpc_events_groups_by_request_type(self):
        report = summarize_rpc_events(
            [
                {
                    "request_type": "step",
                    "round_trip_ms": 12.0,
                    "queue_wait_ms": 1.0,
                    "server_elapsed_ms": 8.0,
                    "transport_overhead_ms": 3.0,
                },
                {
                    "request_type": "step",
                    "round_trip_ms": 20.0,
                    "queue_wait_ms": 2.0,
                    "server_elapsed_ms": 14.0,
                    "transport_overhead_ms": 4.0,
                },
                {
                    "request_type": "reset",
                    "round_trip_ms": 50.0,
                    "queue_wait_ms": 5.0,
                    "server_elapsed_ms": 40.0,
                    "transport_overhead_ms": 5.0,
                },
            ]
        )

        self.assertEqual(report["count"], 3)
        self.assertEqual(report["by_request_type"]["step"]["count"], 2)
        self.assertAlmostEqual(
            report["by_request_type"]["step"]["metrics"]["round_trip_ms"]["mean_ms"],
            16.0,
        )
        self.assertEqual(report["hotspots"][0]["request_type"], "reset")


if __name__ == "__main__":
    unittest.main()
