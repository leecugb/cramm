# 光谱重采样与特征窗波段排除逻辑审计报告

> 日期:2026-09-02 ｜ 对象:`cramm/classifier.py` `_resample_` / `_precompute_feature` / `_diagnostic_feature`,`cramm/emit_reader.py`
> 结论:**逻辑正确、无效值语义一致**;唯一数值偏差为 numpy sqrt-vs-pow 的 1-ulp 特例(已修正 docstring 中的过度声明,见 v1.4.3 提交)。

---

## 一、`_resample_` 重采样核([classifier.py:156-228](../cramm/classifier.py#L156-L228))

### 1.1 算法口径

- 开放窗口 `(x−h, x+h)`,`h = FWHM/2`;`σ = h/√ln2`(窗口边缘权重恰为 0.5)。
- 高斯加权均值 `Σ(temp·w)/Σw`。
- 快路径(searchsorted 二分定位窗口)要求全部波段为正且 `min(x−h) > 0`;否则回退原布尔掩码慢路径。两路径对**完全相同子集、相同顺序**求和。

### 1.2 无效值标记:**输入侧剔除,输出侧 NaN**

| 侧 | 机制 | 说明 |
|---|---|---|
| 输入(源样本) | `temp > 0` 过滤 | 统一剔除三类:specpr 删除标记 0、npz 量程外 NaN(`NaN > 0` 为 False)、负值。**不保留任何哨兵** |
| 输出(目标波段) | `NaN` | FWHM 窗内无源样本、或样本全部被剔除 → `res1[j] = np.nan`。绝不输出 0 或哨兵 |

实测验证(2026-09-02):zero/NaN/负样本被剔除后窗口均值正确;全无效窗口输出 NaN;近恒等重采样(1nm→1nm)有效行 max|Δ|=0。

### 1.3 数值审计发现:sqrt-vs-pow 1-ulp 特例

- 优化版向量化 `σ` 计算 `(halfs**2 / np.log(2)) ** 0.5`:numpy pow ufunc 对**数组** `**0.5` 特判为 `sqrt`;
- 原逐波段**标量** `**0.5` 走 libm `pow`——两者在个别 FWHM 值上相差 1 ulp。
- 实测:EMIT 波段 231(FWHM 8.734 nm),77×285 对中 24 个重采样值差 1.11e-16,其余全部 bit-identical。同一 caveat 适用于快/慢路径等价性。
- **影响评估**:参考谱相对量级 1e-16,对分类无影响;黄金回归链由同一实现产生与验证,不受波及。
- **处置**:不改数值路径;将 docstring 中原"bit-exact vs pre-optimization version"的过度声明修正为如实记录该 1-ulp 例外(随本审计一并提交)。

## 二、特征窗排除波段逻辑([classifier.py:419-494](../cramm/classifier.py#L419-L494))

### 2.1 参考侧:编译期剔除(不对称设计)

```python
mask = (wl <= endpts[3]) & (wl >= endpts[0])   # 波长窗
mask = mask & ~np.isnan(reference)             # NaN 列物理移出窗口
```

- `idx` 为最终窗口列集合:npz 量程外 NaN、resample 空窗 NaN 对应的波段不进入 `con_` / `B`(2×2 闭式最小二乘矩阵)/ `depth_factor` 的任何算术。
- **端点区间剔值不剔列**:`mask_left_end` / `mask_right_end` 仅按波长取,但端点均值用 `r_l[~np.isnan(r_l)].mean()`——区间内 NaN 波段参与"区间非空"判定,却被排除在均值之外。

### 2.2 三个端点异常:空窗编译期判死刑

| 异常 | 触发条件 |
|---|---|
| `InvalidRangeError` | 剔除 NaN 后整个特征窗无一有效列 |
| `InvalidLeftEndPointError` | 左端点区间 `[e0, e1]` 无波段 |
| `InvalidRightEndPointError` | 右端点区间 `[e2, e3]` 无波段 |

- 以 `{"exc": ...}` 缓存于编译产物,求值时抛**同类型新实例**([_diagnostic_feature:636-639](../cramm/classifier.py#L636-L639)),避免共享实例累积 `__traceback__`。
- classify 主循环捕获 → 规则优雅跳过。
- **触发普查**:测试套件三异常均覆盖(201/413/13 次);真实 EMIT 文件(244 有效波段)**零触发**——501 个特征窗全部编译通过。

### 2.3 光谱侧:不做 NaN 剔除(契约在上游)

- `_diagnostic_feature` 对输入光谱**没有任何 `~np.isnan`**:端点均值直接 `spectrum[np.ix_(rows, idx_l)].mean(1)`。
- 前提契约:传感器坏波段必须在上游从波段列表整体移除,`spectrum` / `wl` / `ref` 在同一套 `chanels` 上对齐。
- 残留 NaN 的兜底:mean → NaN → con → NaN → r2/depth NaN → 约束比较恒 False → 像素自然拒绝,无需专门标记。

## 三、上游坏波段移除的参与链路

```
EmitReader.load (emit_reader.py:103-105)
  每波段正值均值 < 0.02 → 整波段移除 (EMIT 285 → 244)
  chanels = np.arange(s)[~mask];  wl = w[chanels]
        │
        ▼
_get_compiled_rules (classifier.py:1398-1401)
  ref = resampled1[rule][chanels]         # 参考谱重采样到全 285 带后切片
  _precompute_feature(ref, wl, endpts)    # wl 中根本不存在被移除波段
```

- 被移除的水汽带**永远不可能落入任何特征窗**:不参与端点均值、不参与 `con_`/`B`、不可能触发三个 Invalid 异常。
- 编译缓存键 `(resample_key, wl.tobytes(), chanels.tobytes())`([classifier.py:1385-1389](../cramm/classifier.py#L1385-L1389))把波段选择列为正式编译输入,选择变化自动失效重编译。

## 四、全链无效值语义总图

```
npz NaN ──resample──> temp>0 剔除(0/NaN/负) ──空窗──> NaN
     │                                                    │
     │                       _precompute_feature: ~np.isnan 剔列
     │                       端点均值剔值 / 三异常兜底(规则跳过)
     │                                                    │
     └── 传感器坏带 ── EmitReader 移除 ──> spectrum 有限 <─┘
                        (残留 NaN 传播为像素拒绝)
```

每层只负责一种语义:源样本侧 `>0` 剔除(兼容 specpr 0 删除标记与 npz NaN),波段/特征侧 NaN 传播,传感器侧上游移除——互不重复、无缝衔接。

## 五、遗留事项

- 无 P1/P2 缺口。1-ulp 例外的处置为文档修正而非数值改动(数值路径变更将迫使黄金链全面 rebaseline,代价远超收益——与 [rf77_bundle_audit.md](rf77_bundle_audit.md) 的"维持现状"裁决同一原则)。
