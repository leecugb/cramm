# CRAMM 算法流程

配套图件:`cramm_algorithm_flowchart_nature.{svg,pdf,tiff,png}`(由 `make_algorithm_flowchart.py` 生成,Nature 期刊风格,183 mm 双栏宽)。

CRAMM 实现 USGS MICA 决策规则体系,并扩展深度比约束与白云母波长仲裁。整体为五层流水线:

## a 输入层

| 输入 | 说明 |
|---|---|
| 高光谱反射率立方体 | 任意 VNIR–SWIR 传感器;内置 EMIT L2A NetCDF 读取器(`emit_reader.py`,坏波段剔除、float32 契约)。其他传感器经同一 `(spectrum, wl, w, bp, chanels)` 七元组接入 |
| 规则库 `rf.json` | 77 条决策规则(黏土、云母、碳酸盐、硫酸盐、绿泥石、角闪石、铁氧化物、冰雪及混合矿物)+ 19 条 mixture 定义 + 53 条 wavelength_map |
| USGS splib06b | 参考光谱库,随 wheel 捆绑 |

## b 预处理层

1. **坏波段剔除与波段配置** — `(w, bp, chanels)`:中心波长、FWHM、有效波段掩码。
2. **参考光谱重采样** — splib06b 记录按传感器波长/FWHM 高斯核重采样(`get_resample`,按波段配置缓存)。
3. **规则编译** — 连续统端点、波段索引、法方程常数 B、深度因子一次性预计算(两级缓存;暖启动单光谱 ≈10 ms,约 16× 加速)。

## c 决策规则核心层

对每条规则(77 条,跨规则 `multiprocessing` 并行,spawn 上下文,BLAS 单线程固定 → 串行≡并行位级一致):

1. **连续统去除** — diagnostic features 的特征区间连续统去除。
2. **2×2 闭式最小二乘** — 拟合参考-像元组合,得 fit (r²) 与 absorption depth(`_fit_r2_depth`)。
3. **排除特征过滤** — not-absorption / not-related 特征作为排除滤波器。
4. **约束审计** — MICA 五层约束(fit / depth / continuum / weighted / ratio_max)+ **CRAMM 深度比约束** `max_depth_ratio_feat1_over_feat0`(9 条白云母-伊利石规则携带,抑制次生吸收过深的假阳性)。

## d 综合判读层

1. **最佳匹配** — 逐像素 `argmax(fit × depth)`。
2. **白云母 2.2 µm 吸收中心二次拟合** — `mus_center`(`_get_quadratic_center`),化学成分代理量。
3. **波长仲裁亚型归属** — `absorption_center_range` 窗口(medhighAl [2.195,2.200) / medAl [2.200,2.206) / lowAl [2.206,2.210) / Fe-rich [2.210,2.220),互不重叠)对白云母像元重仲裁(`_reassign_by_absorption_center`);中心无效或出窗时保持原匹配(保守策略)。
4. **绿泥石 2250 nm 吸收中心二次拟合** — `chl_center`,三条纯绿泥石规则(chlorite_lowFe / clinochlore / clinochlore_Fe)胜出像元,用胜方规则 feat0 端点拟合;作连续成分图层输出,解读走 chl13 M1 标定(LOO 1.0 nm)。
5. **绿泥石宽容窗口仲裁** — 三规则的 `absorption_center_range` 窗口故意重叠 1 nm(lowFe [2.245,2.248) / clinochlore [2.247,2.252) / Fe [2.251,2.25549)):`chl_center` 落入重叠带 → 命中两窗 → 歧义 → 保持原匹配(重叠即容差区,中间成分不被强行归类);仅当中心**排他性**落入另一规则窗口时才重判,并以目标规则端点重拟合中心一次。翻转后中心仍作连续图层输出。

## e 输出层

| 模式 | 产品 |
|---|---|
| 整景 | 矿物图 · 彩色增强图 · 白云母中心图 · 绿泥石中心图(4 幅 uint8 RGB)+ `mus_center`/`chl_center`/`fd` 浮点数组 → GeoTIFF(pyresample 正射校正)/ npz |
| 单光谱 | Top-N 矿物排序 `{"name", fit, fd}` + 多页 PDF 诊断报告(逐规则特征解剖与约束审计) |
