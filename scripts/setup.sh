#!/usr/bin/env bash
# Design Center - AP Placement / Linux & macOS setup
# 自動偵測 Python 3.11+ 與 Node 20+,若已有則跳過安裝。
set -e
cd "$(dirname "$0")/.."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ---------- 顏色輸出 ----------
if [ -t 1 ]; then
    C_GREEN='\033[0;32m'; C_YELLOW='\033[1;33m'; C_RED='\033[0;31m'; C_BLUE='\033[0;34m'; C_RESET='\033[0m'
else
    C_GREEN=''; C_YELLOW=''; C_RED=''; C_BLUE=''; C_RESET=''
fi
ok()   { printf "${C_GREEN}[OK]${C_RESET} %s\n" "$*"; }
warn() { printf "${C_YELLOW}[WARN]${C_RESET} %s\n" "$*"; }
err()  { printf "${C_RED}[ERR]${C_RESET} %s\n" "$*"; }
info() { printf "${C_BLUE}[..]${C_RESET} %s\n" "$*"; }

# ---------- 版本比較 ----------
# usage: ver_ge "3.11.5" "3.11"  -> 0 if first >= second
ver_ge() {
    [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]
}

# ---------- 偵測 Python 3.11+ ----------
PYTHON_BIN=""
for cand in python3.13 python3.12 python3.11 python3 python; do
    if command -v "$cand" >/dev/null 2>&1; then
        v=$("$cand" -c 'import sys;print("%d.%d.%d"%sys.version_info[:3])' 2>/dev/null || echo "0.0.0")
        if ver_ge "$v" "3.11.0"; then
            PYTHON_BIN="$cand"
            ok "找到 Python $v ($cand)"
            break
        fi
    fi
done

# ---------- 偵測 Node 20+ ----------
NODE_OK=""
if command -v node >/dev/null 2>&1; then
    nv=$(node -v 2>/dev/null | sed 's/^v//')
    if ver_ge "$nv" "20.0.0"; then
        NODE_OK="1"
        ok "找到 Node $nv"
    else
        warn "Node 版本太舊 ($nv),需 20+"
    fi
fi
if ! command -v npm >/dev/null 2>&1; then
    NODE_OK=""
fi

# ---------- 偵測作業系統與套件管理工具 ----------
detect_pkg_mgr() {
    if [ "$(uname)" = "Darwin" ]; then echo "brew"; return; fi
    if command -v apt-get >/dev/null 2>&1; then echo "apt"; return; fi
    if command -v dnf     >/dev/null 2>&1; then echo "dnf"; return; fi
    if command -v yum     >/dev/null 2>&1; then echo "yum"; return; fi
    if command -v pacman  >/dev/null 2>&1; then echo "pacman"; return; fi
    if command -v zypper  >/dev/null 2>&1; then echo "zypper"; return; fi
    echo ""
}
PKG_MGR="$(detect_pkg_mgr)"

SUDO=""
if [ "$(id -u)" != "0" ] && command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
fi

install_python() {
    info "準備安裝 Python 3.11+ (透過 $PKG_MGR)"
    case "$PKG_MGR" in
        apt)
            $SUDO apt-get update
            # Ubuntu 22.04 預設 3.10,需 deadsnakes PPA
            if ! apt-cache show python3.11 >/dev/null 2>&1; then
                $SUDO apt-get install -y software-properties-common
                $SUDO add-apt-repository -y ppa:deadsnakes/ppa
                $SUDO apt-get update
            fi
            $SUDO apt-get install -y python3.11 python3.11-venv python3.11-dev
            PYTHON_BIN="python3.11"
            ;;
        dnf)  $SUDO dnf install -y python3.11 python3.11-devel; PYTHON_BIN="python3.11" ;;
        yum)  $SUDO yum install -y python3.11 python3.11-devel; PYTHON_BIN="python3.11" ;;
        pacman) $SUDO pacman -Sy --noconfirm python; PYTHON_BIN="python3" ;;
        zypper) $SUDO zypper install -y python311 python311-devel; PYTHON_BIN="python3.11" ;;
        brew) brew install python@3.11; PYTHON_BIN="python3.11" ;;
        *)
            err "未知作業系統,請手動安裝 Python 3.11+"
            err "  Ubuntu/Debian: sudo apt install python3.11 python3.11-venv"
            err "  macOS:         brew install python@3.11"
            exit 1
            ;;
    esac
    ok "Python 安裝完成 ($PYTHON_BIN)"
}

install_node() {
    info "準備安裝 Node 20+ (透過 $PKG_MGR)"
    case "$PKG_MGR" in
        apt)
            curl -fsSL https://deb.nodesource.com/setup_20.x | $SUDO -E bash -
            $SUDO apt-get install -y nodejs
            ;;
        dnf)
            curl -fsSL https://rpm.nodesource.com/setup_20.x | $SUDO -E bash -
            $SUDO dnf install -y nodejs
            ;;
        yum)
            curl -fsSL https://rpm.nodesource.com/setup_20.x | $SUDO -E bash -
            $SUDO yum install -y nodejs
            ;;
        pacman) $SUDO pacman -Sy --noconfirm nodejs npm ;;
        zypper) $SUDO zypper install -y nodejs20 npm20 ;;
        brew)   brew install node@20; brew link --overwrite --force node@20 ;;
        *)
            err "未知作業系統,請手動安裝 Node 20+"
            err "  Ubuntu/Debian: curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs"
            err "  macOS:         brew install node@20"
            exit 1
            ;;
    esac
    NODE_OK="1"
    ok "Node 安裝完成 ($(node -v))"
}

# ---------- 詢問是否安裝缺少的依賴 ----------
NEED_INSTALL=""
[ -z "$PYTHON_BIN" ] && NEED_INSTALL="${NEED_INSTALL} Python3.11+"
[ -z "$NODE_OK" ]    && NEED_INSTALL="${NEED_INSTALL} Node20+"

if [ -n "$NEED_INSTALL" ]; then
    echo
    warn "缺少以下依賴:${NEED_INSTALL}"
    if [ -z "$PKG_MGR" ]; then
        err "無法偵測套件管理工具,請手動安裝後重跑此腳本"
        exit 1
    fi
    if [ "$AUTO_YES" = "1" ] || [ "$1" = "-y" ]; then
        REPLY="y"
    else
        printf "${C_YELLOW}是否自動安裝? (需 sudo) [Y/n] ${C_RESET}"
        read -r REPLY </dev/tty || REPLY="y"
    fi
    case "$REPLY" in
        n|N|no|NO) err "已取消。請手動安裝後重跑"; exit 1 ;;
    esac
    [ -z "$PYTHON_BIN" ] && install_python
    [ -z "$NODE_OK" ]    && install_node
else
    ok "環境完整,跳過依賴安裝"
fi

echo
info "=== 1/2 Backend venv + pip install ==="
cd backend
if [ ! -d venv ]; then
    "$PYTHON_BIN" -m venv venv
    ok "建立 venv"
else
    ok "venv 已存在,跳過建立"
fi
# shellcheck disable=SC1091
source venv/bin/activate
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt
ok "Python 套件就緒"

echo
info "=== 2/2 Frontend npm install + build ==="
cd ../frontend
if [ -d node_modules ] && [ -f node_modules/.package-lock.json ]; then
    ok "node_modules 已存在,執行 npm ci 確保同步"
    npm ci --silent || npm install
else
    npm install
fi
npm run build
ok "前端 build 完成 → backend/static/"

echo
ok "=== 全部完成! ==="
echo
echo "啟動伺服器:"
echo "  ./scripts/run.sh"
echo
echo "或手動:"
echo "  cd backend && source venv/bin/activate && uvicorn app.main:app --port 8000"
