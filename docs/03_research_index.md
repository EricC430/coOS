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

> **2026-10-19 偏離紀錄 (使用者拍板 Q2,見 `M5_ICEBERG_REDESIGN.md` §13)**:雲端 Neo4j、DGNN、霍克斯過程不再落地;**圖模型保留**,冰山以本地 SQLite 邊表儲存,並以 networkx 做記憶體圖分析 (核心渴望、推理路徑,見設計稿 §4.6 / §6.3)。D-ALP 降級為 nucleus/satellite 證據權重,反溯因保留為「強制競爭假設 + 挫敗分數」。

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

## R11 — Park et al. 情節記憶與 Reflection 機制 (Generative Agents)

**全名**: Park et al., *Generative Agents: Interactive Simulacra of Human Behavior*, UIST 2023

**核心技術詞彙**:

- Memory Stream (情節記憶流)
- 檢索分數 = 新近性 (Recency) × 重要性 (Importance) × 相關性 (Relevance)
- Reflection (定期將觀察昇華為高階洞察)

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M4.2.2 | 記憶檢索與評分 |
| M6.4 | 夜間 Reflection 任務 |

**章節索引**:

- §3.1 Memory Stream (記憶流設計)
- §3.2 Retrieval (新近性、重要性、相關性檢索)
- §3.3 Reflection (定期觀察昇華)

**Claude Code 引用範例**:

```python
# [R11: Park et al. §3.2] score = a * recency + b * importance + c * relevance
score = alpha * recency_score + beta * importance_score + gamma * relevance_score
```

---

## R12 — Character-LLM 經歷寫入與保護 (EMNLP 2023)

**全名**: Shao et al., *Character-LLM: A Trainable Agent for Role-Playing*, EMNLP 2023

**核心技術詞彙**:

- Experience Upload (以「形成性經歷」定義角色)
- Protective Experiences (知識邊界——限制角色所知範圍，不知道就承認不知道)

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M4.2.1 | PersonaCard v2 形成性經歷與知識邊界 |

**章節索引**:

- §Experience Upload (經歷寫入)
- §Protective Experiences (知識邊界機制)

**Claude Code 引用範例**:

```python
# [R12: Character-LLM §Protective Experiences] 對知識邊界外的事物，承認不知道並轉介
if query_topic in config.knowledge_boundary.ignorant_of:
    return refer_to_other_expert(query_topic)
```

---

## R13 — PersonaLLM 五因子條件化生成

**全名**: Jiang et al., *PersonaLLM: Personality Temporal Dynamics in Large Language Models* / Big Five 條件化生成研究

**核心技術詞彙**:

- OCEAN 五因子人格向量 (OCEAN Vector)
- 條件化個性表達 (Conditional Personality Expression)
- 人格一致性評測 (Personality Consistency Evaluation)

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M4.2.1 | PersonaCard v2 五因子人格結構 |

**章節索引**:

- §Personality Conditioning (人格條件化)
- §OCEAN Representation (OCEAN 表達)

**Claude Code 引用範例**:

```python
# [R13: PersonaLLM §Personality Conditioning] 用結構化特質向量 (OCEAN) 定義人格
config = PersonaConfig(big_five={"O": 0.8, "C": 0.7, "E": 0.4, "A": 0.6, "N": 0.3})
```

---

## R14 — RoleLLM / RoleBench 一致性評測 (2023)

**全名**: Wang et al., *RoleLLM: Benchmarking, Eliciting, and Enhancing Role-Playing Abilities of Large Language Models*, 2023

**核心技術詞彙**:

- Role Profile (角色檔案結構)
- 身世拷問測試集 (RoleBench-style Evaluation)
- 量化角色扮演一致性 (Quantifying Role Consistency)

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M4.9 | ARPM-lite 拷問測試集生成與一致性監督 |

**章節索引**:

- §Benchmarking (評測基準)
- §Role Profile Construction (角色檔案建置)

**Claude Code 引用範例**:

```python
# [R14: RoleLLM §Benchmarking] 由 PersonaCard 自動生成身世拷問測試題
test_suite = generate_rolebench_questions(persona_card)
```

---

## R15 — MemGPT 分層記憶管理 (Letta / Mem0)

**全名**: Packer et al., *MemGPT: Towards LLMs as Operating Systems*, 2023 / Letta / Mem0 / LangGraph Store

**核心技術詞彙**:

- 分層記憶結構 (Tiered Memory Structure)
- Core Memory Blocks (核心唯讀記憶區)
- Archival Memory (封存記憶區)
- OS 式分頁換頁 (Memory Paging)

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M4.2.2 | 分層記憶與 [記憶區塊] v2 拼裝 |

**章節索引**:

- §Architecture (MemGPT OS 級架構)
- §Memory Management (記憶管理與分頁)

**Claude Code 引用範例**:

```python
# [R15: MemGPT §Memory Management] 分層記憶：Core Memory (限額 350 tokens) + Archival SQLite 檢索
core_memory = assemble_core_memory_block(goals, promises, top_memories)
```

---

## R16 — Motivational Interviewing 動機式晤談

**全名**: Miller & Rollnick, *Motivational Interviewing: Helping People Change*, 3rd Edition (臨床心理經典)

**核心技術詞彙**:

- OARS 技術組 (Open questions, Affirmations, Reflective listening, Summaries)
- 變化語句 (Change Talk) 辨識
- 滾動順應 (Rolling with Resistance)

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M4.2.2 | mi_selector 心理介入技術選擇器 |

**章節索引**:

- §OARS (開放式提問/肯定/反映式傾聽/摘要)
- §Change Talk (辨識與回放變化語句)
- §Rolling with Resistance (阻抗滾動順應)

**Claude Code 引用範例**:

```python
# [R16: Motivational Interviewing §OARS] 阻抗高時採用反映式傾聽並滾動順應，禁給建議
if reactance > 0.7:
    return ReflectiveListeningDirective()
```

---

## R17 — Working Alliance Inventory (WAI, 1989)

**全名**: Horvath & Greenberg, *Working Alliance Inventory* (WAI), 1989

**核心技術詞彙**:

- 治療同盟三成分 (Working Alliance Triad)
- 目標共識 (Goal Consensus)
- 任務共識 (Task Consensus)
- 情感連結 (Bond / Affective Bond)

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M4.2.1 | PersonaCard v2 治療同盟品質指標 |

**章節索引**:

- §Methodology (評估方法論)
- §Triad Dimensions (目標、任務與情感連結維度)

**Claude Code 引用範例**:

```python
# [R17: WAI §Triad Dimensions] 以目標共識、任務共識與情感連結作為專家品質指標
wai_score = evaluate_working_alliance(session_logs)
```

---

## R18 — Sycophancy Mitigation 反諂媚守則

**全名**: Sharma et al., *Towards Understanding Sycophancy in Language Models*, 2023

**核心技術詞彙**:

- 諂媚行為成因 (Sycophancy Etiology)
- 反諂媚守則 (Anti-Sycophancy Stances)
- 溫和堅持立場 (Gentle Position Stance)

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M4.2.1 | PersonaCard v2 Stances 與反諂媚系統提示詞 |

**章節索引**:

- §Etiology (諂媚行為成因分析)
- §Mitigation Strategies (諂媚行為緩解與反對立場設計)

**Claude Code 引用範例**:

```python
# [R18: Sycophancy Mitigation §Mitigation] 當使用者與 Stance 衝突時，溫和堅持立場，不可立刻倒戈
prompt += "If user view conflicts with your stance, acknowledge their logic but gently insist on your stance."
```

---

## R19 — sqlite-vec 本地向量擴充

**全名**: sqlite-vec: A vector search extension for SQLite

**核心技術詞彙**:

- 本地向量檢索 (Local Vector Search / Embedded Search)
- L1 隱私隔離 (L1 Privacy Isolation - 記憶明文不離端)
- 向量儲存格式 (Vector Embedding Formats)

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M6.1 | sqlite-vec 向量表定義與檢索 |
| M4.2.2 | 情節記憶本地向量相似度檢索 |

**章節索引**:

- §Vector Storage (SQLite 向量儲存)
- §Similarity Query (相似度檢索與 PRAGMA 配置)

**Claude Code 引用範例**:

```sql
-- [R19: sqlite-vec §Vector Storage] 本地向量檢索，確保明文不出 L1 端
SELECT id, content FROM m4_2_persona_memories WHERE vec_distance_cosine(embedding, :query_vec) < 0.35;
```

---

## R20 — The Satir Model (薩提爾模式原典)

**全名**: Satir, V., Banmen, J., Gerber, J., & Gomori, M. (1991). *The Satir Model: Family Therapy and Beyond*. Science and Behavior Books.

**核心技術詞彙**:

- 個人冰山 (Personal Iceberg) — 行為、應對、感受、感受的感受、觀點、期待、渴望、自我
- 五種應對姿態 (Placating / Blaming / Super-reasonable / Irrelevant / Congruent)
- 變化歷程 (Change Process) — 現狀 → 外來元素 → 混亂 → 整合 → 練習 → 新現狀
- 轉化而非消除 (Transformation, not elimination) — 應對姿態曾是生存資源

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M5.1 | 冰山八層 enum 的原典定義 (R04 的圖譜化版本以此為準) |
| M5.4 | 主題的 Satir 變化階段狀態機 |
| M5.5 | mode 2 碰撞 = 外來元素;mode 4 肯定姿態的正向用意 |

**章節索引**:

- §個人冰山 (冰山各層定義)
- §應對姿態 (五種姿態與一致性)
- §變化歷程 (六階段與混亂期的承接)

**Claude Code 引用範例**:

```python
# [R20: Satir Model §變化歷程] 混亂期禁止新的碰撞,只允許承接 (mode 4/5/12)
if theme.satir_phase == SatirPhase.CHAOS:
    allowed_modes = {4, 5, 12}
```

---

## R21 — 矯正性情緒經驗 (Corrective Emotional Experience)

**全名**: Alexander, F., & French, T. M. (1946). *Psychoanalytic Therapy: Principles and Application*. Ronald Press.

**核心技術詞彙**:

- 矯正性情緒經驗 — 在新的關係中經歷與過往預期不同的回應
- 關係作為介入 (Relationship as intervention)

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M5.5 | mode 5:在關係中直接滿足渴望,而非要求使用者先自我覺察 |

**章節索引**:

- §核心概念 (矯正性情緒經驗的定義)

**Claude Code 引用範例**:

```python
# [R21: 矯正性情緒經驗 §核心概念] 渴望被肯定的主題:肯定努力與過程,不以結果為條件
```

---

## R22 — 外化 (Externalization, 敘事治療)

**全名**: White, M., & Epston, D. (1990). *Narrative Means to Therapeutic Ends*. W. W. Norton.

**核心技術詞彙**:

- 外化對話 (Externalizing conversations) — 「問題才是問題,人不是問題」
- 共同命名 (Co-naming the problem)

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M5.5 | mode 8:與使用者共同為模式命名,之後以名字溝通 |

**章節索引**:

- §外化對話 (命名與分離人和問題)

**Claude Code 引用範例**:

```python
# [R22: 外化 §外化對話] 名字必須由使用者同意或提出,系統不可單方面命名
```

---

## R23 — 行為實驗 (Behavioural Experiments)

**全名**: Bennett-Levy, J., Butler, G., Fennell, M., Hackmann, A., Mueller, M., & Westbrook, D. (2004). *Oxford Guide to Behavioural Experiments in Cognitive Therapy*. Oxford University Press.

**核心技術詞彙**:

- 行為實驗 — 以具體行動檢驗一個信念的預測
- 預測 → 行動 → 觀察 → 反思 四步

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M5.5 / M3.13 | mode 9:小實驗提議與遙測判定 |

**章節索引**:

- §實驗設計 (預測、行動、觀察、反思)

**Claude Code 引用範例**:

```python
# [R23: 行為實驗 §實驗設計] 結果出來後由使用者反思,系統只提供觀察到的事實
```

---

## R24 — 改變階段模型 (Stages of Change)

**全名**: Prochaska, J. O., & DiClemente, C. C. (1983). Stages and processes of self-change of smoking: Toward an integrative model of change. *Journal of Consulting and Clinical Psychology, 51*(3), 390–395.

**核心技術詞彙**:

- 懵懂期 / 沉思期 / 準備期 / 行動期 / 維持期
- 準備度 (Readiness) 決定介入類型

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M5.5 | readiness 評分與 mode 12 策略性留白 |

**章節索引**:

- §階段定義 (五階段與對應介入)

**Claude Code 引用範例**:

```python
# [R24: 改變階段 §階段定義] 尚無 change talk (懵懂期) → 不提實驗,只做 mode 1/4/5
```

---

## R25 — 生成效應 (Generation Effect)

**全名**: Slamecka, N. J., & Graf, P. (1978). The generation effect: Delineation of a phenomenon. *Journal of Experimental Psychology: Human Learning and Memory, 4*(6), 592–604.

**核心技術詞彙**:

- 生成效應 — 自己產生的內容比被動閱讀的內容記得更牢

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M5.5 | mode 7 回聲與 mode 10 鞏固:讓使用者自己說出洞察與變化 |

**章節索引**:

- §實驗結果 (自我生成 vs 閱讀的記憶差異)

**Claude Code 引用範例**:

```python
# [R25: 生成效應 §實驗結果] 鞏固用問句讓使用者自述變化,不由系統宣告「你成長了」
```

---

## R26 — 社會學習理論:示範 (Modeling)

**全名**: Bandura, A. (1977). *Social Learning Theory*. Prentice Hall.

**核心技術詞彙**:

- 觀察學習 (Observational learning)
- 示範者 (Model) 的可信度與相似性

**主要供應模組**:

| 模組 | 引用點 |
| ---- | ------ |
| M5.5 / M4.2 | mode 6:專家以自己的 `iceberg_story` 示範一致與脆弱 |

**章節索引**:

- §觀察學習 (注意、保持、再現、動機四歷程)

**Claude Code 引用範例**:

```python
# [R26: 示範學習 §觀察學習] 示範故事必須與 persona card 一致 (ARPM 稽核),否則可信度崩潰
```

---

## 跨論文交叉引用速查


當你的模組會同時觸碰多個心理機制,以下是常見的多重引用組合:

| 場景 | 主引用 | 輔引用 |
| ---- | ------ | ------ |
| 偵測使用者狀態 | R02 (HMM) | R01 (BKT), R06 (Coping) |
| Persona 對話設計 | R03 (Echo Mode) | R05 (ToM), R09 (BDI) |
| 隱私資料壓縮上雲 | R07 (POST/Eguard) | R06 (差分隱私) |
| 冰山推論 | R04 (心理幻覺/反溯因) | R06 (應對姿態), R20 (原典) |
| 冰山介入 | R20 (變化歷程) | R16 (MI), R21–R26 |
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
