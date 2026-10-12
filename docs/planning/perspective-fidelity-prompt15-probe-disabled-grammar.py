"""Prompt 15 probe: S01b Python raw grammar on the re-emitted (mutated) request after a rejected hidden-disabled move."""
import sys,pathlib
from neural.request_knowledge import _parse_raw,_derive_active
t=pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
k,raw=_parse_raw("p1",t)
try: _derive_active(raw); print("accepted")
except Exception as e: print("S01b python grammar rejected mutated re-emitted request:", getattr(e,"code",e))
