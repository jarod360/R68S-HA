#!/usr/bin/env bash
set -euo pipefail

assets_dir=$1
[[ "$HAOS_VERSION" =~ ^[0-9]+\.[0-9]+(\.[0-9]+)?$ ]]
[[ "$HAOS_SHA" =~ ^[0-9a-f]{40}$ && "$GITHUB_SHA" =~ ^[0-9a-f]{40}$ ]]
tag="r68s-$HAOS_VERSION"
bundle="haos_r68s-$HAOS_VERSION.raucb"
dtb=R68S-DTB-SHA256
test -s "$assets_dir/$bundle"
[[ $(wc -l < "$assets_dir/$dtb") -eq 1 ]]
grep -Eq '^[0-9a-f]{64}  rk3568-fastrhino-r68s\.dtb$' "$assets_dir/$dtb"

endpoint="repos/$GITHUB_REPOSITORY/releases"
# The list endpoint includes drafts for the release job's write token.
release=$(gh api --paginate --slurp "$endpoint?per_page=100" |
  jq -c --arg tag "$tag" '[.[][] | select(.tag_name == $tag)] |
    if length > 1 then error("more than one matching release") else .[0] // empty end')

if [[ -n "$release" ]] && jq -e '.draft == false' <<<"$release" >/dev/null; then
  echo "$tag 已发布，跳过创建草稿。"
  exit 0
fi

if [[ -z "$release" ]]; then
  notes=$(cat <<EOF
Home Assistant OS $HAOS_VERSION 的 R68S 签名 OTA 候选包。

- 官方 HAOS 源码：$HAOS_SHA
- R68S 适配提交：$GITHUB_SHA
- 构建记录：$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID
- 已通过签名、机型、A/B 分区和槽内 DTB 检查。已迁移设备从内核槽加载对应的 DTB。发布为 Latest 前请完成实机验收。
EOF
)
  release=$(gh api --method POST "$endpoint" -f tag_name="$tag" \
    -f target_commitish="$GITHUB_SHA" -f name="R68S HAOS $HAOS_VERSION" \
    -f body="$notes" -F draft=true -f make_latest=false)
fi

jq -e --arg sha "$GITHUB_SHA" '.draft and .target_commitish == $sha' <<<"$release" >/dev/null ||
  { echo "::error::同版本草稿来自其他提交，请先审核现有草稿。"; exit 1; }
id=$(jq -er '.id | numbers' <<<"$release")
upload="https://uploads.github.com/repos/$GITHUB_REPOSITORY/releases/$id/assets"

for name in "$bundle" "$dtb"; do
  digest=$(sha256sum "$assets_dir/$name")
  digest="sha256:${digest%% *}"
  asset=$(jq -c --arg name "$name" '.assets[] | select(.name == $name)' <<<"$release")
  if [[ -z "$asset" ]]; then
    asset=$(curl --fail-with-body --silent --show-error --proto '=https' \
      --header "Authorization: Bearer $GH_TOKEN" \
      --header 'Content-Type: application/octet-stream' \
      --data-binary "@$assets_dir/$name" "$upload?name=$name")
  fi
  jq -e --arg digest "$digest" '.state == "uploaded" and .digest == $digest' <<<"$asset" >/dev/null ||
    { echo "::error::附件校验失败：$name。请审核草稿中的现有文件。"; exit 1; }
done

printf '已准备 OTA 草稿：%s/%s/releases/tag/%s\n' "$GITHUB_SERVER_URL" "$GITHUB_REPOSITORY" "$tag" |
  tee -a "$GITHUB_STEP_SUMMARY"
