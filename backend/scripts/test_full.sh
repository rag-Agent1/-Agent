#!/bin/bash
# 后端全链路验证脚本
# Usage: bash scripts/test_full.sh [port] [image_path]
# Default: port=8000, image=../data/images/李宁音速10.png

set -e

PORT="${1:-8000}"
IMAGE="${2:-data/images/李宁音速10.png}"
BASE="http://localhost:$PORT"
PASS=0
FAIL=0

green() { echo -e "\033[32m$1\033[0m"; }
red()   { echo -e "\033[31m$1\033[0m"; }

check() {
    local desc="$1" cond="$2"
    if $cond; then
        green "  ✅ $desc"
        PASS=$((PASS + 1))
    else
        red "  ❌ $desc"
        FAIL=$((FAIL + 1))
    fi
}

echo "========================================"
echo "  后端全链路验证脚本"
echo "  目标: $BASE"
echo "  图片: $IMAGE"
echo "========================================"
echo ""

# 1. Health
echo "--- 1. Health ---"
HEALTH=$(curl -s --max-time 5 "$BASE/api/v1/health")
check "health 返回 200" "echo '$HEALTH' | python3 -c 'import sys,json; d=json.load(sys.stdin); exit(0 if d.get(\"status\")==\"ok\" else 1)'"

# 2. Upload
echo "--- 2. Upload ---"
UPLOAD_RESP=$(curl -s -X POST "$BASE/api/v1/upload/image" -F "file=@$IMAGE")
IMAGE_ID=$(echo "$UPLOAD_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['image_id'])")
check "upload 返回 image_id" "[ -n '$IMAGE_ID' ]"
echo "    image_id: $IMAGE_ID"

# 3. Chat (Round 1) + SSE
echo "--- 3. Chat Round 1 ---"
CHAT1=$(curl -s -X POST "$BASE/api/v1/chat" \
  -H 'Content-Type: application/json' \
  -d "{\"session_id\": null, \"image_id\": \"$IMAGE_ID\", \"text\": \"推荐类似的鞋\"}")
SID=$(echo "$CHAT1" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['session_id'])")
MID1=$(echo "$CHAT1" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['message_id'])")
check "chat 返回 session_id" "[ -n '$SID' ]"
check "chat 返回 message_id" "[ -n '$MID1' ]"
echo "    session_id: $SID"

echo "--- 4. SSE Stream ---"
SSE_OUT=$(timeout 60 curl -s -N "$BASE/api/v1/chat/stream?message_id=$MID1" 2>&1 || true)
check "SSE 有 candidates 事件" "echo '$SSE_OUT' | grep -q 'event: candidates'"
check "SSE 有 delta 事件" "echo '$SSE_OUT' | grep -q 'event: delta'"
check "SSE 有 final 事件" "echo '$SSE_OUT' | grep -q 'event: final'"

# 5. Chat (Round 2 - memory)
echo "--- 5. Chat Round 2 (Memory) ---"
CHAT2=$(curl -s -X POST "$BASE/api/v1/chat" \
  -H 'Content-Type: application/json' \
  -d "{\"session_id\": \"$SID\", \"image_id\": null, \"text\": \"有更便宜的么\"}")
MID2=$(echo "$CHAT2" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['message_id'])")
check "chat round 2 有 message_id" "[ -n '$MID2' ]"

SSE2=$(timeout 30 curl -s -N "$BASE/api/v1/chat/stream?message_id=$MID2" 2>&1 || true)
check "SSE Round 2 有 delta" "echo '$SSE2' | grep -q 'event: delta'"

# 6. Stop
echo "--- 6. Stop ---"
STOP=$(curl -s -X POST "$BASE/api/v1/chat/stop" \
  -H 'Content-Type: application/json' \
  -d "{\"message_id\": \"$MID2\"}")
check "stop 返回 code=0" "echo '$STOP' | python3 -c 'import sys,json; d=json.load(sys.stdin); exit(0 if d.get(\"code\")==0 else 1)'"

echo ""
echo "========================================"
echo "  结果: $PASS 通过, $FAIL 失败"
echo "========================================"

exit $FAIL
