# Tesla BLE Protobuf Files

This directory contains the Python protobuf modules (`*_pb2.py` / `*_pb2.pyi`)
used at runtime by the integration.

## Source & license

These modules are generated from the `.proto` definitions in Tesla's official,
open-source vehicle command SDK:

- **Upstream:** https://github.com/teslamotors/vehicle-command
  (`pkg/protocol/protobuf/*.proto`)
- **License:** Apache License 2.0 (compatible with this project's GPLv3 — see the
  upstream [LICENSE](https://github.com/teslamotors/vehicle-command/blob/main/LICENSE)).

The `.proto` sources are intentionally **not vendored** here — fetch them from the
upstream repo when (re)generating. The only modification applied to the generated
output is converting absolute imports to relative imports so the modules import
cleanly as a package (`from . import xxx_pb2`).

## Regenerating

```bash
# 1. Fetch the upstream .proto files (pin to a tag/commit for reproducibility)
mkdir -p /tmp/tesla_proto && cd /tmp/tesla_proto
base="https://raw.githubusercontent.com/teslamotors/vehicle-command/main/pkg/protocol/protobuf"
for f in car_server common errors keys managed_charging signatures \
         universal_message vcsec vehicle; do
  curl -fsSL "$base/$f.proto" -o "$f.proto"
done

# 2. Generate Python modules + type stubs
protoc -I /tmp/tesla_proto \
  --python_out=/path/to/tesla_ble/proto \
  --pyi_out=/path/to/tesla_ble/proto \
  /tmp/tesla_proto/*.proto

# 3. Convert absolute imports to relative imports (so the package self-imports)
cd /path/to/tesla_ble/proto
python3 - <<'PY'
import os, re
pat = re.compile(r'^import (\w+_pb2) as (\w+__pb2)$', re.MULTILINE)
for fn in (f for f in os.listdir('.') if f.endswith('_pb2.py')):
    s = open(fn).read()
    new = pat.sub(r'from . import \1 as \2', s)
    if new != s:
        open(fn, 'w').write(new)
        print('updated', fn)
PY
```

## Files

`car_server_pb2` · `common_pb2` · `errors_pb2` · `keys_pb2` ·
`managed_charging_pb2` · `signatures_pb2` · `universal_message_pb2` ·
`vcsec_pb2` · `vehicle_pb2`
