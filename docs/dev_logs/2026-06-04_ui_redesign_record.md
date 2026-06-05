# coOS UI 大改版開發紀錄 (2026-06-04)

為了改善原本過於基礎且陽春的 UI，我們對 coOS 的主頁與導航系統進行了全面的重構與美化。以下為本次改版的詳細設計與實作內容。

---

## 1. 核心改版內容

### 1.1. 移除底部 Tab Bar ＆ 導入三方向邊緣導航
- **舊版**: 底部有固定的 5 個 tab 按鈕。
- **新版**: 完全移除底部 tab bar，改為滑鼠接近螢幕邊界時，會向內浮出半透明有弧度（玻璃微光）的邊緣觸發區塊，引導與提示使用者切換：
  - **左邊緣**: 接近時浮出，點擊或按鍵盤 **`左鍵 (ArrowLeft)`** 切換至 **Daily Report（日報）** 頁面。
  - **右邊緣**: 接近時浮出，點擊或按鍵盤 **`右鍵 (ArrowRight)`** 切換至 **Community（社群）** 頁面。
  - **上邊緣**: 接近時浮出，點擊或按鍵盤 **`上鍵 (ArrowUp)`** 切換至 **Achievements（成就）** 頁面。
  - **聊天室切換**: 點擊 Coverflow Carousel 正中央的角色進入該角色的聊天室。

### 1.2. 頁面滑入與滑出過場動畫
- 為了讓切換分頁更具備流暢的視覺連續性，引入了方向性滑入/滑出動畫：
  - **日報**: 從左側滑入；點擊返回時往左滑回，露出底層的主頁面。
  - **社群**: 從右側滑入；點擊返回時往右滑回。
  - **成就**: 從上方滑入；點擊返回時往上滑回。
  - **聊天室**: 從下方滑入；點擊返回時往下滑回。
- 返回時皆使用原方向滑回的物理邏輯，主頁始終作為底層背景保留。

### 1.3. 遊戲級 3D Coverflow 輪盤 Carousel
- **舊版**: 平面橫向排列且佔據底部過多空間。
- **新版**: 重構為佔據底層約 **25%** 高度的弧形 3D Coverflow 輪盤：
  - 聚焦的角色會移動至正中央並放大（約 1.3x 以上，主尺寸 110px），並帶有金色呼吸光暈。
  - 左右兩側角色往兩旁漸次縮小與旋轉（帶 3D perspective 旋轉角度）。
  - 支持**滑鼠滾輪滾動**切換角色（滾輪向上往左轉，滾輪向下往右轉），左右兩側亦保留精緻的箭頭導航按鈕。
  - 輪盤底座設計了微妙的弧形軌道線。
  - 支持 **Avatar 圖片（透明人像/卡通人像）**，聚焦時圖片會帶有動畫突出圓圈（向上偏移並放大縮放）。
  - 點擊正中央聚焦的角色會直接進入該角色的專屬聊天室。

### 1.4. 新建角色按鈕
- 在 Carousel 列表中，最後一個元素設計為虛線圓圈，中間帶有 `+` 號的新建角色按鈕，當使用者點擊時會觸發新建角色流程。

### 1.5. Context Header (2 列等高 / 3 欄等寬) 佈局重構
- 角色名稱標題（如 `CSIE`）獨立置於最上方，只顯示名稱本身，不顯示 "Role" 字樣。
- 下方分為兩個等高的橫列：
  - **第一列**: 平均分配為三欄，分別展示 `Project`、`Promises`、`Goal` 區塊，均採用毛玻璃卡片（glassmorphism）設計。
  - **第二列**: Dashboard 區塊。將 `ConsistencyHeatmap`（熱力圖）移入其中，標題置於區塊左上角，並為熱力圖加入專屬標題「365 天一致性紀錄」。

### 1.6. 治療同盟暖色系調與淺深色切換
- **視覺色調**: 配合治療同盟與成就感的主題，重新設計了溫暖的色調組合（琥珀金、暖珊瑚與溫和的背景漸層波紋），減少焦慮與空虛感。
- **淺色/深色模式**: 支持模式切換（主頁右上角設有 ☀/🌙 切換鈕），背景與卡片會平滑過渡。
- **背景建議**: 未來若放置實際背景圖片，建議使用：工作臺桌面（專注感）、野餐墊或草地/天空（放鬆與真實感）。

---

## 2. 檔案變更總覽

| 變更路徑 | 類型 | 說明 |
| --- | --- | --- |
| `apps/desktop/src/App.tsx` | 修改 | 重寫 App Shell，移除底部 tab bar，加入邊緣觸發監聽、鍵盤事件與過場動畫層。 |
| `apps/desktop/src/index.css` | 修改 | 新增暖色系 Light/Dark 設計系統 Tokens、3D Coverflow 視覺特效、玻璃卡片與背景波紋動畫。 |
| `apps/desktop/src/components/EdgeNavigationTrigger.tsx` | 新增 | 實作滑鼠接近邊界時向內浮出的三向弧形提示面板。 |
| `apps/desktop/src/components/PageTransition.tsx` | 新增 | 實作 spring 物理效果的 4 方向過場滑動容器。 |
| `apps/desktop/src/components/m3_2_dashboard/index.tsx` | 修改 | 重構 Dashboard 為 75% 資訊區與 25% 輪盤區，將 Heatmap 移入 Header。 |
| `apps/desktop/src/components/m3_2_dashboard/RoleFocusCarouselDock/index.tsx` | 修改 | 完全重寫為 3D Coverflow，實作滾輪事件、圖片突出特效與 "+" 虛線按鈕。 |
| `apps/desktop/src/components/m3_2_dashboard/ContextHeaderAggregator/index.tsx` | 修改 | 實作 2 列等高、3 欄等寬與大標題新佈局，嵌入 Heatmap。 |
| `apps/desktop/src/components/m3_2_dashboard/TransitionBackground/index.tsx` | 修改 | 使用新的溫暖呼吸感背景漸層。 |
| `apps/desktop/src/components/m3_2_dashboard/ConsistencyHeatmap/index.tsx` | 修改 | 熱力圖視覺優化，調整 tooltip 為暖色毛玻璃。 |
| `apps/desktop/src/components/m3_2_dashboard/ConsistencyHeatmap/HeatmapCell.tsx` | 修改 | 調整格子的暖色系等級色塊顏色。 |
| `apps/desktop/index.html` | 修改 | 載入 Inter 字型與設定預設 `data-theme="light"`。 |
