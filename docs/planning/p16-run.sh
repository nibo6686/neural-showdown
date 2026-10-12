cd /c/Users/cloud/Downloads/neural/final/sim-core
P=../docs/planning/perspective-fidelity-prompt16
node --test --test-isolation=none dist/tests/env_manager.test.js dist/tests/forced_switch.test.js dist/tests/settling.test.js dist/tests/revival.test.js dist/tests/transition.test.js dist/tests/pipeline_integration.test.js dist/tests/belief_fork.test.js dist/tests/state_extractor.test.js dist/tests/record_identity.test.js dist/tests/action_codec.test.js dist/tests/observable_state.test.js dist/tests/pipeline_utf8_transport.test.js > $P-ts-core.log 2>&1
node --test --test-isolation=none --test-skip-pattern='source turn-limit tie retains a complete two-perspective chain and bulk-publishes every actor row' dist/tests/pipeline_episode.test.js dist/tests/pipeline_episode_faithful.test.js dist/tests/pipeline_episode_stop_repair.test.js > $P-ts-episode.log 2>&1
for f in request_knowledge request_knowledge_characterization perspective_knowledge perspective_knowledge_source perspective_field_semantics simulator_coverage; do echo "== $f" ; node --test --test-isolation=none dist/tests/$f.test.js 2>&1 | grep "^ℹ \(tests\|pass\|fail\)" | tr '\n' ' '; echo; done > $P-ts-knowledge.log 2>&1
cd ..
D:/Anaconda/envs/neuralgpu/python.exe -m unittest trainer.tests.test_pipeline_record trainer.tests.test_perspective_knowledge trainer.tests.test_perspective_knowledge_source trainer.tests.test_request_knowledge trainer.tests.test_request_knowledge_characterization > $P-python.log 2>&1
PYTHONPATH="C:/Users/cloud/Downloads/neural/final/trainer/src;C:/Users/cloud/Downloads/neural/final/trainer/tests" D:/Anaconda/envs/neuralgpu/python.exe -m unittest trainer.tests.test_perspective_field_semantics > $P-python-field.log 2>&1
echo done > $P-run.done
