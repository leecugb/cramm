# 两张 GEMS 相图的模拟同行评审（nature-reviewer 技能）

> 评审日期：2026-08-23 ｜ 技能：nature-reviewer（本地克隆，三报告互盲 + 评审后综合）
> 对象：`D:\gems\results\diag111_muscovite_wv2200_application_en.png`（Figure A 白云母）、`D:\gems\results\user_tk_pos2250_contour.png`（Figure B 绿泥石）
> 被评主张："这两张相图为 CRAMM 的产品提供了标尺，第一次将光谱参数转换为二维地质指针"
> 评估边界：仅图件 + provenance 数据；无正文；无地面真值；文献核验不完整（网络受限）

## Review setup

- **Input scope**：两张相图 + provenance（chlorite_rebuild_model.csv / chlorite_rebuild_log.txt / user_tk_pos2250_field.csv / diag111_titration_guifree_mines23_ssX.csv）
- **Assessment boundary**：上图所述；正文、图注、白云母 14 样本标定明细、chl13 明细未入包
- **Shared manuscript claim summary**：经验光谱标定（wv2200 / Pos2250）经热力学成分场转绣到 T–log(aK⁺/aH⁺) 相图，为 CRAMM 逐像元 mus_center / chl_center 产品提供环境坐标读数
- **Visible evidence base**：三份冻结报告见 §R1/R2/R3
- **Missing materials affecting confidence**：白云母 wv2200–成分标定 provenance；热力学计算条件（P/体系/活度模型/DB 版本）；灰带成因；文献核查

---

## Cross-review synthesis（评审后综合；未向审稿人展示）

### 共识强项（三报告独立提出）

1. **概念组合是真实新元素**：经验光谱标定 × 热力学反应路径成分场 × 开源光谱软件产品的三层组合，在 packet 的 prior-art 锚点中未见先例（R1 strengths-1 / R2 strengths-1 / R3 strengths-1）。
2. **外推诚实性高于同类文献平均**：magenta 标定覆盖边界 + `in_calib` 逐格布尔列（21,905 行中 True 11,807，占 53.9%）（R1 strengths-2 / R2 strengths-4 / R3 strengths-2）。
3. **provenance 工程透明**：拟合日志、可靠性标记、LOsO-CV、灵敏度分析齐备，审稿人可逐步复核（R1 strengths-3 / R2 strengths-2–3）。
4. **跨学科吸引力真实**：勘查光谱、热液地球化学、热力学模拟三社区交集（三报告的 "Who would be interested" 一致收敛）。

### 共识阻断级关切（Blocking，≥2 报告独立提出）

| 综合键 | 来源 | 内容 | 关闭条件 |
|---|---|---|---|
| **C1 标量→二维不成立** | R1-M2 / R2-M6 / R3-M1（三报告全部 Blocking Yes） | 单标量在二维场上只确定一条等值线（一维约束流形），"二维地质指针"措辞必被驳倒 | 降级为"等值线约束"表述；或展示 mus_center × chl_center 双等值线联立求交的机制、前提（同 P 同体系、共生平衡假设显式声明）与不确定度 |
| **C2 不确定度未传播** | R1-M1（Blocking）/ R2-M2（Blocking）/ R3-M2（Major） | 端元系数 95% CI（Ames 宽 43.5 nm、Daph ±15.8 nm）数倍于整场动态范围（~11.8 nm），而等值线画成无宽锐线、colorbar 细分暗示不存在精度 | Monte Carlo/解析传播系数协方差 → 等值线改画为带或置信掩膜；报告典型读数的 ΔT/Δlog a |
| **C3 标尺与产品口径未对齐** | R1-M6（Blocking）/ R2-M8（Blocking） | 图 B 用 "CR 口径" Pos2250，CRAMM chl_center 提取协议未证明一致；图 A 等值线 2190–2215 nm 与产品仲裁窗 2195–2220 nm 双向错配；bridge（n=6, CV-RMSE 2.08）与 chl13（n=13, LOO 1.0）两套标定未调和 | 用 CRAMM 引擎对标定样本重提取、报告偏差；调和或选择两套标定并说明理由；等值线范围与产品量程对齐 |
| **C4 热力学计算条件缺失** | R2-M1（Blocking，唯一提出者；列为共识因 R1/R3 均将其列为材料缺失） | 压力、体系组成、流体 speciation、活度模型、数据库版本均未印在图上——等值线位置不可复核 | 图注补齐全部条件 + 至少两个压力/数据库版本的敏感性图 |

### 其他共识关切（Major，非阻断）

| 综合键 | 来源 | 内容 |
|---|---|---|
| C5 外推区视觉权重 | R1-M3 / R2-M4 / R3-M2 | 近半网格外推，低温近纯 daphnite 区整体外推；Ames 系数由单一样本 SMR-15 锚定（杠杆集中）；外推区须降饱和/斜纹 |
| C6 零端到端验证 | R1-M5 / R3-M4 / R2（not assessable 但列为必补） | 链两端各自有据，叠印读数从未对独立观测（流体包裹体、共生矿物温度计）检验；无真值时须提供内部一致性检验方案（如双矿物读数 T 相容性统计） |
| C7 "第一次"需收窄 | R1 originality / R2-M7 / R3 originality | 可辩护表述：首次将光谱标量等值线叠印于热力学 (T, 流体活度比) 稳定域图并落到开源光谱产品；Duke 1994 / Post & Noble 1993 / Cathelineau 谱系 / HyLogging 一维向量须写入对照 |
| C8 图 A 标定 provenance 缺失 | R3-M3 / R2-M2（附带） | wv2200↔X_Tschermak 的 14 样本标定数据集、拟合形式、RMSE 未随包；须与图 B 同等透明 |
| C9 灰带与缺行未解释 | R1-m2 / R2-M5（Major）/ R3-m3 | 325–360 °C 灰带为人工掩膜（titration 网格 T 连续）、field 网格缺 565–595 °C 多行；恰是浅成-中温热液过渡最有应用价值的温区 |

### 共识小修（≥2 报告）

图 B 中文标注 + "notes/16 定版桥式"内部代号（R1-m1 / R2-m1 / R3-m1）；colorbar 刻度与物理精度不匹配（R3-m2 / R2-M2 附带）；magenta 在两图编码不同含义（R3-m6，R1/R2 未提但值得采纳）；"2254" 标签裁切（R2-m2 / 前次图件审计）。

### 各审稿人侧重差异（真实分歧，不抹平）

- **R1（光谱学）**独有强调：覆盖多边形构造方法未文档化（R1-M3 附带、R1-m5）；NMNH83369 排除/保留判据需写明（R1-m3）。
- **R2（热力学）**独有强调：bridge 端元与热力学端元分数的**可通约性未证**（R2-M3，NNLS 退化 unmixing 点估计作自变量，SMR-14 取值越出可行区间）；Na 白云母（paragonite 组分）对 wv2200 的影响未处理（R2-m7）——这是三报告中最深的技术发现。
- **R3（遥感软件）**独有强调：场景尺度间断——碎屑 vs 自生成因、混合像元单峰假设、"无真值时应用故事靠什么成立"（R3-M4）；等值线走向与相界夹角逐点变化导致标尺分辨率空间不均（R3-M1 附带）。

### 意义判读（broad-interest readout）

Originality 中等偏上（组合新、组件旧）；Scientific importance 领域级实用增量（与 C&G 匹配，非范式级）；Interdisciplinary readership 是最强维度；Technical soundness **当前未建立**；Readability 图 A 接近可用、图 B 不可用。三报告一致结论：**Major revision，全部阻断项不要求新实验即可关闭（C6 的实证演示为强烈建议）**。

### 建立强论证前最重要的 5 件事

1. 主张降级为"等值线约束 + 联立求交前景"，或展示一次完整的双等值线交点定位（C1）；
2. 系数不确定度传播到两张图，等值线画成带（C2）；
3. CRAMM 引擎口径对标定样本重提取，调和 bridge 与 chl13（C3）；
4. 图注补齐热力学计算条件 + 压力/DB 敏感性（C4）；
5. 至少一种无真值内部一致性检验（双矿物读数 T 相容性统计）+ 碎屑/自生假设声明（C6）。

### Risk / unsupported claims

- "第一次将光谱参数转换为二维地质指针"——按现状不可保留（C1+C7）；
- "定量标尺"——在 C2/C3/C4 关闭前只能称"模型内解释框架"；
- 图 A 2190 nm 段与图 B 低温外推区的任何数值引用——标定域外，不可引用为读数。

---

## §R1 Reviewer 1 报告（冻结版，光谱学证据链视角）

评审对象：两张相图（Figure A 白云母 wv2200 应用图，Figure B 绿泥石 Pos2250 预测场）及其 provenance 数据。评审边界：仅图件与 provenance，无正文，无地面真值验证，文献核验不完整。评审视角：成像光谱/矿物光谱证据链。

### Overall assessment

这两张图的核心想法是把经验性的吸收中心标量（wv2200 约 2.2 µm，Pos2250 约 2.25 µm）叠印到热力学反应路径模型给出的 (T, log aK+/aH+) 相图上，从而把一维光谱指针升级为二维环境坐标。就概念而言，这是对既有"Al-OH 波长作为一维蚀变向量"范式的一次有意义的扩展，Figure B 中以 magenta 多边形显式标出标定覆盖区并允许 in_calib 布尔标记随网格输出，是诚实的做法，值得肯定。

但是，从光谱学证据链角度看，作者的中心主张（"第一次将光谱参数转换为二维地质指针"、为 CRAMM 产品"提供标尺"）目前不被所供材料支持。主要障碍有四个：其一，Figure B 的桥式标定仅 n=6，端元系数置信区间（Ames ±21.7 nm）宽于图面展示的整场动态范围（约 14 nm)，且化学解混存在秩亏非唯一性，未见不确定度向相图的传播；其二，单一标量在二维平面上给出的是一条等值线而非一个点，"二维坐标"主张在缺少附加约束时不成立；其三，"第一次"主张与 Duke (1994)、Post & Noble (1993)、HyLogging/TSG 一维蚀变向量实践、以及绿泥石 Pos2250↔Fe/Mg 既有标定之间的关系未被厘清，且文献核验超出本次评审能力；其四，无任何独立地面真值（流体包裹体测温、共生矿物温度计）对预测坐标做过检验。当前状态下，该贡献应定性为"概念示意加方法框架"，而非"定量标尺"。

### Who would be interested in the results, and why

直接读者群是勘查光谱学与蚀变填图社区（HyLogging/TSG 用户、EMIT/EnMAP/AVIRIS-NG 数据处理者），他们已经在用 wv2200 做一维向量解释，若二维化成立，可把经验性空间梯度转译为温度与流体成分梯度，这是该社区长期想要但缺工具的事情。其次是热液矿床与变质岩石学社区，绿泥石温度计（Cathelineau 谱系）和白云母 Tschermak 替代是他们的常用工具，光谱入口能降低成本。对 Computers & Geosciences 的软件方法论文定位而言，这两张图作为 CRAMM 产品的解释层展示是合适的；对更广义读者，吸引力取决于"标尺"是否真的定量，目前这一点未建立。

### Major strengths

1. 概念整合是真实的新元素。把经验光谱等值线直接叠印到热力学稳定域上，使光谱标量与 (T, log aK+/aH+) 两个环境变量同框可读，这一呈现方式在所供 prior-art 锚点中未被覆盖（锚点只覆盖标量到成分、或成分到温度的单跳关系）。
2. Figure B 的外推诚实性。magenta 标定覆盖边界与 user_tk_pos2250_field.csv 中逐格 in_calib 布尔列（21,905 行，True 11,807 行，占 53.9%）使读者能区分内插与外推，这在光谱标定应用文献中是高于平均水平的做法。
3. provenance 透明度。chlorite_rebuild_log.txt 逐记录给出可靠性标记（如 SMR-13.e 的 Pos2250_raw 标记为 False 并被聚合排除）、按样本聚合、秩检验（rank=3，零方向 2·Clin = Ames + ChlMg 解析验证）以及留一样本交叉验证（LOsO-CV），审稿人可以重建整条拟合链。
4. 灵敏度分析意识。模型 CSV 中给出 +NMNH83369 与 -SMR-15 两组灵敏度拟合，系数端点符号稳定（Daph、Ames 均为正位移），说明桥式方向性不依赖单一样本。

### Major Concerns

**R1-M1**（Major, Blocking: Yes, statistical-rigor / figures-and-tables）
Claim pointer: Figure B 的 Pos2250 预测场为 CRAMM 绿泥石产品提供定量标尺，色标 2242–2256 nm，等值线间隔 2 nm。
Evidence pointer: chlorite_rebuild_model.csv 第 2 行与 chlorite_rebuild_log.txt D/E 节，primary 拟合 n=6，Daph 系数 95%CI [2235.3, 2266.9]（±15.8 nm），Ames 系数 95%CI [2251.1, 2294.6]（±21.7 nm）；user_tk_pos2250_field.csv 整场动态范围约 14 nm。
Concern: 图面展示的空间结构（2 nm 间隔等值线、局部 2244 与 2252 闭合区）全部小于端元系数自身的不确定度。桥式系数的不确定度从未传播到预测场，图中无任何误差等值线或置信填充。以当前拟合强度，同一成分点的 Pos2250 预测值不确定度可达数 nm 到十数 nm，足以把任一等值线推移穿越整个图面。定量"标尺"读数在此不确定度下不成立。
Why it matters: 中心主张是"标尺"。标尺的刻度线若比刻度本身的不确定度还细，图面给出的定量印象是误导性的。
Resolution test: 将端元系数协方差通过桥式与 GEMS 成分场传播，给出逐格 Pos2250 预测标准差图层，并在主图或副图中展示；或以 bootstrap/Monte Carlo 重采样拟合系数生成等值线位置包络。若传播后等值线位置不确定度小于 2 nm 间隔，本关切自动关闭；否则需降低图面定量精度表述。

**R1-M2**（Major, Blocking: Yes, claim-moderation / causal-vs-correlative）
Claim pointer: "第一次将光谱参数转换为二维地质指针"，即标量转换为 (T, log aK+/aH+) 二维坐标。
Evidence pointer: Figure A 中 wv2200 magenta 等值线（2190–2215）在白云母稳定域内近似平行于 X_Tschermak 等值线走向；Figure B 同理。两张图中任一标量值对应的都是一条贯穿稳定域的曲线，而非一个点。
Concern: 数学上，单个标量到二维平面的映射是一到多的。等值线上所有 (T, log aK+/aH+) 组合给出同一 wv2200 读数。要把标量升级为二维坐标，必须引入第二条独立约束（例如共生矿物对的第二个吸收中心联立、假设的流体演化路径、或独立温度计）。所供材料未展示任何此类联立机制，也未在图上或 provenance 中说明读图协议。
Why it matters: "二维指针"是标题级主张。若实际交付的是"一维等值线族叠印在二维场上"，其价值仍然真实但性质不同，主张必须降级或补上证成联立可解性的机制。
Resolution test: 二选一。(a) 展示 mus_center 与 chl_center（或 wv2200 与 Pos2250）联立在同一相图框架下给出唯一或近似唯一交点的实例与可解性分析；(b) 将主张改写为"把光谱标量投影为相图上的一维等值线约束"，并明确读出二维坐标所需的附加假设。

**R1-M3**（Major, Blocking: No, experimental-design / data-resource-quality）
Claim pointer: Figure B 预测场覆盖整个绿泥石稳定域并可作为产品标尺使用。
Evidence pointer: user_tk_pos2250_field.csv 21,905 行中 in_calib=False 占 46.1%；Figure B 图面中 magenta 覆盖多边形之外（包括几乎全部 T > 500 °C 区域与右侧高 log 比值区）仍以连续色填充展示，图例仅以"区外=外推"一句带过。
Concern: 近半网格点处于对 n=6 拟合的外推。图面虽然画了边界，但外推区与内插区使用完全相同的色标与等值线视觉权重，读者的第一视觉印象是全场同等可信。此外标定样本成分（绿泥石端元分数来自秩亏解混，Clin_lo/Clin_hi 区间普遍很宽，如 NMNH83369 Clin ∈ [0, 0.856]）与 GEMS 网格成分之间的对应关系未在所供材料中证明，覆盖多边形的构造方法未见文档。
Why it matters: 对勘查用户，图中视觉上最抢眼的高 Pos2250 红色核区与高温区恰恰部分是外推区，而外推误差对线性端元模型是无界的。
Resolution test: 外推区改为斜线纹、降饱和或留白，仅在覆盖区内保留全色标；补充覆盖多边形从 6 个样本端元分数到 (T, log aK+/aH+) 平面的构造方法说明；报告覆盖区内外的分别交叉验证误差估计。

**R1-M4**（Major, Blocking: No, reproducibility / experimental-design）
Claim pointer: Figure B 采用的 3 端元桥式（2243.7·Clin* + 2255.5·Daph + 2263.4·Ames）是绿泥石产品的标定基础。
Evidence pointer: 评审包 context facts 指出另存在 chl13 闭式标定（n=13，LOO-RMSE 1.0 nm，参数化为 xAl/xFe/xMg），与桥式不同；chlorite_rebuild_model.csv 显示桥式 primary n=6、LOsO-CV RMSE 2.08 nm。
Concern: 在同一产品体系内存在两条互不一致的绿泥石标定，而 headline 图选择了样本量更小、交叉验证误差更大的那一条，所供材料未给出选择理由，也未展示两条标定在同一相图上产生的预测场差异。若 chl13 标定代入同一 GEMS 成分场，等值线形态可能与 Figure B 显著不同，则"标尺"的形状本身依赖标定选择。
Why it matters: 证据链要求标定选择可辩护。两套标定并存且未调和，读者无法判断 Figure B 的结构是成分场的性质还是拟合伪影。
Resolution test: 给出桥式相对 chl13 的选择依据（例如端元参数化与 GEMS 输出成分的直接对应性），或并排展示两条标定生成的预测场并量化差异；若差异不可忽略，需说明哪一个进入 CRAMM 产品链路。

**R1-M5**（Major, Blocking: Yes——针对"定量标尺"作为已确立结论的表述；mechanism-evidence）
Claim pointer: 两张相图为 CRAMM 逐像元产品提供标尺，即产品读数可经图读回 T 与流体 log(aK+/aH+)。
Evidence pointer: 评审边界声明"no ground-truth validation exists"；所供 provenance 中无任何独立温度或流体成分观测与图上预测的对比。
Concern: 整条链是"经验标定（n=6 或 n=14）→ 热力学模型场 → 叠印"。链的两端各自有依据，但叠印后的读数从未对任何独立观测验证。白云母端 wv2200↔Tschermak 关系来自 14 样本经验标定，X_Tschermak 场来自 MINES23.1 热力学模型，两层模型误差如何叠加、模型固溶体假设是否覆盖天然白云母/绿泥石成分，均无检验。
Why it matters: 没有端到端验证，"标尺"目前是自我一致的模型内映射，其对天然样品的读数正确性未知。这不妨碍方法学发表，但决定主张的措辞等级。
Resolution test: 至少一个实证演示：对具有独立温度与流体成分约束（流体包裹体、共生矿物温度计）的天然样品或钻孔 HyLogger 剖面，展示光谱读数经相图反演的结果与独立约束的一致性；或将主张明确限定为"模型内映射与解释框架"，并在图中标注未经地面真值校准。

**R1-M6**（Major, Blocking: Yes, data-resource-quality / reproducibility）
Claim pointer: 两张图"为 CRAMM 的产品提供标尺"，即图中等值线与 CRAMM 逐像元 mus_center、chl_center 输出可直接对接。
Evidence pointer: context facts 指出 CRAMM 白云母仲裁窗口为 2195–2220 nm；Figure A 中等值线覆盖 2190–2215 nm，稳定域内大片区域（a1 边界附近高温侧）wv2200 < 2195 nm；Figure B 标题注明"CR 口径"，而 chlorite_rebuild_log.txt 中 Pos2250_CR 来自特定 continuum-removal 协议，所供材料未证明该协议与 CRAMM chl_center 的带提取算法（光谱分辨率、连续统定义、拟合方式）一致。
Concern: 两个口径错配风险。第一，Figure A 相当部分稳定域的预测 wv2200 落在 CRAMM 白云母判定窗口之外，意味着按 CRAMM 自身规则这些区域的产品可能不会被归类为白云母或 mus_center 输出被窗口截断，标尺的有效读数域与图面展示域不一致。第二，标定光谱的提取口径（NIC4 与 ASDNG 仪器混合、特定 CR 协议）与 CRAMM 引擎的逐像元口径若存在系统性偏移（即使 1 nm 量级），直接读图会产生系统性温度偏差，而 1–2 nm 在此正是等值线间隔量级。
Why it matters: "为产品提供标尺"要求产品与标尺同口径。口径未对齐的标尺会产生难以察觉的系统误差。
Resolution test: 用 CRAMM 引擎本身对标定样本光谱（或重采样到 CRAMM 目标波段后）重新提取 mus_center/chl_center，报告与图中等值线口径的偏差及窗口截断率；在图上标出 CRAMM 窗口对应的有效读数区。

### Minor Comments

**R1-m1**（Minor, writing-clarity / figures-and-tables）Figure B 全部图内文字为中文且副标题含内部笔记字样"notes/16 定版桥式"→ 统一英文，删除内部标记。
**R1-m2**（Minor, figures-and-tables）两图灰色水平带（约 320–365 °C）无解释 → 图例或图注说明含义（图注未随包提供，AUTHOR_INPUT_NEEDED）。
**R1-m3**（Minor, reproducibility）NMNH83369 的排除/灵敏度包含判据需在方法中一句写明。
**R1-m4**（Minor, figures-and-tables）Figure B 场值范围（2242–2256）窄于端元跨度（Ames 2263.4），未给成分等值线 → 叠加 X(Daph)/X(Ames) 等值线或图注给出端元分数场内范围。
**R1-m5**（Minor, data-resource-quality）in_calib 判定算法（凸包？距离阈值？）未文档化 → 方法中给出定义。

### Technical failings that must be addressed before the case is established

1. 不确定度传播缺失（R1-M1）。2. 标量到二维坐标的一到多映射未解决（R1-M2）。3. 零地面真值验证（R1-M5）。4. 标定口径与 CRAMM 产品口径未对齐（R1-M6）。5. 两条并存绿泥石标定未调和（R1-M4）。

### Assessment against Nature-style criteria

Originality: 中等偏上但主张超额。新元素是"光谱等值线与热力学相图的耦合呈现"，这一具体组合在所供 prior-art 锚点中未见。但标量到成分（Duke 1994、Post & Noble 1993、Laakso 等 Pos2250↔Fe/Mg)、成分到温度（Cathelineau 谱系）、以及标量作为空间蚀变向量（HyLogging/TSG、van Ruitenbeek、Yang & Huntington）均为既有工作。"第一次将光谱参数转换为二维地质指针"的表述无法在包内核验（标记 AUTHOR_INPUT_NEEDED），且按现有锚点判断，更站得住的表述是"首次将光谱标量等值线叠印于热力学 (T，流体成分) 稳定域图用于联合解释"。

Scientific importance: 领域内实用性明确（勘查光谱社区会立即使用），但"杰出重要性"未建立；在二维化可解性与地面真值验证补上之前，属于有潜力的方法学进展而非已确立的工具。

Interdisciplinary readership: 对光谱学与热液地质两个社区的交叉读者有真实吸引力；对更广读者，故事依赖"遥感像元直接读温度与流体化学"这一承诺，而该承诺目前未兑现。

Technical soundness: 未建立。n=6 标定、宽系数 CI、秩亏解混、无不确定度传播、无独立验证、口径未对齐，五项叠加使定量结论目前不成立。

Readability for nonspecialists: 概念直观（等值线读图），是优点；但 Figure B 中文标注、灰带无解释、成分驱动不可见，降低了可及性。

### Recommendation posture

Major revision。作为 Computers & Geosciences 软件方法论文的解释层展示，这两张图有真实价值，概念扩展值得发表。但 (1) "第一次"主张必须收窄到可辩护的具体组合并补充文献核验，(2) "定量标尺"主张必须在完成不确定度传播、二维可解性说明、口径对齐与至少一个实证演示之前降级为"模型内解释框架"。R1-M1、R1-M2、R1-M5 为 blocking；解决后本文可成为勘查光谱社区有用的参考。

（评审边界声明：本报告仅基于两图与三份 provenance 文件；正文、图注、14 样本白云母标定明细、chl13 标定明细未提供，凡涉及处均已标注 AUTHOR_INPUT_NEEDED 或 not assessable。）

---

## §R2 Reviewer 2 报告（冻结版，热力学建模视角）

评审对象：两张相图与 provenance 数据，不涉及 manuscript 正文，不做 ground truth 验证，文献核验不完整。以下所有判断均锚定在 packet 材料上。

### Overall assessment

这两张图把 CRAMM 的 mus_center（约 2.2 µm）与 chl_center（约 2.25 µm）标量嵌入 T 对 log(aK+/aH+) 的热力学相图框架，概念上是经验光谱标定与 reaction-path 模拟固溶体成分场的一次真实综合，对 Computers & Geosciences 的软件方法论文而言是有说服力的应用展示方向。但是以地球化学审稿标准衡量，目前这把"标尺"尚不能读数。压力与体系条件未印在图上，经验标定链接到热力学成分场的合法性未证明，标定不确定度未传播（图 B 全场动态范围约 11.8 nm，而 Ames 端元系数的 95% CI 宽 43.5 nm），46% 的网格为外推，325 至 360 °C 灰带两图均未解释，单标量定二维坐标所必需的共存平衡假设从未声明，"第一次"的优先权表述超出 packet 可核验范围。建议 major revision。

### Who would be interested in the results, and why

高光谱蚀变填图与找矿勘查社区（white mica wv2200 与 chlorite Pos2250 指标的使用者），因为该图若成立可把日常产出的波长标量直接翻译成温度与流体活度比。地热与热液矿床研究者，因为 200 至 600 °C 正是热液蚀变的核心温区。GEMS/SUPCRT 系列的 reaction-path 建模者，因为把固溶体成分场与可观测光谱量耦合是该社区一直在做但很少落到遥感产品的事。C&G 读者中关心光谱软件如何落地为地质解释工具的人群。

### Major strengths

1. 概念综合有真实价值。把经验 wv2200 标定经 X_Tschermak 场、把三端元 bridge 经 X(Clin*)/X(Daph)/X(Ames) 场叠加到同一类活度图上，使相图从定性稳定域升级为可叠加光谱等值线的定量工具，packet 内未见先例，对软件论文是恰当且亮眼的应用。
2. 工程透明度高。21,905 行 field 网格、30,082 行 titration 网格、bridge 拟合日志与 model CSV 齐备，审稿人可以逐步复核从光谱到相图的每一环。
3. 作者已自觉做 leave-one-sample-out CV、样品 sensitivity（增删 NMNH83369、SMR-15）并标记 CR artifact，方法态度严谨。
4. in_calib 布尔列与图 B 的标定覆盖边界是良好实践，公开承认外推存在。
5. 图 A 的视觉组织清晰，相边界、成分色标、光谱等值线三层信息可读。

### Major Concerns

**R2-M1**（Major, Blocking: Yes, reproducibility / technical soundness）
Claim pointer: 相图为 CRAMM 产品提供定量标尺，可读 T 与 log(aK+/aH+)。
Evidence pointer: 两张 PNG 全图无压力、体系初始组成、流体 speciation、固溶体活度模型、数据库版本信息；数据库版本 MINES23.1 仅见于文件名。
Concern: a1/a2 边界与 X_Tschermak 场的位置对压力、体系组成、活度模型与数据库版本敏感，这是 SUPCRT 家族文献的常识。缺这些条件，等值线位置不可复核，标尺不可复现。
Why it matters: 定量标尺的核心交付物是可复现的等值线位置。压力改变会使 muscovite 稳定域与等值线整体平移，读者无法判断图中读数对应哪个 P。
Resolution test: 图题或图注给出压力（或等压条件）、初始体系组成、流体 speciation 处理、固溶体活度模型、数据库版本；补充至少两个压力或两个数据库下等值线位移的敏感性图，量化标尺对 P 的依赖。

**R2-M2**（Major, Blocking: Yes, statistical-rigor）
Claim pointer: 等值线提供可读的二维坐标。
Evidence pointer: chlorite_rebuild_log.txt D/E 节与 chlorite_rebuild_model.csv，Ames 系数 95% CI [2251.1, 2294.6]（宽 43.5 nm），Daph ±15.8 nm，CV-RMSE 2.08 nm；对 user_tk_pos2250_field.csv 的核算显示全场 Pos2250 动态范围仅 2243.85 至 2255.67 nm（11.8 nm）；图 A 的 14 样 wv2200 标定的拟合质量在 packet 中完全未给出；两图等值线均画成无宽度锐线。
Concern: 标定系数不确定度未向成分场与等值线传播。端元系数的 CI 宽度数倍于全图动态范围，传播后等值线带在 Daph 或 Ames 富集区将与等值线间距同量级甚至更宽。
Why it matters: 没有不确定度的等值线会给出虚假的读数精度。"标尺"主张的核心是可读数，而当前材料无法回答读数的 ΔT 与 Δlog(aK/aH) 有多大。
Resolution test: 用 Monte Carlo 或解析方法把系数协方差经成分场传播到 Pos2250 与 wv2200 场，以等值线带或置信度掩膜重绘两图，报告典型读数的不确定度，并标出读数不可靠区域。

**R2-M3**（Major, Blocking: Yes, mechanism-evidence / experimental-design）
Claim pointer: bridge 公式可合法地施加到热力学计算的固溶体成分上（图 B 标题即为此链式做法）。
Evidence pointer: chlorite_rebuild_log.txt C 节：4 端元化学空间 rank=3，存在解析零空间方向 2*Clin == Ames + ChlMg；SMR-14 拟合取值 Clin=0.421 而同行可行区间 Clin_hi=0.026，dMg=-68.4，rms3=18.7；NMNH83369 行 dMg=-1.29、rms3=10.4；SMR-15 行 lo/hi 为 NaN；Clin*（带星号）在 packet 中无定义。
Concern: 作为 bridge 自变量的成分本身是退化 unmixing 的点估计，可行区间与取值在 SMR-14 上明显脱节，这一自变量不确定度未进入拟合。同时，NNLS 端元（拟合天然样品化学成分）与热力学端元分数 X_Clin_star/X_Daph/X_Ames 的可通约性只是被假设，未被论证。
Why it matters: 若自变量存在系统偏移或端元定义错位，整张预测场会带系统性偏置而非随机噪声，图 B 的每个读数都可能整体平移。
Resolution test: 给出 Clin* 的定义与从 4 个热力学端元到 3 个 bridge 端元的映射公式；用可行区间端点重跑 bridge 得到系数包络并展示对预测场的影响；若不可行，则收窄主张并限定标尺的成分适用范围。

**R2-M4**（Major, Blocking: No, statistical-rigor / claim-moderation）
Claim pointer: 图 B 预测场在全图范围内具有同等的读数权威。
Evidence pointer: chlorite_rebuild_log.txt，n=6 主拟合 3 个端元系数，去掉 SMR-15 后 Ames 由 2263.4 变 2266.9、CV-RMSE 由 2.08 变 3.83 nm；对 user_tk_pos2250_field.csv 的核算显示 in_calib=False 占 46.1%，且 T=200 °C 时 log ratio 低于约 3.1 的全部格子（即近纯 daphnite 区，X_Daph≈1.0）均在标定之外。
Concern: Ames 系数实质由唯一 Ames 富集样品 SMR-15（X_Ames=0.527）锚定，杠杆集中；近半网格为外推，低温左半区整体外推，但图面视觉权重与标定内区域相同。
Why it matters: 外推区与外推区内的单样品杠杆端元叠加，使图 B 低温区的读数可靠性远低于图面暗示的水平。
Resolution test: 对外推区降低视觉权重（斜纹或灰化），文中给出外推区读数的可靠性分级，讨论 Ames 端元的单样品杠杆问题。

**R2-M5**（Major, Blocking: No, figures-and-tables / reproducibility）
Claim pointer: 相图在 200 至 600 °C 全域提供连续标尺。
Evidence pointer: 图 A 与图 B 均在约 325 至 360 °C 出现灰带且无任何解释；图 A 中 a1 边界在带下缘出现缺口；对 diag111_titration_guifree_mines23_ssX.csv 的核算显示 T 在 200 至 600 °C 连续（201 个 T 值），说明灰带是人为掩膜或后处理排除而非数据缺失；user_tk_pos2250_field.csv 另缺 565、570、571、573 至 595 °C 等 T 行。
Concern: 灰带来源不明（收敛失败、近临界水排除、活度模型切换均有可能），且该温区恰是浅成低温至中温热液过渡，是标尺应用价值最高的区段之一。
Why it matters: 标尺在最想用的温区断开且无理由，读数链断裂；不透明的掩膜也损害可复核性。
Resolution test: 说明灰带与缺行的排除标准与物理或数值原因，尽量补全或在图上明示该区不可读。

**R2-M6**（Major, Blocking: Yes, mechanism-evidence / claim-moderation）
Claim pointer: 光谱标量被转换为二维地质坐标 (T, log(aK+/aH+))。
Evidence pointer: 两张 PNG 与全部 provenance 文件中均无共存平衡假设的声明；titration 网格为 2 °C 步长而 field 网格为 1 °C 步长且缺行，两网格采样不同；条件未印出（见 R2-M1）。
Concern: 单个 wv2200 值在图 A 上只对应一条等值线，即一系列 (T, log ratio) 对，数学上欠定。得到二维读数必须假设同一像元内 muscovite 与 chlorite 与同一流体在同一 P、T 下平衡共存，用两条等值线相交。该假设集未在任何地方声明，且两图须处于同一压力与体系组成下才可相交，这一点无法从 packet 验证。
Why it matters: 这是"二维指针"主张的逻辑核心。缺声明与同前提保证，则主张本身不成立，只能说是两条各自欠定的一维约束。
Resolution test: 明确写出共存平衡假设、同 P 同体系前提，给出相交读数的示意流程与不确定度，讨论天然样品中非平衡与多期次白云母的风险，必要时把主张降级为一维约束的联合图示。

**R2-M7**（Major, Blocking: No, novelty-significance / claim-moderation）
Claim pointer: "第一次将光谱参数转换为二维地质指针"。
Evidence pointer: packet 给出的 prior-art 锚点：wv2200 与 Tschermak 的经验关系自 Duke (1994)、Post & Noble (1993) 已存在；chlorite 化学温度计（Cathelineau 1988 谱系）成熟；GEMS/SUPCRT 活度图是标准实践。packet 内无任何与这些 prior art 的对照。
Concern: 新颖性被断言而未被区分。真正新的部分是"把经验标定链接进热力学成分场并叠加到开源光谱软件产品"这一工程组合，而非光谱到地质坐标的转换概念本身。
Why it matters: 优先权表述超出证据，审稿阶段会被文献核验直接挑战，损害整篇可信度。
Resolution test: 将主张改写为可辩护形式，例如首次在开源高光谱决策系统产品上叠加热力学 T 与流体活度比坐标，并附一段与上述 prior art 的最小对照。文献核验本身超出本报告范围。

**R2-M8**（Major, Blocking: No, experimental-design / statistical-rigor）
Claim pointer: 该标尺适用于 CRAMM 的 mus_center 与 chl_center 产品。
Evidence pointer: 图 B 标题明示 "CR 口径"（continuum removal），而 CRAMM 的 chl_center 提取协议在 packet 中未展示；packet 上下文事实第 4 条指出项目内另存在 chl13 闭式标定（n=13，LOO-RMSE 1.0 nm，xAl/xFe/xMg 参数化），与 bridge 不同。
Concern: 若 CRAMM 产品的标量与 Pos2250_CR 之间存在系统性偏移，所有读数整体平移。bridge 与 chl13 两套并存的成分-波长关系何者为准未定。
Why it matters: 标尺的刻度必须与它所服务的产品用同一协议定义，否则尺子与对象不匹配。
Resolution test: 在同一批样品上比较 CRAMM chl_center 与 Pos2250_CR 的偏差与散布；调和或选择 bridge 与 chl13 并说明并存理由。

关于 ground-truth 验证（用独立温度或流体约束的天然样品检验标尺），按本次评估边界标记为 Not assessable from provided material，但这是地球化学审稿人信任标尺前必然会要求的证据，列入必须补齐项。

### Minor Comments

**R2-m1**（Minor, figures-and-tables）图 B 中文标注 + "notes/16 定版桥式" + "CR 口径" 未定义 → 出正式英文版图并定义术语。
**R2-m2**（Minor, figures-and-tables）图 B 多条细黑线未入图例；"2254" 标签被裁切；两图底色区块无图例 → 补全图例或图注解释所有线型与底色。
**R2-m3**（Minor, figures-and-tables / data-resource-quality）图 A colorbar 至 0.40 而网格最大 0.3516；高 X_Tschermak 核区无 wv2200 等值线；等值线止于 2215 nm 而产品窗至 2220 nm → 对齐色标与等值线量程。
**R2-m4**（Minor, claim-moderation）图 A 2190 nm 等值线低于产品可输出范围 → 标注或裁剪。
**R2-m5**（Minor, reproducibility）field 网格缺 565–595 °C 多行，筛选规则未文档化 → 文档化。
**R2-m6**（Minor, figures-and-tables）覆盖多边形与 in_calib 标志局部不一致（高估覆盖）→ 严格对齐或声明为近似。
**R2-m7**（Minor, data-resource-quality）titration 网格 muscovite 端元仅 Celadonite、Fe-Celadonite、Muscovite 三项；Na 白云母（paragonite 组分）对 wv2200 的影响未处理；n_pg 列身份未文档化 → 说明排除理由。

### Technical failings that must be addressed before the case is established

1. 图上或图注给出压力、体系组成、流体 speciation、活度模型、数据库版本 + 压力/DB 敏感性（R2-M1）。2. 标定不确定度传播，等值线改画为带（R2-M2）。3. 证明 bridge 端元与热力学端元分数可通约（R2-M3）。4. 声明共存平衡假设与同 P 同体系前提（R2-M6）。5. 解释灰带与缺行（R2-M5）。6. 证明 CRAMM 产品标量与 Pos2250_CR 口径一致，调和 bridge 与 chl13（R2-M8）。7. 补充独立自然约束下的验证（强烈建议，受边界限制）。8. "第一次" 降级（R2-M7）。

### Assessment against Nature-style criteria

Originality：中等偏上。各组件均为成熟工具，新颖性在于把三者链接并落到开源光谱产品上的工程组合。packet 内未见先例，但 "第一次" 的强表述未被支撑。
Scientific importance：field-local。对高光谱勘查与热液蚀变社区有实用价值，对地球化学整体不构成范式级推进。对 C&G 的软件方法定位而言重要性与期刊匹配。
Interdisciplinary readership：光谱遥感、勘查地质、热液地球化学三个社区都能读懂动机，交叉性真实存在，是本文较强的维度。
Technical soundness：目前不成立。R2-M1 至 R2-M3 与 R2-M6 为 blocking。
Readability for nonspecialists：图 A 组织良好；图 B 存在中文标注、内部引用、未入图例线型与未定义术语，非专业读者无法独立完成读数流程。

### Recommendation posture

Major revision。所有 blocking 项均可通过补充报告、误差传播分析与主张降级解决，不要求全新实验（ground-truth 验证为强烈建议但受本次评估边界限制）。若作者完成上述修正，这两张图可以成为该软件论文有说服力的应用亮点；按现状，"定量标尺" 与 "二维地质指针" 的表述超出证据，不可接受。

---

## §R3 Reviewer 3 报告（冻结版，遥感软件应用视角）

评审对象：两张相图（Figure A 白云母 wv2200 应用图；Figure B 绿泥石 Pos2250 预测场）及其 provenance 数据，针对声明"这两张相图为 CRAMM 的产品提供了标尺，第一次将光谱参数转换为二维地质指针"。目标期刊 Computers & Geosciences（软件方法论文，图置于 Discussion/Application 作为解释框架）。评审边界：仅图件与 provenance，无正文，无地面真值，文献核验未完成。

### Overall assessment

这两张图的核心价值是真实存在的。它们把 CRAMM 逐像元的吸收中心标量产品（mus_center、chl_center）放进一个由 GEMS/MINES23.1 反应路径模拟给出的热力学坐标系（T 与 log(aK+/aH+)），使一个软件产品从"矿物分类器"升级为"成分与成因环境制图工具"。对 Computers & Geosciences 的读者群而言，这正是让软件方法论文具有地质学意义的那类解释框架，方向正确，图示本身也基本诚实（Figure B 明确画出了标定覆盖边界并标注区外为外推）。

然而，以目前的形式，作者的核心声明站不住。一个标量对着一张二维相图读数，得到的不是二维坐标点，而是一条等值线（一维约束）；要从等值线收缩到 (T, log a) 点，需要第二个独立观测量或对一个坐标轴作假设。"二维地质指针"的表述超出了证据。此外，Figure B 视觉权重最大的区域（daphnite 主导的红色叶瓣）位于标定覆盖区之外，且端元系数的置信区间（Daph [2235.3, 2266.9]，Ames [2251.1, 2294.6]）远大于产品本身的 1 nm 级精度，图面没有传播这种不确定性。Figure A 的 wv2200 等值线的经验来源（波长对 X_Tschermak 或 Si p.f.u. 的标定关系及其误差）不在评审包内，无法核验。综合判断为 major revision：框架值得发表，声明需要降级，不确定性需要上图。

### Who would be interested in the results, and why

三类读者。第一，EMIT/EnMAP 时代的星载高光谱应用群体，他们已有的矿物填图产品缺少成因解释层，这两张图提供了一个现成的解释模板。第二，热液蚀变与勘查地质群体，他们熟悉 Al-OH 波长作为一维勘查向量（HyLogging/TSG 传统），会关心把一维向量升级为与活度-温度坐标挂钩的读数方式，哪怕只是等值线级别的约束。第三，热力学模拟与光谱学的交叉群体，Figure B 的"经验桥式叠加在热力学固溶体成分场上"是一种可复用的方法组合。跨学科吸引力是真实的，但取决于作者能否把声明校准到证据允许的范围。

### Major strengths

1. 概念组合有新意。把反应路径模拟的矿物固溶体成分场与经验波长-成分标定桥接，再用于解释逐像元光谱产品，据评审包信息这是 CRAMM 产品体系内的首次实现，且与开源软件的定位形成一致的整体贡献叙事。
2. 图面设计体现了方法论自觉。Figure B 用 magenta 虚线多边形显式区分标定内与外推区，user_tk_pos2250_field.csv 中有对应的 in_calib 逐点标记，这种诚实的边界标注在同类应用图中并不常见，应当保留并强化。
3. 两张图共用同一套 a1/a2 相界坐标系，白云母与绿泥石两个产品可以放进同一个解释框架，为后续多矿物联合约束预留了结构。
4. 产品端的工程纪律（chl13 标定 LOO-RMSE 1.0 nm，arbitration 窗口容差 1 nm）为"波长可测准"这一前提提供了支撑，使讨论可以聚焦在桥式模型与热力学场的不确定性上。

### Major Concerns

**R3-M1**（Major, Blocking: Yes, claim-moderation）
Claim pointer: "第一次将光谱参数转换为二维地质指针"，即标量吸收中心可被读作 (T, log(aK+/aH+)) 二维坐标。
Evidence pointer: Figure A 中 magenta wv2200 等值线（2190 至 2215 nm）为曲线族；Figure B 中 Pos2250 等值线（2244 至 2252 nm）同为曲线族。
Concern: 单个标量读入二维相图，数学上只能定位到一条等值线，即二维空间中的一维约束流形，而不是一个坐标点。同一 wv2200 值在 Figure A 上对应 (T, log a) 的连续组合；例如在低 X_Tschermak 区，2195 等值线纵贯约 300 °C 以上的温度范围。此外等值线走向在空间上不均匀，在 Figure A 高温侧 2190 至 2195 等值线几乎与 a1 相界平行，波长微小变化对应巨大温度变化，信息含量局部趋于退化；在低温高 log a 区 2205 至 2215 等值线近垂直排列，约束的主要是 log a 而非 T。因此这把"标尺"的刻度方向与分辨率在图面上逐点变化，且本质上是一维的。
Why it matters: 被评审的正是这句话本身。以当前措辞，任何细心的读者都会发现标量无法给出二维坐标，声明会被直接驳倒，进而损害两张图真实的一维约束价值。
Resolution test: 声明降级为可辩护形式，例如"将光谱标量映射为 T-log(aK+/aH+) 空间中的等值线约束，首次为 CRAMM 逐像元产品提供热力学解释坐标系"；或者明确给出收缩到点所需的第二约束（如共生矿物对、假设的流体演化路径、独立地温计）并在图上示范一次完整的二维定位。同时建议在图上或正文量化等值线走向与相界的夹角分布，说明哪些区域对 T 敏感、哪些区域对 log a 敏感。

**R3-M2**（Major, Blocking: No, statistical-rigor 兼 figures-and-tables）
Claim pointer: Figure B 作为 chl_center 产品的定量标尺。
Evidence pointer: chlorite_rebuild_model.csv 第 2 行（n=6 主拟合，CV-RMSE 2.08 nm，CI_Daph [2235.3, 2266.9]，CI_Ames [2251.1, 2294.6]）；user_tk_pos2250_field.csv 中 X_Daph ≈ 1 的大片区域 in_calib = False；Figure B 中红色高值叶瓣大部分位于 magenta 覆盖多边形之外，colorbar 刻度间隔约 1.75 nm 并显示到 0.5 nm 量级的视觉分辨。
Concern: 三个数量级关系没有对齐。产品端 chl_center 的仲裁容差为 1 nm（chl13 LOO-RMSE 1.0 nm，n=13），桥式模型 CV-RMSE 为 2.08 nm（n=6），而 Daph 与 Ames 端元系数的置信区间宽度达 ±16 至 ±22 nm。图面视觉权重最大的红色叶瓣（Pos2250 接近 2255.5，即 Daph 端元）恰恰落在标定覆盖区之外，其预测值的不确定性接近 colorbar 全量程，但图上没有任何不确定性表达，colorbar 的细分刻度反而暗示了不存在的精度。n=6 的敏感性分析（n=7 与 n=5 时 c_Ames 从 2263.4 漂移到 2266.9，CV-RMSE 恶化到 3.83）进一步说明端元系数不稳。
Why it matters: 标尺的刻度误差大于被测信号的区分度时，图的应用叙事在外推区不成立，而读者视线首先落在外推区。这不否定图的价值，但必须让不确定性可见，否则图在误导。
Resolution test: 至少做到三件事。一，把 in_calib = False 区域降饱和或加阴影。二，叠加由端元 CI 传播得到的 Pos2250 不确定度等值线或置信带，或将 colorbar 刻度间隔改为不小于 CV-RMSE 的物理间隔。三，报告标定覆盖多边形面积占整个着色场的比例，并在场景应用时报告落在多边形内的像元比例。

**R3-M3**（Major, Blocking: No, reproducibility）
Claim pointer: Figure A 的 wv2200 等值线可作为 mus_center 的定量标尺。
Evidence pointer: Figure A 中 2190 至 2215 nm 等值线；评审包内无任何关于 wv2200 与 X_Tschermak（Si p.f.u. = 3+X）之间经验关系的 provenance 文件。证据状态为 not assessable from provided material。
Concern: Figure A 的等值线位置完全取决于一个波长对 Tschermak 替代程度的标定关系，该关系的数据集、样本量、拟合形式与误差均未随包提供。没有这个 provenance，Figure A 作为标尺的刻度无法被独立检验，也无法与 Figure B 的 provenance 透明度对齐。AUTHOR_INPUT_NEEDED。
Why it matters: 两张图被声明为同一类贡献（标尺），但一张有逐点 provenance 另一张没有，审稿人与读者无法对称地核验。
Resolution test: 提供 wv2200 对 Si p.f.u.（或 X_Tschermak）的标定关系、样本清单、RMSE 或等效误差度量，并以与 chlorite_rebuild_model.csv 相同的格式给出；同时说明该标定在 EMIT 波段采样与 MICA 连续统去除口径下的适用性。

**R3-M4**（Major, Blocking: No, experimental-design 遥感产品有效性）
Claim pointer: 这两张图可在场景尺度（EMIT 全场景，1280×1242 像元）上作为逐像元产品的解释框架。
Evidence pointer: 评审包第 4 条上下文事实（无场景级地面真值，无野外 XRD/化学）；图为平衡热力学模型，像元为约 60 m 混合像元。
Concern: 从平衡相图到场景像元的读数链条上有三处未处理的间断。一，像元内的白云母或绿泥石可能是碎屑成因（继承自源区），其吸收中心记录的是别处别时的形成条件，把它读作本地流体环境需要自生成因与就地平衡的假设，该假设在评审包中没有任何支撑。二，混合像元中多种 Al-OH 或 Fe/Mg-OH 相共存时，MICA 仲裁窗口给出的单一中心波长与相图所假设的单相成分之间没有对应关系的论证。三，在没有任何地面真值的前提下，评审包没有提出任何替代性的内部一致性检验方案。
Why it matters: 对 Computers & Geosciences 的软件方法论文，Discussion 中的应用图可以不依赖野外真值，但必须说明在没有真值时应用故事靠什么成立。当前材料没有回答这个问题，而这恰是遥感读者最先质疑的地方。
Resolution test: 在不发明新实验的前提下，以下任一组合可闭合。一，内部一致性检验：对白云母与绿泥石共存的像元，分别读数得到的 T 应落在相容区间，给出全场景相容性统计。二，与已知地质对照：测试场景的已知蚀变分带或矿床地质与读数格局的空间一致性叙述。三，把仲裁容差 ±1 nm 与桥式 CV-RMSE 2.08 nm 换算成图上的等值线厚度，给出像元读数的不确定度分布图。四，明确写出碎屑/自生假设与混合像元限制，把图的用途限定为"成因假说生成"而非"环境参数反演"。

### Minor Comments

**R3-m1**（Minor, figures-and-tables）Figure B 中文标注 + 内部代号 → 英文出版级标注，桥式系数表达式可保留但需图注说明来源。
**R3-m2**（Minor, figures-and-tables）Figure B colorbar 刻度（间隔 ~1.75 nm）暗示的精度与 CV-RMSE 2.08 nm 不匹配；上限 2256 截断桥式 Ames 端元 2263.4 未说明理由 → 调整刻度并说明取值依据。
**R3-m3**（Minor, figures-and-tables）Figure A 灰色水平带（T ≈ 330–360 °C）未标注含义 → 图例或图注定义。
**R3-m4**（Minor, figures-and-tables）Figure A 等值线 2190–2215 nm 与产品窗口 2195–2220 nm 双向错位 → 对齐或图注说明。
**R3-m5**（Minor, data-resource-quality）未报告覆盖区面积比例、未叠加标定样本成分点投影 → 报告比例并叠加样本点。
**R3-m6**（Minor, writing-clarity / readability）magenta 在两图编码不同含义（图 A=等值线，图 B=标定边界）→ 区分色例。

### Technical failings that must be addressed before the case is established

1. 声明降级或补足第二约束（R3-M1）。2. Figure B 的不确定性上图与外推区视觉降级（R3-M2）。3. Figure A 等值线 provenance 补齐（R3-M3）。4. 场景尺度适用性论证（R3-M4）。

### Assessment against Nature-style criteria

Originality: 中等偏上。波长-成分关系本身与 Al-OH 一维向量均为已建立的前作，贡献的新意在于组合方式与在开源软件产品层面的首次落地，而非关系本身。"第一次"的表述必须收窄到组合与实现层面，否则在文献核验完成后大概率被推翻。
Scientific importance: 对领域内部为实质有用的增量，尚不构成广泛重要性。它提升的是一个具体软件产品的解释力，影响半径取决于 CRAMM 的用户群与 EMIT 时代成分填图工作的采纳程度。
Interdisciplinary readership interest: 真实存在且是本文的强项。光谱学、热力学模拟、勘查地质三个群体的交集读者会直接受益，前提是声明校准后框架仍然清晰。
Technical soundness: 尚未建立。桥式模型的 n=6 小样本与宽 CI、Figure A 缺失的标定 provenance、不确定性未传播、场景尺度假设未论证，四点叠加使"标尺"目前只在定性层面成立。
Readability for nonspecialists: Figure A 接近可读，Figure B 因中文标注与内部代号不可直接进入稿件；两图共用的坐标系是好的叙事基础，但需要一段为非热力学读者写的"如何读这张图的等值线"引导，并明确一维约束的性质。

### Recommendation posture

Major revision。概念组合值得发表在 Computers & Geosciences，图件的诚实边界标注（in_calib 机制）应当保留并推广到不确定性表达。在声明降级为一维等值线约束、Figure A provenance 补齐、Figure B 不确定性上图、并补充至少一种无真值条件下的内部一致性检验之后，这组图可以成为软件方法论文中有说服力的解释框架。以当前形式，"第一次将光谱参数转换为二维地质指针"的声明不可保留。
