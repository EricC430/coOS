# 非 M6 功能討論與薩提爾冰山覺察技術實現紀錄

**標籤**:`[DevLog-Design-Refinement]`
**日期**:2026-05-31
**上下文**:解決 M6 規格修訂過程中，延伸出對非 M6 模組（如行為監測、AI 專家發話策略、薩提爾圖譜應用）的討論紀錄，供跨 Session 查閱與驗證。

---

## 1. 討論中提及的「非 M6 模組」功能整理

在本次時段卡片與 XP 帳本規格修訂中，牽涉到了以下目前尚未撰寫詳細 SPEC（但已存在於系統架構藍圖中）的非 M6 功能：

### 1.1 M1.1/M1.2 行為監測與專注指標 (Telemetry Metrics)
*   **功能需求**：當天每個 `daily_reflection_segments` 的行為數據來源。
*   **細部指標**：
    *   `duration_minutes`：使用者專注時間。
    *   `focus_depth`：專注深度評分（0.0 ~ 1.0，基於 VS Code 編輯頻率與視窗切換）。
    *   `distraction_count`：分心中斷次數（切換至社群網站或無效視窗頻率）。
*   **對接時機**：由端側監測軟體背景收集，寫入本地 SQLite，在生成 Segment 草稿時做為事實背景（Beliefs）提供給 AI 專家。

### 1.2 M1.5 微干預/微微 Nudges 引擎 (Micro-Interventions)
*   **功能需求**：當使用者完成某個專案階段，或者做出「打破舊有負向信念」的行為時，AI 專家主動跳出引導聊天。
*   **運作機制**：
    *   系統利用慢迴路（Slow Loop）分析出使用者的負向信念（例如：`求助等於無能`）。
    *   當 Telemetry 監測到使用者發生打破該信念的行為（例如：`主動發起 GitHub 協作 PR`），微干預引擎便會派發事件，觸發 AI 專家以朋友口吻進行正面強化讚美。

### 1.3 M3.8 Wrapped 週報數據敘事化福祉 (Narrating Welfare)
*   **功能需求**：在每週結算中，讀取薩提爾冰山圖譜，轉譯為有溫度的自省敘事。
*   **防錯機制 (RISK-10)**：絕對禁止虛假樂觀。如果當週 `mood_score` 平均極低（<4），週報必須自動從「慶祝模式」降級為「陪伴/共情模式」，避免產生 Gaslighting（煤氣燈效應）般的虛假正向感。

### 1.4 M1.2 Defer-to-Breakpoint 斷點好奇套問 (Breakpoint Elicitation)
*   **功能需求**：AI 專家像朋友一樣好奇你在忙什麼的聊天，並在此過程中藉由自然對話，套出可以補上 `daily_reflection_segments` 反思卡片所需的資訊（減少使用者手動輸入負擔）。
*   **對接時機**：Telemetry 偵測到編輯器閒置或工作完成的「自然斷點」時，才觸發聊天推送，避免中斷使用者的心流。

---

## 2. 薩提爾冰山覺察引導方式：是技術設計還是幻覺？

**結論：這是一項完全具備技術細節且可行性已被紀錄的系統設計，並非幻覺。**

在 coOS 的學術憲法與已存在的 `M4.2 (Persona)` 規格中，設計了以下三個關鍵技術組件，來確保 AI 專家使用**「從旁慢慢引導與認知重塑（Socratic Reframing）」**，而非白目地直接宣讀冰山診斷報告：

### 2.1 BDI 協調器 (BDI Reconciler - RISK-08)
*   **位置**：`services/m4_2_persona/graph.py` 中的 `bdi_reconciler` 節點。
*   **原理**：AI 專家不會直接把信念（Beliefs，例如：`使用者有搞砸事情的信念`）直接拼貼成 Prompt 回覆。
*   **技術實作**：
    ```python
    # [R09 §BDI] 統一在 Python 層 reconcile 信念與渴望，轉化為「引導意圖 (Intention)」
    def reconcile(belief: str, desire: str) -> str:
        if "搞砸事情的信念" in belief:
            # 轉換為溫和的引導意圖，而不是揭露
            return "透過詢問使用者當下的感受，並將今日的成功歸因於其付出的努力 (行為事實)，重塑其信念。"
        return desire
    ```

### 2.2 狀態反轉原則 (State Inversion Principle - RISK-03)
*   **位置**：[docs/05_integration_risk_audit.md](file:///c:/Users/chent\Desktop/我的資料夾/學校/大學/三下/生成式人工智慧導論/coOS/docs/05_integration_risk_audit.md) (§RISK-03)。
*   **原理**：系統強制規定，注入隱性狀態時，Prompt **絕對禁止鏡像 (Mirror)** 使用者的狀態。
*   **技術實作**：如果快迴路檢測到 `anxiety` (焦慮) 或 `avoidance` (逃避)，注入 Persona Context 的參數是 `persona_tone="gentle"`、`challenge_level="low"` 且 `guilt_inducement=False`，這在系統提示詞生成器中是寫死的映射規則，確保 AI 在語氣上先溫和下來。

### 2.3 音調狀態機與 Agency 控制 (Echo Mode - R03 §3)
*   **位置**：[M4_2_persona_state_machine_SPEC.md](file:///c:/Users/chent\Desktop/我的資料夾/學校/大學/三下/生成式人工智慧導論/coOS/docs/modules/M4_2_persona_state_machine_SPEC.md#L170-L191)。
*   **原理**：當偵測到使用者有防衛阻抗（Reactance，例如 "你不懂"）時，系統會調降 AI 的 Agency（主導權，如從 0.8 降到 0.3）。
*   **技術實作**：語氣狀態機轉移至 `EMPATHETIC` (共情) 或 `PROBING` (探索) 狀態。在這兩種狀態下，System Prompt 會有硬性約束：**「禁止使用肯定句陳述使用者心理，必須使用引導式問句（如：你是否覺得...？）」**。

### 2.4 心智模型對應您的實戰範例 (Example Alignment)
當使用者出現「運氣好的事情最後一定會搞砸」的信念時，系統處理流程：
1.  **慢迴路記錄**：`M4.6 Observer` 從歷史對話偵測到此觀點，寫入 Neo4j：`(:Perception {content: "運氣好最後會搞砸"})`。
2.  **慢迴路載入**：新 Thread 開啟時，檢索出此 Perception 放入背景 REMT 上下文。
3.  **快迴路觸發**：當前 Segment 完成，使用者表示這只是運氣好。
4.  **BDI 轉譯與發話**：
    *   `bdi_reconciler` 拒絕直說「你又來了」。
    *   `Echo Mode` 設定 Agency 為 `PROBING`（引導提問）。
    *   AI 專家 Robert 發話：「*拿到這個成績真的很棒！但這真的只是運氣嗎？我看你這禮拜投入了很多時間去克服那個編譯錯誤，要不要跟我說說你是怎麼解出來的？*」（引導歸因至個人努力，重塑勝任感）。
