# CRAMM 学术价值评估与发表建议

> 评估日期：2026-08-23 ｜ 评估基准：Nature 系列评审框架（novelty / rigor / reproducibility / significance 四维）
> 事实基础：本文件所有数字均可溯源到 `docs/paper_preparation.md` §0 事实核对表、`docs/verification_matrix.md`、`docs/benchmark.md`、`docs/MCF_vs_rfjson_verification.md`、`docs/arbitration_stats.md`——写作时直接引用，不再二次核实。
> 与 `paper_preparation.md` 的关系：那份档案是"写什么"的素材库；本文件是"值多少、投哪里、怎么投"的判断层。

---

## 1. 一句话定位

**CRAMM 是 USGS MICA 决策规则体系的首个开源实现，并把规则体系从"矿物探测"推进到"矿物成分填图"——其投稿定位是软件-方法论文（software–method paper），不是应用论文，也不是理论论文。**

这一定位决定了：评审的核心问题是"实现是否可信、扩展是否真实、工程是否严谨"，而不是"某矿区填图结果是否惊人"。所有材料组织都应服务于这三个问题。

---

## 2. 学术价值拆解（四维）

### 2.1 Novelty（新颖性）——三层，由硬到软

| 层 | 内容 | 硬度 | 审稿人可质疑点 |
|---|---|---|---|
| **实现层** | MICA 自 kokaly2011 起仅以 IDL 闭源随 ENVI/PRISM 分发，15 年无开源实现。CRAMM 是首个，且与官方 .mcf（2014 v6a）**逐字段核验零差异**（77 规则、142 特征、1,136 连续统槽、80 处 NOT 引用、77×4 材料约束、64 条参考身份、77 色表） | ★★★★ 事实性新颖，无法反驳（核验脚本 `docs/verify_mcf_rfjson.py` 可重复执行） | "移植算不算贡献？"——用 §2.2 的可复现性论证回应 |
| **方法层** | **窗口拓扑设计原则**：白云母无缝拼接窗（亚型轴离散先验）/ 绿泥石故意重叠 1 nm 窗（连续成分先验，容差=chl13 标定 LOO-RMSE 1.0 nm）/ 碳酸盐重复窗（不可分辨先验→声明式零翻转）。三族全场景翻转 46,823 / 15,305 / 0（总计 62,128），六向族间交叉翻转 = 0 | ★★★ 全文最有普适性的方法论贡献：窗口拓扑应对应亚型轴先验 | "为什么不直接用混合像元分解？"——答：可解释性 + 专家知识编码，规则体系与 ML 并存的正当事由 |
| **产品层** | 从离散标签到连续成分场：mus/chl/cal 三条吸收中心产品线；chl13 闭式标定 pos2250 = 2218.8·xAl + 2279.6·xFe + 2249.7·xMg（in-sample RMSE 0.73 nm）；白云母 wv2200–Tschermak 相图锚定 | ★★ 渐进式创新，但是 EMIT 时代的实用增量 | "精度验证在哪？"——这是最弱一环，见 §4 风险 R1 |

**判断**：新颖性足以支撑 C&G 软件论文，不足以支撑方法学期刊（如 RSE/ISPRS J）的算法论文——那里会要求场景级地面真值验证，目前不存在。

### 2.2 Rigor（严谨性）——本项目最强的维度

验证矩阵 13 项套件全部存档可复跑（`docs/verification_matrix.md`），其中对审稿人最有说服力的四条：

1. **忠实性核验零差异** + 三类设计性偏离（线性合成混合物、传感器无关寻址、新增字段）逐条主动声明——"faithful port"主张有一手证据而非自述；
2. **逐比特工程纪律**：串行≡并行逐比特（spawn + BLAS 单线程锁定），golden 五键回归 + 平台相关基线的治理工具（rebaseline 带像素级审计门禁）；
3. **仲裁独立性实证**：窗口间距 25/52 nm 双重隔离，全场景六向交叉翻转 = 0（不是论证，是测量）；
4. **诚实性纪律**（Nature 标准最看重、多数软件论文缺位）：Beckman 参考谱与文献锚点 1–2 nm 系统性红移在图件与 figures/README 中**显式标注**而非掩盖；in-sample 0.73 nm 与 LOO 1.0 nm 两个 RMSE 口径分写；场景位置图明确标注"无底图、边界线非凭记忆添加"。

**判断**：这是把论文从"又一个工具发布"提升到"可信基础设施"的关键资产，Cover letter 应直接引用验证矩阵。

### 2.3 Reproducibility（可复现性）——名义满分，闭环未完成

- ✅ 纯 Python、跨平台（Win/Linux/macOS）、Python 3.9–3.13、依赖极小（顶层仅 numpy）；
- ✅ MIT、dist/ 有 1.0.0 wheel+sdist、README 徽章指向 PyPI；
- ✅ 传感器无关契约（七元组 `(spectrum, wl, w, bp, chanels)` + 运行时重采样）——EMIT 读取器仅 106 行，是唯一传感器专属代码；
- ✅ 自定义规则库机制（rf_path / invalidate_caches() 契约，7 场景测试）——社区扩展的技术通道已就绪；
- ⚠️ **闭环缺口**：本地仓库无 remote、GitHub 未推送、Zenodo DOI 未取、PyPI 实测未做。这些是投稿**门槛**（C&G 强制 code availability），不是加分项。见 §5 第 0 步。

### 2.4 Significance（意义）——时机是真实资产

- EMIT（2022–）全球开放 L2A 产品把星载矿物填图推向业务化，而 MICA 规则体系绑定 ENVI/IDL 许可与预卷积库——**社区需求与工具缺口同时存在**，这是 Introduction 的立足点；
- DS787（Kokaly et al. 2013，阿富汗全国 218 航带 HyMap 填图）证明该规则体系可业务化——CRAMM 让它第一次可以被任何人复现、审计、扩展；
- 性能口径（权威基准，同机同环境 2026-08-23）：整景 1,589,760 px，serial 131.73 s → nw=4 61.88 s（25,689 px/s）；暖调用单光谱 9.8 ms。"比 IDL 快约 10×"目前**无仓库内对照证据**（风险 R2）。

---

## 3. 期刊定位矩阵

| 期刊 | 匹配度 | 判断 |
|---|---|---|
| **Computers & Geosciences** | ★★★★★ | **主选**。开源软件+算法论文的标准归宿；验证矩阵、自定义规则机制、逐比特工程正对 reviewer 口味；paper_preparation.md 已按 C&G 格式（Highlights、Graphical Abstract、code availability 表）准备 |
| **JOSS** | ★★★★ | **后续追加**。JOSS 明确欢迎已在其他期刊描述过的软件（"software already published elsewhere is welcome"），C&G 接收后投 JOSS 是合规的双通道，篇幅 1–2 页、周期数周，扩大软件可见度。**顺序不能反**（JOSS 先走会稀释 C&G 新颖性主张） |
| SoftwareX | ★★★ | 备选。软件元数据论文，门槛低于 C&G，但方法与科学增量着墨少，浪费了方法层创新 |
| IEEE JSTARS / TGRS | ★★ | 不推。会要求传感器横向对比或定量精度验证，正中 R1 软肋 |
| Remote Sensing of Environment / ISPRS J | ★ | 不投。应用期刊，需要场景级地面真值与地质解读——目前无场景验证数据 |
| Nature 系（Sci Data / Comms Earth Environ） | ☆ | 不现实。无新数据集（Sci Data）、无领域级新发现（Comms）——诚实结论：本文是"可信工具+方法增量"，不是"发现型"工作 |

**结论：C&G 单主选，JOSS 追加，不做多线海投。**

---

## 4. 风险登记册（按审稿杀伤力排序）

| # | 风险 | 现状 | 处置 |
|---|---|---|---|
| **R1** | 产品层（mus/chl/cal 中心→成分）缺独立精度验证 | 只有 chl13 标定集自洽（LOO 1.0 nm）与相图理论锚定，无场景级真值 | 措辞降级：写成 "composition proxy"（现状）而非 "quantitative composition"；Discussion 局限节如实列适用边界（绿泥石 ≳50% 占比前提等）。**不补实验也能投**，补了（如 DS787 Panjsher AOI 定性对照）则升档 |
| **R2** | "10× faster than IDL" 无一手证据 | ~~仅记忆事实~~ **2026-08-23 关闭**：用户提供同景 PRISM 计时 ~25 min → serial 11× / nw=4 24×，两种执行模式均超一个数量级，摘要级主张恢复为 "more than an order of magnitude"；协议细节（同机确认、PRISM/ENVI 版本、计时范围）已在 docs/benchmark.md 立账待补 | 措辞已恢复有界形式；投稿前补齐 protocol 记录（benchmark.md 状态节清单） |
| **R3** | 像元口径矛盾 | 1,831,922（疑正射网格活像元）> 1,589,760（场景总像元） | 全文统一 1,589,760；核实正射口径后只在需要处使用并注明 |
| **R4** | 场景地质背景未确认 | 足迹已从 L2A 地理定位数组精确获得（99.65°E 41.03°N，戈壁、中蒙边境），但地质背景段落未写、Earthdata 元数据未核对 | 网络恢复后查 Earthdata granule 元数据；地质背景只写有文献支撑的内容，**严禁杜撰** |
| **R5** | 深度比约束（0.6/0.4）阈值经验设定 | 无灵敏度实验 | Discussion 局限节声明即可；灵敏度实验列为可选增补 |
| **R6** | 发布闭环未完成 | ~~无 remote / 未推 GitHub / 无 Zenodo DOI / PyPI 未实测~~ **2026-08-23 更新：Zenodo DOI 已取得（10.5281/zenodo.22024483，README 徽章已加）→ GitHub 推送与 release 归档已完成；仅剩 PyPI `pip install cramm` 三平台实测** | §5 第 0 步，纯流程性工作，卡投稿门槛 |

---

## 5. 发表路径（顺序即策略）

**第 0 步 — 发布闭环（投稿门槛，半天工作量，待网络）**
~~配置 remote → 推送 GitHub（leecugb/cramm）→ 打 1.0.0 tag~~ → 实测 `pip install cramm` → ~~Zenodo 关联 release 取 DOI → README/CITATION.cff 加 DOI~~。**2026-08-23 状态：GitHub 已推送、Zenodo DOI 已取得（10.5281/zenodo.22024483）、README 徽章已加；CITATION.cff 待作者署名信息到位后创建；仅剩 PyPI 实测。** EMIT 影像永不入库（已 gitignore）。

**第 1 步 — 关闭 R2/R3/R4（写作前置）**
R2 定摘要措辞，R3 统一数字口径，R4 撑起 Results 场景节。三者都是"关缺口"而非"做新工作"。

**第 2 步 — 成稿（素材已齐）**
paper_preparation.md 已备好：标题候选（推荐 #2 进取型）、Abstract 草稿（~210 词）、Introduction 论点链、Methods/Results/Discussion 素材清单。图件 6/8 已完成（算法流程图、产品五联图、白云母仲裁、绿泥石窗口、碳酸盐锚点、性能曲线、场景位置——其中 7 张可直接用）；验证矩阵总表已存档（`docs/verification_matrix.md` 英文化即成 Table）。文献库是唯一未成建制的素材（Tetracorder/splib06b/EMIT ATBD/标定集出处等正式条目）。

**第 3 步 — 投稿 C&G**
Cover letter 四个卖点：首个开源 MICA 实现（复现性）/ 传感器无关规则引擎（EMIT 时代需求）/ 窗口拓扑设计原则（方法增量）/ 逐比特工程纪律 + 13 项验证矩阵（严谨性）。建议审稿人方向：成像光谱规则方法 × 矿物填图应用 × 地学软件工程。

**第 4 步 — C&G 接收后投 JOSS**
短平快，双通道扩大影响力；引用计数归 C&G 主文，JOSS 收割软件使用入口。

**第 5 步 — （已定方向）论文二：OGR / Chemical Geology 应用论文**
2026-08-23 定稿：两张 GEMS 相图定位为 CRAMM 产品的**解释框架**（README 措辞已降级为 isopleth 约束表述，见 `docs/figure_eval_gems_phase_diagrams.md` §8.7）。相图的"定量标尺"主张留待论文二——二龙包/焦家实测 wv2200 投点验证 + 场景 T–log a 格局解读 + 焦家 OGR 2025 null result 的可检验预测。评审关切 C6（端到端验证）由此从论文一的强烈建议转为论文二的核心贡献。

---

## 6. 诚实的自我定位（写给作者自己的话）

- 这篇文章的**硬通货是严谨性与复现性**，不是科学发现。四维评分：rigor ★★★★★ / reproducibility ★★★★☆（闭环后满分）/ novelty ★★★☆ / significance ★★★（时机加成）。
- C&G 的影响因子不高，但它是这篇工作的**正确读者群**：需要可审计规则引擎的成像光谱社区。
- 最大的软肋（R1 精度验证）决定措辞边界：凡 "quantitative composition" 一律写作 "composition proxy"，凡 "10×" 必须有对照记录或降级。守住这两处，审稿最坏结果是小修；守不住，可能被拒在可信性上。
