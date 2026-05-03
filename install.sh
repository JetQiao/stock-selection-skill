#!/usr/bin/env bash
# PB-ROE 选股 Skill 一键安装脚本
#
# 功能：
#   1. 把当前目录复制到 ~/.claude/skills/pb-roe-stock-selection/
#   2. 安装 Python 依赖（akshare、pandas、jinja2 等）
#   3. 设置脚本可执行权限
#   4. 验证安装是否成功
#
# 用法：
#   bash install.sh              # 标准安装
#   bash install.sh --reinstall  # 强制覆盖已有版本

set -e

SKILL_NAME="pb-roe-stock-selection"
TARGET_DIR="$HOME/.claude/skills/$SKILL_NAME"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
REINSTALL=false

for arg in "$@"; do
  case "$arg" in
    --reinstall) REINSTALL=true ;;
  esac
done

echo "========================================="
echo "  PB-ROE 选股 Skill 安装"
echo "========================================="
echo ""

# 1. Python 检查
echo "[1/4] 检查 Python..."
if ! command -v python3 &> /dev/null; then
  echo "❌ 未找到 python3。请先安装 Python 3.9+"
  echo "   macOS: brew install python"
  echo "   或访问 https://www.python.org/downloads/"
  exit 1
fi
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "   ✓ python3 $PY_VERSION"

# 2. 复制 skill 到 ~/.claude/skills/
echo ""
echo "[2/4] 安装到 $TARGET_DIR ..."

if [ -d "$TARGET_DIR" ] && [ "$REINSTALL" = false ]; then
  if [ "$SOURCE_DIR" != "$TARGET_DIR" ]; then
    echo "   ⚠ 已存在同名 skill。加 --reinstall 覆盖，或手动删除后重试"
    echo "   跳过文件复制（仅安装依赖）"
  else
    echo "   ✓ 已经在目标目录中"
  fi
else
  if [ "$SOURCE_DIR" != "$TARGET_DIR" ]; then
    mkdir -p "$(dirname "$TARGET_DIR")"
    if [ -d "$TARGET_DIR" ]; then
      rm -rf "$TARGET_DIR"
    fi
    cp -r "$SOURCE_DIR" "$TARGET_DIR"
    echo "   ✓ 已复制到 $TARGET_DIR"
  else
    echo "   ✓ 已经在目标目录中"
  fi
fi

chmod +x "$TARGET_DIR/scripts/run_pb_roe.py" 2>/dev/null || true

# 3. 安装依赖
echo ""
echo "[3/4] 安装 Python 依赖..."
echo "   (akshare 较大，首次安装需 1-3 分钟)"

PIP_CMD="python3 -m pip install"
if command -v uv &> /dev/null; then
  echo "   检测到 uv，优先使用 uv"
  if uv pip install --system -r "$TARGET_DIR/requirements.txt" 2>/dev/null; then
    echo "   ✓ uv 安装完成"
  else
    $PIP_CMD --user -r "$TARGET_DIR/requirements.txt" --quiet
    echo "   ✓ pip 安装完成"
  fi
else
  $PIP_CMD --user -r "$TARGET_DIR/requirements.txt" --quiet || \
    $PIP_CMD -r "$TARGET_DIR/requirements.txt" --quiet --break-system-packages
  echo "   ✓ pip 安装完成"
fi

# 4. 验证
echo ""
echo "[4/4] 验证安装..."
if python3 -c "import akshare, pandas, jinja2" 2>/dev/null; then
  echo "   ✓ 依赖导入成功"
else
  echo "   ❌ 依赖导入失败"
  echo "      请手动运行：pip install -r $TARGET_DIR/requirements.txt"
  exit 1
fi

echo ""
echo "========================================="
echo "  ✅ 安装完成"
echo "========================================="
echo ""
echo "如何使用："
echo ""
echo "  方式 1（推荐）— 在 Claude Code 中直接说："
echo "      帮我跑一遍 PB-ROE 选股"
echo ""
echo "  方式 2 — 命令行直接运行："
echo "      python3 $TARGET_DIR/scripts/run_pb_roe.py"
echo ""
echo "  常用参数："
echo "      --mode loose            宽松阈值（更多结果）"
echo "      --industry 食品饮料     只选某个行业"
echo "      --top-n 10              输出 Top 10"
echo "      --skip-history          跳过历史 ROE 检查（更快）"
echo "      --output ~/abc.html     自定义输出路径"
echo ""
echo "报告默认输出到 ~/pb_roe_report.html，跑完会自动在浏览器打开。"
echo ""
