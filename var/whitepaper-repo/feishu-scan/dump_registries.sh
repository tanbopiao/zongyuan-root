#!/usr/bin/env bash
set -u
cd /opt/ZONGYUAN-ROOT/ZONGYUAN-ROOT/feishu-scan
mkdir -p registry_ndjson
B1="WBQNbr4tca2neIs23X8coL4jnch"
B2="IKIdb7KLDapblXsvVDIcs8FLnLa"
# base1 tables
declare -A T1=(
  [tblCAOoZWlXJaES2]="snap_registry"
  [tblupyiEi8wxJJzv]="ip_asset_lib"
  [tblzSekdjIBEtSKY]="feishu_resource_index"
  [tblwjUrcuuHg3LP9]="meta_rules"
  [tblzUfFmQ3uZ9fUl]="meta_laws"
  [tbl6JcYtRJx21aBs]="subdomain_isolation"
  [tblj6UtrvvNYbLpi]="arch_breakpoints"
  [tblOx2talJkurh5m]="data_table"
)
for tid in "${!T1[@]}"; do
  name="${T1[$tid]}"
  lark-cli base +record-list --base-token "$B1" --table-id "$tid" --limit 2000 \
    --format ndjson --output "registry_ndjson/B1_${name}.ndjson" --overwrite --as user >/dev/null 2>&1
  echo "B1 $name -> $(wc -l < registry_ndjson/B1_${name}.ndjson 2>/dev/null || echo 0) lines"
done
# base2 single table
lark-cli base +record-list --base-token "$B2" --table-id tbl6bt6EuQrgkj6b --limit 2000 \
  --format ndjson --output "registry_ndjson/B2_evolution_archive.ndjson" --overwrite --as user >/dev/null 2>&1
echo "B2 evolution -> $(wc -l < registry_ndjson/B2_evolution_archive.ndjson 2>/dev/null || echo 0) lines"
