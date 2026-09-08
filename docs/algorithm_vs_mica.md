# CRAMM 算法逻辑梳理与 USGS MICA 原算法对比

> 归档日期:2026-09-06 ｜ 基线:v1.5.0.post1(PyPI 已发布)
> 合规基线:[`mica_compliance_audit.md`](mica_compliance_audit.md)(2026-08-25,计算核 13 项逐条与官方定义一致,本文不重复其字段级核验)
> 相关对账:[`arbitration_windows.md`](arbitration_windows.md)(三族窗口实测)、[`resample_feature_window_audit.md`](resample_feature_window_audit.md)(重采样/特征窗无效值语义)、[`arbitration_audit.md`](arbitration_audit.md)(仲裁 30 项检查)、[`algorithm_flow.md`](algorithm_flow.md)(流水线速查)

---

## 一、算法全链路(v1.5.0 现状)

### 1. 输入层 — 传感器无关契约

- 一切下游消费七元组 `(spectrum, wl, w, bp, chanels)`:反射率立方体、有效波段波长、
  全波段中心波长、FWHM、有效波段索引。
- 内置 EMIT L2A 读取器(`emit_reader.py`):float32、填充值归零、**坏波段剔除**
  (逐波段正均值 < 0.02 → 该波段从 chanels 移除);其他传感器自备加载器走同一契约。
- 规则库 `cramm/data/rf.json`:77 条决策规则,与官方
  `.mcf` v6a 启用态**字段级一致**;v1.4.0 起 id-free,规则名是规则库与参考谱束的唯一链接。
- 参考谱束 `cramm/data/rf77_splib07_1nm.npz`:77×2151,350–2500 nm 1 nm 主网格,
  splib07 选谱(选谱审计见 `splib07_selection.md`);19 条混合规则的谱在打包期预烘焙,
  运行时零合成、零外部库依赖。

### 2. 预处理层 — 重采样 + 规则编译

- **参考重采样** `_resample_`(classifier.py:174-256):1 nm 主网格 → 传感器波段,
  高斯核,开窗 `(x−h, x+h)`、`σ = h/√ln2`(h = FWHM/2),`temp > 0` 过滤
  (0 / NaN / 负值采样剔除),空窗 → NaN。按 `(w, bp, chanels)` 缓存。
- **规则编译** `_get_compiled_rules`(:1389)/ `_precompute_feature`(:442):
  端点四值 → 左右区间均值端点;**参考侧 NaN 列编译期剔除**;法方程常数 B、深度因子
  一次性预计算;两级缓存(暖启动单光谱 ≈10 ms)。无效端点配置抛
  InvalidRange/LeftEndPoint/RightEndPoint → 该规则列置零并记日志。
- **无效值语义链**:上游坏波段移除(读数) → 参考侧编译期剔除 → 像元侧不再过滤
  (契约:坏波段必须在上游移除)。完整链条见 `resample_feature_window_audit.md`。

### 3. 决策规则核心(77 规则,跨规则 `multiprocessing` 并行)

对每条规则、每个像元:

1. **连续统去除** `_diagnostic_feature`(:601):直线连续统过两端点
   (均值波长, 均值反射率),逐通道相除(DS787 Eq.1)。
2. **2×2 闭式最小二乘** `_fit_r2_depth`(:545):`con ≈ k0·con_ + k1`,
   无 BLAS `np.einsum` 求解(串并行逐比特一致的结构保证);k0>0 掩膜;
   fit = r²,depth = k0·(1 − min con_)(缩放参考深度,乘性 scale 释义)。
3. **特征加权**:weighted fit = Σ wᵢ·r²ᵢ,Σwᵢ = 1。
4. **约束过滤**:MICA 五层(特征级 fit/depth、连续统 8 槽、NOT 绝对/相对特征、
   材料级 WEIGHTED_FIT_DEPTH 4 槽、约束违反置零)+ **CRAMM 深度比约束**
   `max_depth_ratio_feat1_over_feat0`(9 条白云母/伊利石/混合规则携带)。

### 4. 综合判读层

1. **最佳匹配**:`argmax(weighted fit)`;全零像元 → 背景(kokaly2011 规范)。
2. **三族吸收中心拟合** `_get_quadratic_center`(:258):对赢家规则 feat0 窗内
   CR 剖面取 argmin 三点做抛物线顶点拟合;窗口边缘极小值 / ±inf 顶点(精确共线)
   折叠为 NaN → 0。产出 `mus_center`(2.2 µm)/ `chl_center`(2250 nm)/
   `cal_center`(2330 nm)连续图层。
3. **波长仲裁** `_reassign_by_absorption_center`(:309),三态判定:
   0 命中(出窗/无效)→ 保持;≥2 命中(歧义)→ 保持;恰好 1 命中且非当前 →
   **翻转 + 按目标规则端点重拟合中心一次**。五道门控(member / fit_pos / 中心有效 /
   唯一命中 / 目标 fit 非 NaN 且 > 0),窗口左闭右开,**族锁定**(仲裁组 = 族列表 ∩
   带窗规则,跨族结构不可能)。三个仲裁组:

   | 族 | 带窗成员 | 窗口结构 | 语义 |
   |---|---|---|---|
   | 白云母 | medhighAl / medAl / lowAl / Fe-rich | 无缝拼接 [2.195, 2.220) | 确定性仲裁到唯一亚型 |
   | 绿泥石 | lowFe / clinochlore / clinochlore_Fe / thuringite | 无缝拼接 [2.245, 2.266) | 同上 |
   | 碳酸盐(v1.5.0) | abundant 对 + plain 对 | **按丰度层两次调用**:dolomite [2.308,2.328) vs calcite [2.334,2.350),6 nm 死区 [2.328,2.334) | 对内竞争,跨层结构不可能 |

### 5. 输出层

- **整景**:矿物图 / 彩色增强图 / 白云母中心图 / 绿泥石中心图 / 碳酸盐中心图
  (5×uint8 RGB)+ `mus_center` / `chl_center` / `cal_center` / `fd` 浮点数组,
  GeoTIFF(pyresample 正射)或 npz。
- **单光谱**:Top-N `{"name", fit, fd}` + 多页 PDF 诊断(逐规则特征解剖与约束审计);
  **不做仲裁**(既有设计差异,审计 P3 已记录)。

---

## 二、与 USGS MICA 原算法的对比

### 2.1 计算核:逐项一致(13/13)

`mica_compliance_audit.md` 以 DS787(方法学)、kokaly2011(PRISM/MICA 论文)、
`.mcf` v6a 字段语义为基准逐条核验:连续统去除、端点区间取值、线性回归 r²、
缩放参考深度、特征加权、特征级约束、连续统约束、NOT 特征、材料级约束、
违反置零、argmax(weighted fit) 选优、全零无匹配、无效端点工程化处理——
**全部一致**。唯一不可字节级确认项:IDL 源码不可得,"scale 是否含截距 k1"
采用乘性释义(DS787_summary §21),1,136 个约束槽在该释义下经生产验证。

### 2.2 CRAMM 的算法扩展(MICA 无,均有文档声明)

| # | 扩展 | 内容 | 动机 |
|---|---|---|---|
| 1 | **深度比约束** | `max_depth_ratio_feat1_over_feat0`,9 条规则 | 次生 2.35 µm 吸收过深 → 非白云母;抑制白云母假阳性 |
| 2 | **吸收中心产品线** | mus/chl/cal_center 三个连续图层 | 从"矿物检测"到"成分定量" |
| 3 | **波长仲裁** | 12 条带窗规则、三族;v1.5.0 碳酸盐按丰度层对内竞争 | 亚型定义在波长轴上,argmax 之外用带位重裁决 |
| 4 | **成分解读框架** | chl13 标定(LOO-RMSE 1.0 nm);白云母 GEMS 相图框架 | 中心波长到化学成分的标定链 |

### 2.3 数据与工程差异(非算法偏离)

| 维度 | MICA 原版 | CRAMM | 核验 |
|---|---|---|---|
| 实现 | IDL / ENVI 生态 | 纯 Python,pip 安装,Py3.9–3.13 | — |
| 参考谱轨 | splib06b specpr,运行时读取 | 1 nm splib07 预烘焙束(v1.3.0 起唯一轨道;19 条混合谱 v1.3.1 起预烘焙) | corr 中位 0.99972 / 0.99474 |
| 重采样 | HyMap 预卷积库 | 运行时高斯核,任意传感器 | 同上 |
| 传感器 | 特定载荷 | 任意 VNIR–SWIR(七元组契约) | EMIT 内置 |
| 数值纪律 | 不可考 | einsum 无 BLAS、串并行逐比特、黄金回归链 | 5/5 array_equal |
| 规则链接 | splib 记录号 | id-free 规则名(v1.4.0) | 装载期契约校验 |

### 2.4 规则库与 `.mcf` v6a 的差异清单

- **字段**:启用态规则数值零不一致(前置核验,verify 脚本已归档)。
- **参考谱选谱审计**(v1.2.2–v1.2.6):dry_veg_nongrass → LP-Needles-2;
  illite_gds4 → ASDNGb 全覆盖重测版;jarosite_K → NIC4a;
  AMX 计算混合谱 5 条按"配方保真 + 同仪器优先"策略别名接入。
- **族定义**:serpentine_antigorite_or_calcite+dolomite 排除出碳酸盐族
  (其参考为 antigorite,非碳酸盐)。
- **权重舍入**:6 条规则 Σw 偏差 ≤2e-6(.mcf 四位小数舍入,原样继承)。
- **known self-miss**:纯 calcite / dolomite 参考不满足自身 plain 规则约束,
  自识别时 abundant 变体胜出(测试套件文档化,`KNOWN_SELF_MISS`)。

### 2.5 仲裁与中心的实测影响

- **白云母 / 绿泥石**:生产翻转统计见 `arbitration_stats.md`;
  窗口结构 2026-08-26 由容差重叠重置为无缝平铺(确定性仲裁)。
- **碳酸盐 v1.5.0**(EMIT 025 全场景):plain 对 calcite→dolomite 翻转 1599 像元
  (0.10% 场景 / 2.1% 碳酸盐赢家,中心 2314–2328 nm,即铁白云石带位),
  反向零翻转,abundant 对零翻转;817 候选被目标 fit 门控挡回
  (100% 倒在 min_weighted_fit=0.64 / fit×depth≥0.045);重拟合 100% 在窗。
- **设计边界**:单光谱 Top-N 呈现仲裁前证据,可能与整景最终归属不同
  (审计 P3,建议在对外文档中明示)。

---

## 三、状态小结

CRAMM = **MICA 计算核(13 项逐条一致)+ 4 项声明式算法扩展 + 1 nm splib07
预烘焙参考轨 + 传感器无关工程化 + 逐比特数值纪律**。截至 v1.5.0.post1:
PyPI 已发布(wheel 纯净运行时集);GitHub 公开树为最小运行集(13 文件 + 2 张
README 插图);干净 venv 安装后全量审计通过(自识别 8/8、test_core 14 过、
test_custom_rules 7/7、test_single_spectrum 7/7、黄金回归 5/5 array_equal)。

## 四、相关档案

- `docs/mica_compliance_audit.md` — 计算核 13 项合规核验(字段级)
- `docs/MCF_v6a_summary.md` / `docs/DS787_summary.md` / `docs/kokaly2011.md` — 原始定义研读
- `docs/arbitration_windows.md` / `docs/arbitration_audit.md` / `docs/arbitration_stats.md` — 仲裁窗口/审计/生产统计
- `docs/resample_feature_window_audit.md` — 重采样与特征窗无效值语义链
- `docs/rf77_bundle_audit.md` / `docs/splib07_selection.md` — 1 nm 谱束烘焙与选谱审计
- `docs/lowfe_feat2_bias.md` — chlorite_lowFe feat2 打分惩罚(既有风险,已接受)
