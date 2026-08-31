# Stage 5 of splib07 migration: generate docs/MCF_vs_rf07_diff.md from the
# selection table (difference declaration of the v07 track vs .mcf heritage).
import json

SEL = json.load(open(r"d:\CRAMM\docs\splib07_selection.json", encoding="utf-8"))
refs = SEL["references"]

L = []
L.append("# .mcf 与 rf_splib07.json 差异声明")
L.append("")
L.append("> 日期：2026-08-31（dry_veg_nongrass 映射更正；illite_gds4 覆盖裁决：BECKb→ASDNGb；"
         "AMX 变体审计：AMX8→BECKb、AMX12→NIC4a、AMX17→NIC4b；"
         "jarosite_K 覆盖裁决：NIC4aa→NIC4a）｜ 数据：`docs/splib07_selection.json`（逐条 r 值）、"
         "`docs/splib07_export_audit.md`（烘焙审计）、`docs/splib07_dualrun_diff.md`（场景双跑）")
L.append("")
L.append("## 结论")
L.append("")
L.append("rf_splib07.json 的 **77 条规则同 rf.json 逐比特一致**（诊断特征参数、约束、权重原样继承 "
         ".mcf v6a 启用态，核验见 `docs/MCF_vs_rfjson_verification.md`）；"
         "差异有两类，均已逐条裁决并记录：")
L.append("")
L.append("1. **参考光谱来源**：splib06b 记录 → splib07 同名样品记录"
         "（53 条唯一实物参考，D1-A 同仪器+同测量类型选谱；"
         "1 条裁决覆盖偏离同仪器策略：illite_gds4 改用同样品 ASDNGb 记录以恢复 "
         "1.4 µm 带真实数据）；")
L.append("2. **5 条混合配方改接 AMX 实物记录**：splib07 AMX 系列中与 .mcf 配方同样品同配比、"
         "且仪器变体经配方合成核对的计算混合谱，烘焙后以权重 1.0 别名接入（GDS212/213 先例）"
         "——19 条混合配方中 14 条与 rf.json 逐比特一致（12 条线性合成 + 2 条 GDS 别名），"
         "5 条为 AMX 别名。")
L.append("")
L.append("因此 rf_splib07.json **不是**对 .mcf 的逐位保真移植——它是同规则、新参考的 v1.2.0 轨道；"
         "rf.json 保持不动，继续作为 .mcf 零差异保真基线。两轨道并存，由 `MicaEngine(rf_path=...)` 选择。")
L.append("")
L.append("**计数口径**：77 条规则 → 70 条唯一规则面参考（51 条直接引用 + 19 条混合谱；"
         "7 条复用——dry_veg_grass/dry_veg_nongrass/calcite/dolomite/serpentine_chrysotile 各 2 规则共享、"
         "serpentine_antigorite 3 规则共享）→ 58 条唯一实物记录（51 + 2 条仅经权重 1.0 别名引用的 "
         "GDS212/213 + 5 条 AMX 计算混合记录，合成 rec id 90008/90010/90012/90017/90021）。")
L.append("")
L.append("## 参考谱差异（53 条唯一实物参考）")
L.append("")
L.append("r = splib07 记录与 06b 原记录在 0.35–2.5 µm 公共网格上的 Pearson 相关"
         "（选谱阶段计算，同仪器同测量类型优先）。")
L.append("")
L.append("| splib06b rec | splib06b 标题 | 选定 splib07 记录 | r |")
L.append("|---|---|---|---|")
for rec, s in refs.items():
    L.append(f"| {rec} | {s['splib06b_title']} | `{s['splib07_record']}` | {s['r_vs_06b']} |")
n_hi = sum(1 for s in refs.values() if (s["r_vs_06b"] or 0) >= 0.99)
L.append("")
L.append(f"53 条中 {n_hi} 条 r≥0.99（绝大多数 ≥0.9995）；"
         "最低为 illite_gds4（GDS4，r=0.9708，1.4 µm 覆盖裁决的已接受代价），"
         "其余均在 0.999 以上。"
         "**2026-08-31 更正（一）**：dry_veg_nongrass（rec 12794）曾按名称精确匹配误选 "
         "splib07 LP-Needles-3（r=0.8839）——该记录实为 USGS 新测的健康绿叶谱；"
         "06b 'LP-Needles-3' 的真正对应是 splib07 **LP-Needles-2**（编号重排，"
         "r=0.999995），已更正映射并重建 v07 黄金基线。"
         "**2026-08-31 更正（二）**：illite_gds4（rec 4625）原按同仪器策略选 "
         "Illite_GDS4_Marblehead_BECKb_AREF（r=0.9973），但 splib07 删除了其 "
         "1.35–1.42 µm 水汽吸收带（06b 有 100 个有效采样，BECKb 仅剩 5 个，"
         "npz 中线性桥接）；裁决改用同样品全覆盖记录 "
         "**Illite_GDS4_Marblehead_ASDNGb_AREF**（1.4 µm 带 101 个真实采样、"
         "整数 nm 网格恒等烘焙，全段 r=0.9708）——规则特征窗（2.2/2.35 µm）内"
         "两记录与 06b 几乎重合，分类行为影响可忽略，已重建 v07 黄金基线。"
         "**2026-08-31 更正（三）**：jarosite_K（rec 4875）原按质量字母（aa>a）选 "
         "Jarosite_GDS99_K_200C_Syn_NIC4aa_RREF（r=0.9827），但 06b 原记录标记 "
         "W2R4Na——其 NIC4 源测量正是 quality a 记录，跨传感器变体审计证实 "
         "**NIC4a 与 06b 原记录 r=1.0000**（NIC4aa 的 0.9827 为真实重测差异），"
         "且覆盖起点更早（1.300 vs 1.424 µm）；裁决改接 NIC4a（遗产测量一致性"
         "优先于质量字母，同更正（一）同类），已重建 v07 黄金基线。")
L.append("")
L.append("## 混合谱处理")
L.append("")
L.append("- **12 条线性合成规则**：不烘焙——引擎在传感器网格重采样端元后才加权合成"
         "（`get_resample` 既有顺序），v07 轨道沿用同一口径，端元换为新参考即自动重算，"
         "无第二套插值代码。")
L.append("- **2 条权重 1.0 别名规则**（`calcite.8+montmorilloniteNa.2_mix_intimate`→GDS212、"
         "`kaolinite.2+calcite.8_mix_intimate`→GDS213）：直接引用 splib07 同名**实测**物理混合记录。")
L.append("- **5 条 AMX 别名规则**：配方与 splib07 AMX 预计算面积混合记录同样品同配比，"
         "且选定仪器变体经配方合成核对（USGS 按仪器分别计算 AMX），"
         "烘焙后以权重 1.0 别名接入（合成 rec id 90000+AMX 编号），不再由端元合成。")
L.append("")
L.append("| mix_id | 规则 | AMX 记录 | r(v07 合成) | max\\|Δ\\| | r(06b 合成) |")
L.append("|---|---|---|---|---|---|")
for a in SEL["amx_mixture_aliases"]:
    L.append(f"| {a['mix_id']} | {a['rule']} | `{a['amx_record']}` | "
             f"{a['r_vs_synth_v07']} | {a['maxdiff_vs_synth_v07']} | {a['r_vs_synth_06b']} |")
L.append("")
L.append("r<1 的原因：AMX 由 USGS 用其自择端元记录预先计算，并非本选谱表端元的数值加权和"
         "（对 06b 端元合成同样 r≈0.96–0.99，差异不来自 06b→07 重测）；max\\|Δ\\| 为 EMIT 网格上"
         "与 v07 端元合成谱的最大绝对差。**拒绝的 3 条 AMX 映射**：AMX3/AMX13 用 "
         "KGa-1 ≠ 5167(KGa-2)（mix_7703/mix_7741）、AMX14 用 HS295 ≠ 596(GDS96)（mix_7707）"
         "——端元样品不一致，维持端元合成。**AMX17**（mix_7737，27 号规则）端元正确但其 "
         "ASDNGb 变体不遵循配方（对配方合成 r=0.805，与任何 ASDNG 端元组合最高 0.956），"
         "NIC4b 变体配方保真（对配方合成 r=0.998、与同仪器端元合成 1.0000；独立佐证："
         "`docs/library_validation_report.txt` 中 AMX17 仅 NIC4 变体以 0.9999 命中本规则）；"
         "v1.2.4 曾撤销别名回到端元合成，v1.2.5 经用户裁决改接实测混合记录 "
         "**AMX17_NIC4b**（Record=13116，合成 rec id 90017，与 v07 端元合成 r=0.999996）"
         "——实测面积混合物理上优先于线性合成；**AMX12**（mix_7745）由 ASDNGa "
         "改接 NIC4a 变体（对配方合成 r 0.897→0.985）；**AMX8**（mix_7821）由 ASDNGb "
         "改接 BECKb 变体——端元 Calcite WS272/Dolomite HS102 均为 BECK 测量，"
         "同仪器变体对配方合成 r 0.995→1.0000（跨传感器变体审计，2026-08-31）。")
L.append("")
L.append("## 行为差异实证")
L.append("")
L.append("1. **烘焙口径**（`docs/splib07_export_audit.md`）：1 nm 主网格分段线性烘焙对 ASD/整数对齐记录"
         "为逐位恒等；高斯核重采样下 BECK 10 nm→1 nm 稠密化**非无损**（EMIT 网格 max|Δ| 普遍 ≤2e-2，"
         "最大 1.03e-1 于 Topaz 陡沿，r≥0.996），NIC4 ~0.93→1 nm 降采样最大 8.5e-3。"
         "烘焙同时按构造消除 BECK 粗采样的 FWHM 窗空洞（遗产空洞填平，新增空洞为 0）。")
L.append("2. **场景双跑**（`docs/splib07_dualrun_diff.md`，EMIT 全场景 1,589,760 像元）："
         "分类图差异 orth_rgb 1.956% / mus 1.431% / chl 0.005% / cal 0.123%；吸收中心连续层 Δ 中位数=0"
         "（max 1.9 nm mus / 14.0 nm cal）；99.3% 的 mus 图新增像元是方解石（+混合）→方解石+白云母混合的"
         "族间仲裁边缘漂移；cal 差异以碳酸盐族检出边缘翻转为主——v1.2.1–v1.2.5 由 AMX8_ASDNGb "
         "引起的 1,637 像元 bin 级平移（cal 0.296%）在 AMX8 改接 BECKb 变体后消除"
         "（BECKb 与 legacy 配方合成在 EMIT 网格逐点一致，max|Δ|=0.0），"
         "剩余效应主要来自 AMX10/AMX21（无配方保真变体，r=0.96 有界差异）。"
         "差异有界、可归因。")
L.append("")
L.append("## 既有结论不变")
L.append("")
L.append("- `docs/MCF_vs_rfjson_verification.md` 的全部结论绑定 rf.json，不受本轨道影响；")
L.append("- 黄金基线双轨独立：`tests/golden_arrays.npz`（legacy）与 `tests/golden_arrays_v07.npz`（v07）。")
L.append("")

with open(r"d:\CRAMM\docs\MCF_vs_rf07_diff.md", "w", encoding="utf-8") as f:
    f.write("\n".join(L))
print("wrote docs/MCF_vs_rf07_diff.md")
