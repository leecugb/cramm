# CRAMM 论文写作准备档案

> 目标期刊：**Computers & Geosciences**（开源软件 + 算法论文）
> 建档日期：2026-08-23 ｜ 建档方式：对 D:\CRAMM 全仓库素材逐一核实（README、docs/、cramm/classifier.py、cramm/data/rf.json、tests/、benchmark 日志、git 历史）
> 用户提供的"项目事实"已逐条核对：**除一处数字口径存疑外全部属实**（见 §8 缺口清单）。

---

## 0. 事实核对表（写作时可直接引用，均已在仓库中找到一手出处）

| 事实 | 出处 | 状态 |
|---|---|---|
| rf.json = 77 规则 + 19 mixtures + 53 wavelength_map | `cramm/data/rf.json` 实测（顶层 keys: rf/mixtures/wavelength_map） | ✅ |
| 与官方 .mcf（2014 v6a）逐字段核验零不一致 | `docs/MCF_vs_rfjson_verification.md`：77 条目集合、142 诊断特征、1,136 连续统约束槽、80 处 NOT 引用、77×4 材料级约束、64 条纯谱参考身份、77 类别颜色 RGB 逐值一致 | ✅ |
| 9 条深度比规则（0.6×6 + 0.4×3） | rf.json 实测，名单与 README 一致 | ✅ |
| 11 条仲裁窗口规则（白云母 4 无缝拼接 / 绿泥石 3 重叠 1nm / 碳酸盐 4 重复窗） | rf.json 实测，窗口数值与 README/algorithm_flow.md 完全一致 | ✅ |
| 7 条结构式元数据规则（白云母族 4 + 绿泥石族 3；tier A/B） | rf.json 实测：medhighAl/Fe-rich/illite_gds4 = A，illite_imt1 + 绿泥石×3 = B | ✅ |
| 仲裁器数学语义（单窗翻转重拟合 / 多窗歧义保持 / 无效保守 / 向量化单趟） | `classifier.py::_reassign_by_absorption_center`（302–407 行）docstring 与实现 | ✅ |
| 窗口间距 mus–chl 25 nm、chl–cal 52 nm，族间自隔离 | 同上 docstring + `tests/check_arbitration_independence.py` | ✅ |
| 整景 1280×1242，nw=4 分析 ~62 s | `D:/test/full_scene_timing.json`：serial 156.4 s / nw=4 61.6 s（speedup 2.54），加载 4.09 s；24 逻辑核，Python 3.13.9 | ✅ |
| 暖调用单光谱 ~10 ms、缓存 16× | `output/benchmark_full.log`：cold 158.6 ms → warm 9.6 ms，16.5× | ✅ |
| 参考重采样 cold 138.1 ms / warm 0.0 ms | 同上 | ✅ |
| 测试矩阵（21 + 7 + 6 + 16 + 7 + 编译路径逐比特 + golden 串并行） | `tests/` 目录与 README Testing 节 | ✅ |
| git 里程碑 77164b4(chl_center) → 1793ac5（绿泥石宽容仲裁） → c683947(cal_center) | `git log` 实测 | ✅ |
| dist/ 已有 cramm-1.0.0 wheel + sdist | `dist/` 目录 | ✅ |
| **本地仓库未配置 git remote（`git rev-list origin/main` 失败）** | `git status` 实测 | ⚠️ 与"领先 origin ~15 提交"的表述需对齐：当前 D:\CRAMM 无 remote，推送 GitHub 是投稿前必办项 |
| ⚠️ "1,831,922 非黑像元"与场景总像元数矛盾 | timing JSON：1280×1242 = **1,589,760** 总像元；1,831,922 > 总数，可能为正射输出网格的活像元数，**投稿前必须核实口径** | ⚠️ |

---

## 1. 拟定标题候选（3 个）

1. **CRAMM: an open-source Python implementation of the USGS MICA decision-rule system for sensor-agnostic hyperspectral mineral mapping**
   CRAMM：USGS MICA 决策规则体系的首个开源 Python 实现——面向传感器无关的高光谱矿物填图
   *（稳妥型：软件论文标准句式，"first open-source"进摘要而非标题更稳）*
2. **From mineral detection to mineral composition: CRAMM, an open Python toolkit extending USGS MICA with wavelength-arbitrated subtyping and absorption-center mapping**
   从矿物探测到矿物成分：CRAMM——以波长仲裁亚型归属与吸收中心填图扩展 USGS MICA 的开源工具包
   *（进取型：把三条产品线创新顶进标题，C&G 读者一眼看到增量）*
3. **CRAMM: reproducible and extensible decision-rule mineral identification for EMIT and beyond**
   CRAMM：面向 EMIT 及未来传感器的可复现、可扩展决策规则矿物识别
   *（简短型：强调 reproducible/extensible 两个 C&G 关键词）*

推荐 **2** 作主选、**1** 作保守备选（若审稿人倾向"实现类"定位）。

---

## 2. Abstract 草稿（英文，~200 词）

> The USGS Material Identification and Characterization Algorithm (MICA) is a widely used expert system for mapping minerals from imaging spectroscopy, but it is distributed only as closed-source IDL code tied to the ENVI environment and to sensor-specific pre-convolved reference libraries, which limits reproduction, extension, and uptake by new spaceborne missions such as EMIT. Here we present CRAMM, the first open-source, pure-Python implementation of MICA. Its rule library—77 decision rules with 142 diagnostic features—was verified field-by-field against the official 2014 v6a MICA command file with zero discrepancies, while reference spectra are resampled to arbitrary band configurations at runtime, making the classification core sensor-agnostic. CRAMM extends MICA in three ways: an optional secondary-feature depth-ratio constraint that suppresses white-mica false positives; wavelength-arbitrated attribution of muscovite, chlorite, and carbonate subtypes against calibrated absorption-center windows, including deliberately overlapping tolerance windows and declarative zero-flip schemes; and per-pixel absorption-center maps that turn subtype labels into continuous composition proxies anchored to measured mineral chemistry. A full EMIT granule (1280 × 1242 pixels) is classified in about one minute with four workers—an order of magnitude faster than the IDL implementation—with bit-exact serial–parallel reproducibility guarded by a golden regression suite. CRAMM is cross-platform, self-contained, and available on PyPI, lowering the barrier from mineral detection to quantitative mineral composition mapping.

（约 210 词；结构：背景→缺口→方法→结果→意义；数字均可溯源；"order of magnitude faster"对应 10× 记忆事实，投稿前需 §8-2 的对照证据支撑）

---

## 3. Introduction 论点链（bullet）

- **领域尺度**：成像光谱矿物填图是蚀变制图、矿产勘查、地热与碳循环研究的基础手段；基于光谱特征的规则体系（Tetracorder → MICA）因其可解释性与专家知识编码能力，与统计/机器学习方法并存至今。
- **旗舰先例**：DS787（Kokaly et al., 2013）阿富汗全国 HyMap 填图（218 航带、>438,000 km²、双 .mcf 分 1 µm/2 µm 两遍）证明规则体系可业务化；`docs/DS787_summary.md` 已提炼其算法公式化（连续统去除、fit=r²、深度缩放、约束层级），可直接改写为 Introduction 第 2–3 段。
- **痛点（gap）**：MICA 仅以 IDL 闭源形式随 PRISM/ENVI 分发（kokaly2011 原文自述）；参考库必须**预卷积到具体传感器**（HyMap 126ch 专用副本），换传感器 = 重建整套库 + 依赖 ENVI/IDL 许可 → 不可复现、不可扩展、无法接入新传感器。
- **机遇**：EMIT（2022–，全球开放 L2A 反射率产品）把星载矿物填图推向业务化，社区急需开放、可审计、传感器无关的规则引擎。
- **本文工作（一段收束）**：CRAMM = 忠实移植（与官方 .mcf 逐字段零差异核验）+ 三个层次的创新——
  1. *工程层*：纯 Python、跨平台、零配置、运行时重采样、逐比特可复现；
  2. *规则层*：深度比约束（9 规则）抑制白云母假阳性；
  3. *产品层*：从"分类标签"到"成分连续场"——mus/chl/cal 三条吸收中心产品线 + 波长仲裁亚型归属（无缝拼接 / 宽容重叠 / 声明式零翻转三种窗口哲学的族别化设计）。
- ** lineage 亮点**（DS787_summary §5 已备好）：白云母四亚型原是"多参考光谱投票"→ CRAMM 升级为 2.2 µm 吸收中心连续定量 + 仲裁，是全文最硬的一条创新脉络。

---

## 4. Methods 素材清单

### 4.1 算法管线（配图：docs/cramm_algorithm_flowchart_nature，已有 Nature 风格 183 mm 双栏图，svg/pdf/tiff/png 四格式）
- 五层流水线（docs/algorithm_flow.md 已写成表）：输入层（七元组契约 `(spectrum, wl, w, bp, chanels)`）→ 预处理层（坏波段剔除、高斯核重采样缓存、规则编译两级缓存）→ 决策规则核心层（连续统去除 → 2×2 闭式最小二乘 → fit(r²)/depth → NOT 特征排除 → 五层约束 + 深度比约束）→ 综合判读层（argmax(fit×depth) + 三族中心二次拟合 + 统一仲裁器）→ 输出层（5 幅 uint8 RGB + 4 浮点数组 → GeoTIFF/npz）。
- 数学语义一手出处：DS787 方程 1–2（R_C = R_O/R_L；D = 1 − R_C；深度不直接计算而经缩放取值）；`_fit_r2_depth` 对应深度因子设计；`_get_quadratic_center` 三点抛物线顶点 + 共线三元组 NaN 折叠。

### 4.2 规则库与核验（Methods 必有一小节 + 一张核验表）
- rf.json 结构：77 规则（diagnostic/not_absolute/not_relative features、weighted_constraints）+ 19 mixtures（端元线性合成）+ 53 wavelength_map（4 种仪器网格）。
- 核验表素材（docs/MCF_vs_rfjson_verification.md）：A 条目集合 77=77；B 142 特征 + 1,136 连续统槽；C 80 处 NOT 引用；D 77×4 材料级约束；E 64 条参考身份（6 条人工复核）；G 颜色表 77=77。
- **设计性差异须如实声明**：13 条混合物由实物混合谱改为端元线性合成；其中 kaolinite.5+muscoviteMedAl.5 与 alunite.5+kaolinite.5 的端元由 KGa-1 换成 KGa-2（双峰锐度不同）——核验文档明确标注"论文中应注明"。
- 未移植的 .mcf 头部参数（传感器绑定项由运行时契约替代）——正好是"传感器无关"论证的一部分。

### 4.3 仲裁器数学语义（Methods 核心小节）
- 统一仲裁器 `_reassign_by_absorption_center`：成员门控（`mus_c > 0` 且属族）→ 窗口命中计数 → 恰好单窗且目标规则接受（fit 非 NaN 且 >0）→ 翻转并以目标规则端点重拟合中心一次（失败回退旧中心）；多窗=歧义保持；无效/出窗=保守保持；全向量化单趟、串并行共用同一实现 → 逐比特。
- 三种窗口哲学（论文卖点，建议单列一小节或表）：
  - 白云母：**无缝拼接** [2.195,2.200)/[2.200,2.206)/[2.206,2.210)/[2.210,2.220)，锚定各参考谱实测 wv2200；13 族成员中 9 个无窗（伊利石/混合物）不仲裁；
  - 绿泥石：**故意重叠 1 nm**（容差 = chl13 标定 LOO-RMSE 1.0 nm，即重复测量噪声地板）；闭式模型 pos2250 = 2218.8·xAl + 2279.6·xFe + 2249.7·xMg；价态约定经闭集归一精确抵消；
  - 碳酸盐：**重复窗**（calcite 对 [2.334,2.350)、dolomite 对 [2.308,2.328)）→ 构造性零翻转，单测钉死；价值在连续图层 + 七锚点序列（菱镁矿 2311.3 < 文石 2315.2 < 铁白云石 2319.2 < 白云石 2321.2 < 菱铁矿 ~2327 < 方解石 2339.4 < 菱锰矿 ~2369 nm）。
  - 族间独立性：窗口间距 25/52 nm + 成员门控双重隔离；`check_arbitration_independence.py` 全场景六向交叉翻转实证为 0。

### 4.4 化学锚定元数据
- 7 条规则 reference.structural_formula（tier A = 湿法双价态 / B = 全铁约定）；白云母 O=11 无水基（14 样本标定集）、绿泥石 O₁₀(OH)₈ 基（chl13 标定集，CCa-1 化学采用 Bartel XRF）；纯元数据不进分类计算（README 明确，防审稿人误读）。

### 4.5 实现与逐比特工程
- 三层架构：emit_reader（唯一传感器专属，106 行）/ classifier（1613 行，顶层仅 numpy，pandas 惰性导入降低 spawn 开销）/ renderer（528 行）+ mica_engine facade（335 行）。
- 多进程 spawn + BLAS 单线程锁定 → 串行≡并行逐比特；预编译规则常数（法方程 B、深度因子）两级缓存；暖调用 9.6 ms（16.5×）。
- 自定义规则库能力（README "Custom rule libraries"）：构造时传 rf_path 或就地改 + invalidate_caches() 契约；`test_custom_rules.py` 7 场景覆盖——**这是 C&G "可扩展性"评审点的直接证据，Introduction/Methods 都要点到**。
- 单光谱 PDF 诊断（renderer，docs/single_spectrum_diagnostic.png 已有图）：逐规则特征解剖 + 约束审计，可作"可解释性"卖点图。

---

## 5. Results 素材清单（标注：✅已有数据 / 🔬需补实验 / 🖼需补图）

### 5.1 软件与性能
- ✅ 整景：1280×1242×285，加载 4.09 s；serial 156.4 s / nw=4 61.6 s（speedup 2.54；98.4 → 38.7 ms/kpixel）；benchmark_full.log 另有 150 行子块 nw=1/2/4 = 14.46/10.98/8.48 s 与整景 131.15/90.49/64.91 s 两组扫描（**两组数字来自不同日期/机器状态，投稿前统一复跑一次**）。
- ✅ 单光谱：cold 158.6 ms / warm 9.6 ms / 16.5×；重采样 cold 138.1 ms / warm 0.0 ms。
- ✅ 5 张 GeoTIFF + raw npz + Top-N API 产品线完整（README 输出表可直接改成论文 Table）。
- 🔬 "比 IDL 快约 10×"：目前只有记忆事实，无仓库内对照记录 → 需补一次可复现的 IDL-vs-CRAMM 同场景计时（或改写为保守表述）。
- 🖼 性能随 workers 扩展曲线图。

### 5.2 三族仲裁定量效果
- ✅ 碳酸盐：全场景 78,672 胜者（find_cal_tile.py 输出口径，脚本在、结果未存档 → 重跑存档即 ✅）；cal_center 连续层 + 七锚点解读框架成文。
- ✅ 绿泥石：全场景 50 px 换色 + 17,588 px 同色重拟合（用户事实；exp_chlorite_arbitration.py 可行性实测脚本在，含 2250/2350 双带交叉表与双带门控统计 → 重跑并存档输出）。
- 🔬 白云母：四亚型仲裁的**全场景翻转统计目前仓库无存档**——必须补（每亚型翻转数、翻转前后 mus_center 分布、与 DS787 Panjsher AOI 式定性对照）。
- ✅ 独立性：check_arbitration_independence.py 六向交叉翻转全场景为 0（脚本在，重跑出表）。
- 🖼 仲裁前后对比图（白云母亚型图 before/after + 中心直方图叠窗口线）；绿泥石宽容窗口示意（重叠区=歧义保持）；碳酸盐七锚点参考谱图 + cal_center 直方图（5 nm 分箱）。

### 5.3 整景产品
- ✅ 输出 GeoTIFF 在 output/ 可生成；测试场景 EMIT_L2A_RFL_001_20220819T061448_2223104_025（NASA/JPL 公开产品，数据可用性声明好写）。
- 🔬 场景地理位置与地质背景未确认（**严禁杜撰**）→ 用 granule ID 查 Earthdata 元数据定足迹，补一段地质背景 + 已知矿化对照。
- 🖼 产品五联图（矿物图/增强图/mus/chl/cal 中心图）+ 区域位置图；碳酸盐 ~39% 覆盖（含混合）可写成一句结果。
- 🖼 单光谱诊断 PDF 一页示例（已有 png，直接可用）。

### 5.4 验证矩阵（建议做成一张 Table）
- ✅ test_core 21 项契约（含窗口仲裁合成单测、chl/cal 集成契约）｜test_custom_rules 7｜test_parallel_isolation 6｜check_rows_logic 16｜test_single_spectrum 7｜check_compiled_path（302 px × 77 规则逐比特）｜golden 5-key 串并行回归（平台相关基线 + rebaseline_golden.py 像素级审计门禁）｜check_arbitration_independence 全场景三族独立性。
- ✅ .mcf↔rf.json 核验表（§4.2），verify_mcf_rfjson.py 可重复执行。

---

## 6. Discussion 要点

- **与 USGS MICA 的关系**：逐字段核验零差异 = "faithful port"主张的证据基础；6 条参考记录标题差异经人工复核为同一样品（核验文档 §2 表可直接引用）；三类设计性偏离（线性合成混合物、传感器无关寻址、CRAMM 新增字段）逐条声明——这是回应"实现是否可信"审稿意见的核心段落。
- **宽容仲裁哲学**：绿泥石重叠窗把"参考谱是成分连续体上的点"这一事实编码进规则——中间成分不被强行归类；碳酸盐重复窗把同一机制推到极限（声明式零翻转）。可提炼为一般性设计原则：**窗口拓扑（拼接/重叠/重复）应对应于亚型轴的离散/连续/不可分三种先验**——这是论文最有普适性的方法论贡献，建议单设一段。
- **碳酸盐发现性价值**：规则库只覆盖七锚点中的 3 个，文石/菱镁矿静默落入 dolomite 但可在 cal_center 连续层辨识——"连续中心层超越离散规则库分辨力"是强卖点，可配场景实例（需 5.3 的场景解读支撑）。
- **局限（如实写）**：
  - calcite_abundant 全场景仅 5 px（该规则近乎哑规则）；
  - mus_center 化学反演的理论残余通道与适用边界（chl13 自承：绿泥石 ≳50% 像元占比、相似制样；2350 nm 带仅作纯矿物检查）；
  - golden 基线平台相关（BLAS ulp 差异），跨平台需 rebaseline——已在 README/工具链中治理，但要写进论文；
  - 深度比约束阈值（0.6/0.4）目前为经验设定，缺系统灵敏度实验（🔬 可选补）；
  - 1-µm .mcf（铁矿物 VNIR 组）未移植——DS787 双 command file 模式只实现了一半，写为未来工作。
- **未来方向**：接入更多传感器实例（七元组契约已备）、1-µm 规则组、混合像元分解耦合、社区规则库生态（custom rules 机制已就绪）。

---

## 7. 图表清单

### 已有（直接用或轻微整饰）
| 图/表 | 路径 | 用途 |
|---|---|---|
| 算法流程图（Nature 风格，183 mm 双栏，svg/pdf/tiff/png） | `docs/cramm_algorithm_flowchart_nature.*` | Fig. 1 管线总览 |
| 白云母 wv2200–Tschermak 相图（GEMS/MINES23.1） | `docs/muscovite_wv2200_phase_diagram.png` | Discussion/Application 图 |
| 单光谱诊断 PDF 示例 | `docs/single_spectrum_diagnostic.png` | 可解释性/软件功能图 |
| .mcf↔rf.json 核验表 | `docs/MCF_vs_rfjson_verification.md` 表 | Methods 表（英文化即可） |
| .mcf 结构梳理（四段式、别名面板、77 条目统计） | `docs/MCF_v6a_summary.md` | Methods/附录素材 |
| DS787/kokaly2011 提炼 | `docs/DS787_summary.md`、`docs/kokaly2011.md` + 两篇 PDF 原文存档 | Introduction/Related work 引用底料 |

### 需做
1. 场景位置图 + 地质背景（先查 granule 足迹）。
2. 产品五联图（矿物图/增强图/三个中心图，同一区域配色统一）。
3. 白云母仲裁 before/after 亚型图 + 中心直方图叠四窗口分界线。
4. 绿泥石三参考谱 + chl13 标定散点（pos2250 vs 模型）+ 宽容窗口示意。
5. 碳酸盐七锚点参考谱序列图 + cal_center 直方图（5 nm 分箱）+ 文石/菱镁矿疑似像元实例。
6. 性能扩展曲线（workers vs 吞吐，两组 benchmark 统一复跑后出图）。
7. 验证矩阵总表（测试套件 × 覆盖点 × 结果）。
8. （可选）深度比约束抑假阳性实例图：同一像元在有无约束下的归属变化。

---

## 8. 素材缺口与矛盾点（投稿前必须关闭）

1. **数字口径矛盾**：用户事实"1,831,922 非黑像元" > 场景总像元 1,589,760（1280×1242）——前者疑为正射输出网格活像元数，必须核实并在论文中使用同一口径。
2. **10× 加速无一手证据**：仓库内无 IDL 对照计时记录；要么补一次同机同景 IDL-vs-CRAMM 计时并记录环境，要么把摘要措辞降为保守表述。
3. **白云母仲裁全场景翻转统计缺失**（绿泥石 50 px/17,588 px、碳酸盐 78,672 也只有脚本没有存档输出）——三个 exp/check 脚本重跑并存档即可关闭。
4. **场景地理位置/地质背景未确认**：granule ID 可查 Earthdata；位置与已知矿化信息是 Results 场景节的骨架，缺失会卡住 5.3 全部图件。
5. **深度比约束的定量效果**：9 条规则启用前后假阳性抑制率无场景级统计（目前只有机制描述）。
6. **文献库未建**：目前只有 DS787 与 kokaly2011 两篇归档；C&G 论文需补 Tetracorder（Clark et al. 2003）、splib06b（Clark et al. 2007 DS231）、EMIT（Green et al. 及 L2A ATBD）、chl13/白云母标定集出处、GEMS/MINES23.1 等正式引用条目。
7. **git remote 未配置**：D:\CRAMM 本地仓库无 origin（README 徽章指向 github.com/leecugb/cramm）——推送与发布闭环待办（见 §9）。

---

## 9. 投稿前 Checklist

- [ ] 配置 remote 并推送 GitHub（leecugb/cramm）；确认 1.0.0 tag 与 dist/ 产物一致
- [ ] 确认 PyPI `cramm` 1.0.0 已发布且三平台可装（README 徽章显示已有，实测一遍 pip install）
- [ ] Zenodo 关联 GitHub release 取 DOI；README/CITATION.cff 加 DOI
- [ ] 数据可用性声明：EMIT L2A granule（NASA LP DAAC/Earthdata 公开）+ 场景 ID；代码可用性声明：GitHub + PyPI + Zenodo DOI + MIT
- [ ] 关闭 §8 全部缺口（尤其 1/2/3/4）
- [ ] 统一性能数字：同机同环境复跑 benchmark.py --full + timing_full_scene.py，论文只用一组
- [ ] C&G 格式：Highlights（3–5 条）、Graphical Abstract（产品五联图可复用）、软件元数据表（code availability section 必填项：语言/许可/仓库/DOI）
- [ ] Cover letter 要点：首个开源 MICA 实现（复现性价值）+ 传感器无关规则引擎（EMIT 时代社区需求）+ 从分类到成分的产品线创新 + 逐比特工程纪律与完整验证矩阵；建议 2–3 名审稿人方向（成像光谱规则方法 / 矿物填图应用 / 地学软件工程）
- [ ] 自查：摘要与正文所有数字可溯源到本档案 §0 表；未确认信息（场景地点等）一律不进稿

---

## 10. 下一步最该补的 3 件事（优先级）

1. **补齐场景级定量结果与产品图**（堵住 Results 最大空洞）：查 granule 足迹定地理位置；重跑 exp_chlorite_arbitration.py / find_cal_tile.py / check_arbitration_independence.py 并存档输出；补跑白云母仲裁翻转统计；渲染产品五联图与仲裁前后对比图。→ 直接决定 5.2/5.3 两节能否成稿。
2. **固化"10× 加速"证据或降级措辞**：同机 IDL-vs-CRAMM 对照计时（环境、版本、输入记录齐全），写进 Methods/Benchmark 小节；若不可行，摘要与正文统一改为保守表述。→ 这是摘要级 claim，审稿必查。
3. **完成发布闭环 + 数字口径核实**：配置 remote 推送 GitHub、确认 PyPI、Zenodo DOI；同时核实 1,831,922 像元口径矛盾并统一全文数字。→ 低成本但卡投稿门槛（C&G 强制代码/数据可用性）。
