#!/usr/bin/env bash
# 一键自检：对 examples/ 实际跑通 抽取 -> 建图 -> 指标/归类/快照
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$HERE/examples/out"
rm -rf "$OUT"
mkdir -p "$OUT"

python3 "$HERE/scripts/extract_triples.py" \
  --docs "$HERE/examples/sample-docs" \
  --dict "$HERE/examples/entity-dict.json" \
  --out "$OUT/triples.jsonl" \
  --did "DID-BR-000002" > "$OUT/extract.log"

python3 "$HERE/scripts/build_graph.py" \
  --triples "$OUT/triples.jsonl" \
  --dict "$HERE/examples/entity-dict.json" \
  --outdir "$OUT" \
  --did "DID-BR-000002" > "$OUT/build.log"

# 二次跑：带快照做版本升级判定（图应无变化 -> unchanged）
python3 "$HERE/scripts/build_graph.py" \
  --triples "$OUT/triples.jsonl" \
  --dict "$HERE/examples/entity-dict.json" \
  --outdir "$OUT" \
  --prev-snapshot "$OUT/graph-snapshot.json" \
  --did "DID-BR-000002" > "$OUT/build2.log"

echo "=== extract summary ==="
python3 -c "import json;d=json.load(open('$OUT/extract.log'));print('triples:',d['triples_extracted'],'docs:',d['docs_scanned'])"
echo "=== build summary ==="
python3 -c "import json;d=json.load(open('$OUT/build.log'));print('nodes:',d['metrics']['node_count'],'edges:',d['metrics']['edge_count'],'density:',d['metrics']['density'],'components:',d['metrics']['connected_components'],'isolated:',d['metrics']['isolated_count'],'version:',d['graph_version'])"
echo "=== rebuild (unchanged check) ==="
python3 -c "import json;d=json.load(open('$OUT/build2.log'));print('version_bump:',d['version_bump'])"
echo "SELFCHECK OK"
