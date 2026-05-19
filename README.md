# Design Center — AP Placement

WiFi AP 自動佈點設計中心 — 從桌面 GUI 移植的 Web 版。
上傳建築平面圖、自動辨識牆體、用 NSGA-II 基因演算法找出最佳 AP 佈點，並輸出含熱力圖的 PDF 報表。

---

## 功能總覽

- 上傳平面圖（PNG/JPG），檔名 `*_WxHm.png` 自動讀取實際尺寸
- OpenCV 自動辨識牆體與 6 種材質（concrete / brick / glass / wood / metal / door）
- NSGA-II 真 GA 多目標最佳化 AP 佈點，容量公式：1 AP / 120 m²
- 牆體穿透感知熱力圖（Signal / Coverage / Interference / SINR 4 種模式）
- PDF 報表一鍵下載
- **零 Docker、SQLite 單檔、3 個命令完成啟動**

---

## 一、系統需求

| 項目 | 版本 |
|------|------|
| Python | **3.11+** |
| Node.js | **20+**（僅 setup 階段需要編譯前端） |
| 作業系統 | Windows 10/11、macOS、Linux |

> 不需要 Docker、PostgreSQL、Redis。SQLite 與本機 venv 全包辦。

---

## 二、安裝（只跑一次）

### Windows
```bat
scripts\setup.bat
```

### macOS / Linux
```bash
chmod +x scripts/*.sh
./scripts/setup.sh          # 互動確認
# 或一鍵全自動 (不問,直接裝):
./scripts/setup.sh -y
```

setup 腳本會依序：
1. **環境檢查** — 偵測 Python 3.11+ 與 Node 20+
   - 已安裝 → 跳過,直接用現有版本
   - 未安裝 → 依 distro 自動透過套件管理工具安裝
     （支援 `apt` / `dnf` / `yum` / `pacman` / `zypper` / `brew`,需 sudo）
2. 在 `backend/venv` 建立 Python 虛擬環境並安裝 `requirements.txt`
3. 在 `frontend/` 跑 `npm install` 與 `npm run build`
4. 前端 build 結果輸出到 `backend/static/`,由 FastAPI 直接 serve

> **Ubuntu 22.04 注意**：預設 Python 是 3.10,腳本會自動加 `deadsnakes` PPA 來裝 3.11。
> **沒有 sudo 權限的環境**：請事先請管理員裝好 Python 3.11+ 與 Node 20+,setup 偵測到就會直接跳過。

---

## 三、啟動系統

### Windows
```bat
scripts\run.bat
```

### macOS / Linux
```bash
./scripts/run.sh
```

啟動成功後：
- 後端 API 與前端 UI 都掛在 **http://localhost:8000**
- 瀏覽器會自動開啟首頁
- API 文件（Swagger）在 **http://localhost:8000/docs**
- 要停止伺服器：在終端機按 `Ctrl + C`,或在另一個終端機跑停止腳本：
  - Windows: `scripts\stop.bat`(可加 port: `scripts\stop.bat 8001`)
  - Linux/macOS: `./scripts/stop.sh`(可加 port: `./scripts/stop.sh 8001`)

### 手動啟動（除錯用）
```bash
cd backend
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

uvicorn app.main:app --port 8000 --reload
```

---

## 四、介面操作教學

### Step 1 — 建立新專案
1. 進入首頁 `http://localhost:8000`
2. 點右上角 **「+ New Project」**
3. 輸入專案名稱（例：`HQ 3F`），按 **Create**
4. 自動跳轉到該專案的工作台

### Step 2 — 上傳平面圖
1. 將 PNG/JPG 拖放到中央的 **Upload Drop Zone**（或點擊選檔）
2. **建議檔名格式：`name_WxHm.png`**（例：`office_50x30m.png`）
   - 系統會自動讀取寬高 → 公尺比例
   - 否則需手動在側欄輸入 Width / Height
3. 上傳後左側畫布顯示原圖

> 範例圖在 `floor_plans/`，可直接拖來測試：
> - `apartment_12x9m.png` — 公寓 4 房
> - `sample_30x20m.png` — 基本辦公
> - `hotel_40x12m.png` — 旅館 14 房
> - `datacenter_40x25m.png` — 全金屬牆機房
> - `office_50x30m.png` — 開放辦公 + 機櫃

### Step 3 — 自動辨識牆體
1. 點側欄 **★ Auto Detect Walls**
2. 等待 1–3 秒，畫布上會疊加偵測到的牆段（依材質著色）
3. 若辨識結果不理想，可重複按該鈕（會用不同閾值重試）

### Step 4 — 設定 AP 參數
側欄輸入：
| 欄位 | 說明 | 建議值 |
|------|------|--------|
| **# APs** | 想佈幾顆 AP，輸入 `0` 表示 AI 自動決定（依面積 / 120m²） | `0` |
| **Target Coverage (%)** | 期望的 RSSI ≥ -67 dBm 覆蓋率 | `95` |
| **GA Generations** | 演算代數，越大越精準也越慢 | `50`（預設） |

### Step 5 — 執行最佳化
1. 點 **▶ Run GA Optimizer**
2. 進度條透過 WebSocket 即時更新（顯示目前代數 / 最佳適應度）
3. 收斂後右側自動顯示熱力圖與 AP 位置（紅點）

### Step 6 — 切換熱力圖模式
右側下拉選單可在四種視覺化間切換：

| 模式 | 意義 |
|------|------|
| **Signal** | 各點接收到最強 AP 的 RSSI（dBm） |
| **Coverage** | 是否達到 -67 dBm 門檻（綠 / 紅） |
| **Interference** | 同頻干擾強度 |
| **SINR** | 訊號干擾雜訊比 |

### Step 7 — 下載 PDF 報表
1. 點 **📄 Download PDF**
2. PDF 內含：平面圖 + AP 座標表 + 4 種熱力圖 + 統計摘要

---

## 五、跨機器移植

不需要 Docker，整個資料夾打包即可：

```bash
# 在開發機
tar czf design-center-portable.tar.gz . \
    --exclude=backend/venv \
    --exclude=backend/data \
    --exclude=backend/static \
    --exclude=frontend/node_modules \
    --exclude=.git

# 對方機器
tar xzf design-center-portable.tar.gz
./scripts/setup.sh   # 或 setup.bat
./scripts/run.sh     # 或 run.bat
```

對方只需先裝好 **Python 3.11+** 與 **Node 20+**。

---

## 六、專案結構

```
Design-Center-AP-Placement/
├── backend/
│   ├── app/
│   │   ├── api/        # REST routes
│   │   ├── services/   # 演算法包裝
│   │   ├── ws/         # WebSocket
│   │   ├── main.py
│   │   └── models.py   # SQLAlchemy
│   ├── algorithms/     # 100% 複用 Desktop 版
│   │   ├── genetic_optimizer.py
│   │   └── wall_detector.py
│   ├── data/           # 執行時產生（gitignore）
│   ├── static/         # 前端 build 結果（gitignore）
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api/        # axios client
│       ├── components/
│       ├── pages/
│       └── hooks/
├── floor_plans/        # 5 張範例圖
└── scripts/
    ├── setup.{sh,bat}
    ├── run.{sh,bat}
    └── stop.{sh,bat}
```

---

## 七、API 概覽

完整互動文件：**http://localhost:8000/docs**

| Method | Path | 用途 |
|--------|------|------|
| `POST` | `/api/projects` | 新建專案 |
| `GET` | `/api/projects` | 列表 |
| `POST` | `/api/projects/{id}/upload` | 上傳平面圖 |
| `POST` | `/api/projects/{id}/walls/detect` | 自動偵測牆 |
| `POST` | `/api/projects/{id}/optimize` | 觸發 GA（async） |
| `GET` | `/api/projects/{id}/heatmap?mode=...` | 取得熱力圖 |
| `GET` | `/api/projects/{id}/report.pdf` | 下載 PDF |
| `WS` | `/ws/tasks/{task_id}` | 即時進度推送 |

---

## 八、技術棧

**後端**：FastAPI · SQLAlchemy 2 · SQLite · BackgroundTasks · WebSocket · NumPy · OpenCV · DEAP · ReportLab
**前端**：React 18 · TypeScript · Vite · React Router · Konva · Plotly · Tailwind · Zustand · Axios

---

## 九、演算法說明

- **訊號模型**：室內 log-distance + 牆體穿透累積衰減
- **路徑損耗指數**：n = 3.0（辦公室環境）
- **GA**：NSGA-II 多目標、向量化 RSSI 計算
- **Auto-N**：建築面積 ÷ `sqm_per_ap` → 起始 N，往上找最小達標 N

---

## 十、常見問題

| 問題 | 解法 |
|------|------|
| `python` 不認得 | 確認 Python 3.11+ 已加進 PATH，或改用 `py -3.11` |
| `npm install` 卡住 | 換 registry：`npm config set registry https://registry.npmmirror.com` |
| Port 8000 被占用 | Linux/macOS: `PORT=8001 ./scripts/run.sh`；Windows: 編輯 `scripts/run.bat` 改 `--port 8001` |
| Linux 跑 `./scripts/setup.sh` 顯示 Permission denied | `chmod +x scripts/*.sh` 後再跑 |
| 從 Windows clone 後 Linux 跑 `.sh` 報 `bad interpreter` | `.gitattributes` 已強制 LF,重新 clone 即可。已有的可用 `sed -i 's/\r$//' scripts/*.sh` |
| 牆體辨識結果偏少 | 平面圖解析度建議 ≥ 1000px，線條越清楚越好 |
| GA 跑很久 | 把 # APs 設小一點，或降 Generations |

---

## License

Internal demo / PoC. 演算法承自開源專案
[AadarshMishraa/Wifi-Signal-Prediction-and-Automatic-AP-Placement](https://github.com/AadarshMishraa/Wifi-Signal-Prediction-and-Automatic-AP-Placement)（MIT）+ 自製 GA 強化。
