import json
from pathlib import Path
from unittest.mock import patch

import pytest

from neural.version_profile import (
    installed_native_profile, NATIVE_ENGINE_COMMIT, NATIVE_ENGINE_INTEGRITY, ReaderProfileError,
)


def test_installed_native_commit_and_integrity():
    profile = installed_native_profile()
    assert profile['engine_commit'] == NATIVE_ENGINE_COMMIT
    assert profile['integrity'] == NATIVE_ENGINE_INTEGRITY


def test_reject_npm_same_version():
    original = Path.read_text

    def read(path, *args, **kwargs):
        text = original(path, *args, **kwargs)
        if path.as_posix().endswith('/pokemon-showdown/package.json'):
            data = json.loads(text)
            data.pop('engine_commit')
            data['gitHead'] = '739a5e1fee432ad80ff7136d70cca993be358b59'
            return json.dumps(data)
        return text

    with patch.object(Path, 'read_text', read), pytest.raises(ReaderProfileError, match='installed-runtime-mismatch'):
        installed_native_profile()


def test_reject_installed_content_with_valid_metadata():
    original = Path.read_bytes

    def read(path):
        data = original(path)
        return data + b'\n// altered' if path.as_posix().endswith('/pokemon-showdown/dist/sim/battle.js') else data

    with patch.object(Path, 'read_bytes', read), pytest.raises(ReaderProfileError, match='installed-runtime-content'):
        installed_native_profile()
