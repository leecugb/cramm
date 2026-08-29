# Stage 5 of splib07 migration: generate docs/MCF_vs_rf07_diff.md from the
# selection table (difference declaration of the v07 track vs .mcf heritage).
import json

SEL = json.load(open(r"d:\CRAMM\docs\splib07_selection.json", encoding="utf-8"))
refs = SEL["references"]

L = []
L.append("# .mcf 与 rf_splib07.json 差异声明")
L.append("")
L.append("> 日期：2026-08-29 ｜ 数据：`docs/splib07_selection.json`（逐条 r 值）、"
         "`docs/splib07_export_audit.md`（烘焙审计）、`docs/splib07_dualrun_diff.md`（场景双跑）")
L.append("")
L.append("## 结论")
L.append("")
L.append("rf_splib07.json 的 **77 条规则与 19 条混合配方同 rf.json 逐比特一致**（诊断特征参数、"
         "约束、权重原样继承 .mcf v6a 启用态，核验见 `docs/MCF_vs_rfjson_verification.md`）；"
         "唯一差异是**参考光谱来源**：splib06b 记录 → splib07 同名样品记录"
         "（53 条唯一实物参考，D1-A 同仪器+同测量类型选谱）。")
L.append("")
L.append("因此 rf_splib07.json **不是**对 .mcf 的逐位保真移植——它是同规则、新参考的 v1.2.0 轨道；"
         "rf.json 保持不动，继续作为 .mcf 零差异保真基线。两轨道并存，由 `MicaEngine(rf_path=...)` 选择。")
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
         "最低为 dry_veg_nongrass（LP-Needles-3，r=0.8839）——splib07 仅存重测记录，"
         "裁决接受并在此声明（同 `docs/rfjson_splib07_verification.md`）。")
L.append("")
L.append("## 混合谱处理")
L.append("")
L.append("- **17 条线性合成规则**：不烘焙——引擎在传感器网格重采样端元后才加权合成"
         "（`get_resample` 既有顺序），v07 轨道沿用同一口径，端元换为新参考即自动重算，"
         "无第二套插值代码。")
L.append("- **2 条权重 1.0 别名规则**（`calcite.8+montmorilloniteNa.2_mix_intimate`→GDS212、"
         "`kaolinite.2+calcite.8_mix_intimate`→GDS213）：直接引用 splib07 同名**实测**物理混合记录。")
L.append("")
L.append("## 行为差异实证")
L.append("")
L.append("1. **烘焙口径**（`docs/splib07_export_audit.md`）：1 nm 主网格分段线性烘焙对 ASD/整数对齐记录"
         "为逐位恒等；高斯核重采样下 BECK 10 nm→1 nm 稠密化**非无损**（EMIT 网格 max|Δ| 普遍 ≤2e-2，"
         "最大 1.03e-1 于 Topaz 陡沿，r≥0.996），NIC4 ~0.93→1 nm 降采样最大 8.5e-3。"
         "烘焙同时按构造消除 BECK 粗采样的 FWHM 窗空洞（遗产空洞填平，新增空洞为 0）。")
L.append("2. **场景双跑**（`docs/splib07_dualrun_diff.md`，EMIT 全场景 1,589,760 像元）："
         "分类图差异 mus 1.43% / chl 0.005% / cal 0.078%；吸收中心连续层 Δ 中位数=0"
         "（max 1.9 nm mus / 14 nm cal）；96.6% 的 mus 图新增像元是方解石+蒙脱石混合→方解石+白云母混合的"
         "族间仲裁边缘漂移。差异有界、可归因。")
L.append("")
L.append("## 既有结论不变")
L.append("")
L.append("- `docs/MCF_vs_rfjson_verification.md` 的全部结论绑定 rf.json，不受本轨道影响；")
L.append("- 黄金基线双轨独立：`tests/golden_arrays.npz`（legacy）与 `tests/golden_arrays_v07.npz`（v07）。")
L.append("")

with open(r"d:\CRAMM\docs\MCF_vs_rf07_diff.md", "w", encoding="utf-8") as f:
    f.write("\n".join(L))
print("wrote docs/MCF_vs_rf07_diff.md")
