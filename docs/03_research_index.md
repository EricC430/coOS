# 研究論文索引 (Research Index)

> 本文件是專案的「學術憲法」。每個架構決策、每個演算法選擇都必須能追溯到此處的某一條編號。
>
> Claude Code 引用研究時的標準格式:`[Rxx: 短關鍵字 §章節]`

## 引用語法快查

```python
# 在程式碼註解中
# [R03: Echo Mode §3.2] 偵測防衛語氣 → 調降 Agency 從 0.8 → 0.3

# 在 commit message 中
git commit -m "feat(M4.2): Echo Mode 阻抗消解控制器 [R03 §3.2, R05 §治療同盟]"

# 在文件中
M4.2.2 實作參考 [R03: Echo Mode 動態音調控制] 與 [R05: 跨越恐怖谷效應]
```

---

## R01 — ZPD 量化與 RLHF 自動化難度調節

**全名**:深入研究近側發展區 (ZPD) 的量化與強化學習反饋 (RLHF):自動化難度調節與程序化內容生成之縱向架構解析

**核心技術詞彙**:

- ZONE 框架 (REJECT + GRAD 機制) — ZPD 機率化操作
- 多模態 BKT (貝氏知識追蹤) — 任務耗時 + 挫折語氣四象限
- POMDP — 部分可觀察狀態的信念分布
- α-DPO — 動態自適應獎勵邊界
- DualLoop-DPO — 快慢雙迴路 KL 漂移控制
- ABC (Attention-Based Credit Assignment) — 注意力信用分配
- Dropout 危機管理 — 強制退縮重建自信

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M4.8 | POMDP + 多模態 BKT (狀態推論) |
| M4.11 | ZONE 框架生成 ZPD 任務池 |
| M4.13 | α-DPO 防範 Dropout 後懲罰 |

**章節索引**:

- §理論基礎 — ZONE 數學形式化
- §動態追蹤 — 任務耗時 + 挫折語氣
- §DDA 與 PCG — 程序化內容生成
- §α-DPO 與 DualLoop — RLHF 變體
- §Dropout 危機 — 退縮與信用分配

**Claude Code 引用範例**:

```python
# [R01: ZONE §REJECT] 過濾低於使用者能力的任務,先做 Rejection Sampling
def filter_tasks_below_zpd(tasks, user_ability):
    return [t for t in tasks if t.difficulty > user_ability.lower_bound]
```

---

## R02 — 隱性行為模式機器學習識別與動態 Persona Agent 注入

**全名**:深度研究:隱性行為模式的機器學習識別與動態 Persona Agent 注入架構

**核心技術詞彙**:

- 源碼變更熵 (Source-code Change Entropy) — Shannon Entropy of diff blocks
- 時間動力學 (Temporal Dynamics) — 提交間距的爆發性特徵
- 孤立森林 (Isolation Forest) — 非監督式異常閾值
- HMM (隱馬爾可夫模型) + Viterbi 解碼 — 動態狀態解碼
- REMT (Real-time Editable Memory Topology) — 即時可編輯記憶拓樸
- YAML 上下文工程 (Context Engineering)
- DRIFT (Dynamic Rule Isolation Framework Transformer) — 動態規則隔離

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M4.8 | 特徵矩陣萃取 + HMM 狀態解碼 |
| M4.2.4 | REMT 上下文注入 |
| M4.1.4 | DRIFT 防 Prompt Injection |
| M1.3.1 | 源碼變更熵的計算 (VS Code AST 攔截器) |

**章節索引**:

- §計算心理語言學 — 提交訊息語意特徵
- §非監督式管線 — Isolation Forest + HMM
- §動態上下文工程 — REMT 與 YAML
- §架構安全性 — DRIFT 防禦

**Claude Code 引用範例**:

```python
# [R02: 源碼變更熵 §1.1] H = -Σ p_i log(p_i),p_i 為各檔案 diff 比例
def calculate_change_entropy(diff_blocks):
    file_ratios = compute_file_diff_ratios(diff_blocks)
    return -sum(p * math.log2(p) for p in file_ratios if p > 0)
```

---

## R03 — 勸導式科技與動態人設一致性

**全名**:深度研究勸導式科技與生成式代理之動態人設一致性:架構挑戰與心理防衛機制之協同

**核心技術詞彙**:

- 人設崩塌 (Persona Drift) — LLM 長對話下的人格漂移
- ARPM (Adaptive Re-ranking Persona Memory) — 異質時序記憶治理框架
- Echo Mode 協議 — 動態音調控制 (Tone Stability)
- 心理阻抗理論 (Psychological Reactance Theory)
- 情緒恐怖谷 (Bots with Empathy) — AI 同理心的反面效應
- 諂媚效應 (Sycophancy)
- KPM (Knowledge-based Persuasion Model)
- CIIT + LASSI — 人際互動的馬可夫模型化

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M4.2.1 | 系統提示詞工程 (固定人設) |
| M4.2.2 | Echo Mode 阻抗消解 |
| M4.9 | ARPM 異質時序記憶治理 |
| M4.2.4 | 副語言瑕疵渲染 |

**章節索引**:

- §1 微觀認知架構
- §2 ARPM 框架
- §3 Echo Mode 協議
- §4 阻抗理論與同理心悖論
- §5 KPM 知識驅動勸導
- §6 從權威到共情的狀態機移轉

**Claude Code 引用範例**:

```python
# [R03: Echo Mode §3.2] Agency 平滑切換,絕對禁止階躍式變化
class EchoModeController:
    AGENCY_AUTHORITATIVE = 0.85
    AGENCY_EMPATHETIC = 0.25
    TRANSITION_STEPS = 5  # 5 個對話 turn 內漸進

    def transition(self, current_agency, target_agency):
        step = (target_agency - current_agency) / self.TRANSITION_STEPS
        return current_agency + step
```

---

## R04 — 動態 GNN 個人知識圖譜 + 薩提爾冰山 + 心理幻覺防禦

**全名**:深度研究基於動態圖神經網路的個人知識圖譜:薩提爾冰山模型結構化與心理幻覺防禦機制

**核心技術詞彙**:

- 動態圖神經網路 (DGNN)
- GraphRAG — 圖結構檢索增強生成
- 薩提爾冰山七大節點 — Behavior → Coping Stance → Feeling → Perception → Expectation → Yearning → Self
- 霍克斯過程 (Hawkes Processes) — 時序自我激發
- NSVIF (Neuro-Symbolic Verification & Inference Framework)
- D-ALP (Discourse-weighted Abductive Logic Programming) — 論述加權溯因邏輯
- 反溯因推理 (Counter-Abductive Reasoning)
- 心理幻覺 (Psychological Hallucination) — 過度推論的具體形式

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M5.1 | 薩提爾冰山節點/邊 schema |
| M5.2 | NSVIF 反溯因驗證 |
| M4.10 | D-ALP 論述加權 |
| M5.3 (動力學) | 霍克斯過程時序建模 |

**章節索引**:

- §拓樸演化 — 從靜態摘要到動態圖譜
- §冰山本體論化 — 節點與邊定義
- §霍克斯過程 — 時序激發
- §心理幻覺定義
- §D-ALP 框架
- §反溯因驗證
- §雙階段心理學引導的編輯防禦

**Claude Code 引用範例**:

```cypher
// [R04: 冰山七大節點] Cypher schema 嚴格依此設計
CREATE (b:Behavior {description: "連續除錯3小時"})
       -[:REFLECTS {confidence: 0.8}]->
       (cs:CopingStance {type: "超理智"})
       -[:DRIVEN_BY]->
       (f:Feeling {emotion: "挫折"})
```

---

## R05 — 計算心智理論動態評估 + 治療同盟

**全名**:深度研究計算心智理論的動態評估:高階語言模型的信念追蹤與治療同盟架構

**核心技術詞彙**:

- 計算心智理論 (CTM, Theory of Mind)
- 高階 ToM — 信念追蹤 (Belief Tracking)
- 對抗性生成與擾動測試
- 治療同盟 (Therapeutic Alliance)
- 跨越恐怖谷效應
- 副語言線索 (Paralinguistic Cues) — 填充詞、自我修正
- 合成心理病理學 (Synthetic Psychopathology)
- 主動展現弱點 — 觸發同理心與罪惡感
- EHARS 量表 (Experiences in Human-AI Relationships Scale)

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M4.2.1 | 過往經歷敘事 |
| M4.2.3 | 社會承諾與同理心制約 |
| M4.2.4 | 副語言線索注入 |

**章節索引**:

- §典範轉移 — 從靜態到動態評估
- §動態評估基準 — ToM 量化
- §連續多輪對話的信念追蹤
- §治療同盟建構
- §跨越恐怖谷
- §合成心理病理學
- §EHARS 量表

**Claude Code 引用範例**:

```python
# [R05: 副語言線索 §跨越恐怖谷] 約 8% 機率注入填充詞
FILLER_WORDS = ["嗯...", "讓我想想", "等等,我重新想一下", "啊對了"]
async def inject_paralinguistic(response_text):
    if random.random() < 0.08:
        return random.choice(FILLER_WORDS) + " " + response_text
    return response_text
```

---

## R06 — 整合 ToM 與薩提爾冰山的深度行為分析

**全名**:深度行為分析與認知建模:整合心智理論與薩提爾冰山理論的大型語言模型創新應用研究

**核心技術詞彙**:

- 數位表型 (Digital Phenotypes)
- 版本控制紀錄作為認知狀態感測器
- 多維度開發者輪廓
- 應對姿態 (Coping Stances) — 指責、討好、超理智、打岔、表裡一致
- 雙層記憶網路 — 短期 + 長期
- 多目標強化學習 (Multi-objective RL)
- 差分隱私去識別化 (Differential Privacy)

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M4.8 | 行為特徵 → 認知狀態映射 |
| M5.1 | 應對姿態作為冰山中層 |
| M2.4.2 | 差分隱私微調 |
| M4.4.3 | 雙層記憶網路 |

**章節索引**:

- §第二章 數位表型探勘
- §第三章 ToM 在 LLM 中的應用
- §第四章 薩提爾冰山與情感計算
- §第五章 微觀結構化分析
- §第六章 動態系統提示詞配置
- §第七章 差分隱私保護

---

## R07 — 2026 年端側 LLM 語意壓縮與邊緣-雲端協同

**全名**:深度調查:2026 年端側輕量語言模型之即時語意壓縮與邊緣雲端協同推論架構

**核心技術詞彙**:

- Gemma 4 E2B/E4B — Per-Layer Embeddings (PLE) 稠密架構
- Llama 4 Scout — MoE 顯存陷阱
- WebAssembly 3.0 + WebGPU
- CogentLM, WebLLM — 瀏覽器推理引擎
- 35.5ms 首字延遲目標
- 硬提示詞壓縮 vs 軟提示詞
- 連續嵌入 (Continuous Embeddings)
- POST 框架 (Privacy of Soft Prompt Transfer)
- Vec2Text / Zero2Text 嵌入逆向攻擊
- Eguard — 基於文字互資訊優化的雙層防禦
- PRISM — 動態語意路由 (Edge-Cloud Collaborative Inference)

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M2.2 | Gemma 4 E4B 邊緣模型載入 |
| M1.6 | WebGPU + CogentLM 部署 |
| M2.2.2 | POST 框架意圖向量 |
| M2.4 | Eguard 防禦 + PRISM 路由 |
| M2.5 | PRISM 雲端-邊緣協同 |

**章節索引**:

- §1 SLM 架構演進
- §2 WebAssembly 3.0 + WebGPU
- §3 IDE 脈絡與螢幕焦點擷取
- §4 文字壓縮 → 意圖向量演進
- §5 嵌入逆向攻擊與 Eguard 防禦
- §6 PRISM 動態語意路由

**Claude Code 引用範例**:

```python
# [R07: POST §4.3] 將原始程式碼壓縮為意圖向量,絕對不傳明文
async def compress_to_intent_vector(raw_code: str) -> IntentVector:
    edge_model = await get_gemma_edge_client()
    soft_prompt = await edge_model.encode_to_soft_prompt(raw_code)
    return IntentVector(
        embedding=soft_prompt,
        # Eguard 確認剝離具體變數名稱
        stripped_entities=eguard_filter(soft_prompt)
    )
```

---

## R08 — 混合主動式介面之認知負荷、微干預、打斷管理、草稿與核准

**全名**:深度調查混合主動式介面之認知負荷:微干預、打斷管理與「草稿與核准」機制之實證研究

**核心技術詞彙**:

- 混合主動式介面 (Mixed-Initiative Interface)
- 認知負荷理論 (Cognitive Load Theory)
- 草稿與核准 (Draft & Approve) 機制
- 心理所有權 (Psychological Ownership)
- 適應悖論 (Adaptation Paradox)
- 破壞性打斷 + 恢復延遲 (Resumption Lag)
- 延遲至斷點 (Defer-to-Breakpoint)
- 警報疲勞 (Alert Fatigue) — 醫療級別介面設計
- 微干預 (Micro-Nudges)
- 微摩擦力 (Micro-Friction / Design Friction)
- System 1 vs System 2 思維切換
- 意圖與執行的脫鉤 (Decoupling Intentions from Execution)
- IKEA 效應 — 勞動轉化為價值
- 吉布斯反思循環 (Gibbs Reflective Cycle)

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M1.2 | 斷點偵測引擎 (Defer-to-Breakpoint) |
| M1.5 | 微 Nudges 引擎 |
| M3.3.3 | 草稿與核准彈窗 + 吉布斯反思 |
| M3.9 | 防疲勞通知儀表板 (警報疲勞) |
| M3.3.3.4 | 微摩擦力強制留白 |

**章節索引**:

- §一 認知負荷轉移與作者身分危機
- §二 任務斷點打斷管理
- §三 醫療級警報疲勞防範
- §四 微摩擦力的必要性
- §五 意圖脫鉤與作者身分五大設計模式
- §六 IKEA 效應與結構化反思

**Claude Code 引用範例**:

```typescript
// [R08: §四.2 微摩擦力] 強制留白欄位,觸發 System 2
const ReflectionForm = () => {
  const [userFeeling, setUserFeeling] = useState("");
  const [actionPlan, setActionPlan] = useState("");

  // [R08: §六.1 IKEA 效應] 必填,不可省略
  const isValid = userFeeling.length > 0 && actionPlan.length > 0;

  return (
    <form>
      {/* AI 已填補的客觀描述 (ai_description) 與初步分析 (ai_analysis) */}
      <textarea
        placeholder="主觀感受是什麼? (必填,我們不接受空白)"
        value={userFeeling}
        onChange={(e) => setUserFeeling(e.target.value)}
        required
      />
      {/* ... */}
    </form>
  );
};
```

---

## R09 — AI 數位擬人化與情感依附

**全名**:人工智慧的數位擬人化與情感依附:從建構虛擬同理心到驅動人類正向行為改變的系統架構與心理機制

**核心技術詞彙**:

- HAIA (Human-AI Information Attachment) — 三階段發展模型
- 擬社會偏好 (Parasocial Preference)
- Replika 案例:模擬同理心、人造親密感、道德邊界
- SDT (Self-Determination Theory) — 自決理論
- Fogg Behavior Model (FBM) — B = MAP (Motivation × Ability × Prompt)
- Woebot 系統設計 + 治療同盟數位突破
- BDI 框架 (Belief-Desire-Intention)
- 多代理人系統 (Multi-Agent Systems, MAS)
- 信任校準 (Trust Calibration)
- 病態使用風險

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M4.1 | LangGraph 多智能體系統設計 |
| M4.2.3 | SDT 自主、勝任、連結三需求 |
| M4.2.1 | BDI 信念-渴望-意圖建模 |
| (橫切) | 防範病態使用的倫理設計 |

**章節索引**:

- §第二章 擬人化心理機制
- §第三章 HAIA 三階段
- §第四章 SDT 在 AI 教練中的應用
- §第五章 Woebot 與治療同盟
- §第六章 MAS + ToM + BDI
- §第七章 後端資訊分析與對齊機制

---

## R10 — 融合 LLM 的半自動化個人行為記錄

**全名**:融合大型語言模型之半自動化個人行為記錄:從量化自我到質性自我的技術演進與深層心理學影響研究報告

**核心技術詞彙**:

- 量化自我 (Quantified Self) → 質性自我 (Qualitative Self)
- 記錄疲勞 (Recording Fatigue)
- 級聯架構 (Cascade Architecture) — 語音轉文字 → 解析 → 結構化
- 狀態機代理工作流 (Agent Workflow State Machine)
- 意圖驅動的支出追蹤
- MindScape — 反思動態鷹架
- MindfulDiary — 對話式精神狀態記錄
- CARE 評測基準 — 安全性與風險控管
- DiaryMate — 情緒代理權轉讓
- Narrating Fitness — 數據敘事化

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M3.3 | 日報結構化 (量化→質性) |
| M4.4 | 自然套問與 NER 抽取 |
| M3.8 | Wrapped Insights (敘事化) |
| M3.4.3.3 | 語音意識流輸入 |
| (跨層) | CARE 安全評測作為驗收 |

**章節索引**:

- §典範轉移
- §認知負荷消解
- §語音處理級聯架構
- §代理工作流狀態機
- §財務與飲食的無摩擦追蹤
- §MindScape 反思鷹架
- §對話式記錄安全性 (CARE)
- §敘事化福祉
- §自主權危機 (DiaryMate)

**Claude Code 引用範例**:

```python
# [R10: §對話式記錄 CARE] 偵測自傷意圖時,優先回應安全資源,延後紀錄
async def safe_log_voice_memo(transcript: str):
    if care_classifier.detect_self_harm(transcript):
        await trigger_safety_resource()  # 不寫入 raw_tracking_logs
        return SafetyEscalation()
    return await normal_processing_pipeline(transcript)
```

---

## 跨論文交叉引用速查

當你的模組會同時觸碰多個心理機制,以下是常見的多重引用組合:

| 場景 | 主引用 | 輔引用 |
| ---- | ------ | ------ |
| 偵測使用者狀態 | R02 (HMM) | R01 (BKT), R06 (Coping) |
| Persona 對話設計 | R03 (Echo Mode) | R05 (ToM), R09 (BDI) |
| 隱私資料壓縮上雲 | R07 (POST/Eguard) | R06 (差分隱私) |
| 圖譜建模 | R04 (DGNN) | R06 (薩提爾分層) |
| 日報草稿 | R08 (草稿與核准) | R10 (語音記錄) |
| ZPD 任務生成 | R01 (ZONE) | R02 (隱性狀態) |
| 防止 Persona 漂移 | R03 (ARPM) | R04 (NSVIF) |

## 引用衛生 (Citation Hygiene)

**禁止**:

- ❌ 「根據相關研究...」(無法驗證)
- ❌ 「研究顯示這樣做更好」(無編號)
- ❌ 引用整篇論文不指章節 (例如只寫 `[R03]`)
- ❌ 引用研究但程式碼實作偏離論文 (例如論文說 5 步漸進,實作直接跳變)

**必須**:

- ✅ `[R03: Echo Mode §3.2]` — 編號 + 關鍵字 + 章節
- ✅ 程式碼註解中明確說明本行如何體現該研究
- ✅ 若實作對研究有任何修改,寫明「偏離理由」並讓 Reviewer 核可

## 新增第 11 篇論文時的流程

未來若加入新研究:

1. 編號為 `R11`
2. 在本文件末追加完整條目 (沿用相同 schema)
3. 更新 `04_module_registry.md` 中對應模組的 Research 欄
4. 若觸發任何新風險,追加至 `05_integration_risk_audit.md`
5. 若改變某模組的引用,更新該模組的 SPEC.md References 區塊
