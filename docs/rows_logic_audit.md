# rows 存活像元逻辑审计报告

> 审计日期:2026-08-25 ｜ 基线:c75882d(MICA 合规审计)之后;本报告与 einsum 修复同提交
> 审计对象:`cramm/classifier.py` 活像元限制(alive-pixel restriction / rows subset)性能优化及其「与全量计算逐比特等价」声明
> 审计方法:代码链路透析 + 既有单元差分(check_rows_logic.py)复审 + **新增端到端 A/B 差分**(check_alive_restriction.py)+ BLAS 行为受控实验

## 结论

1. **活像元簿记逻辑本身完全正确。** alive_rows 生命周期——初始化(None=全量)、逐特征更新(`~isnan(weighted r2)`)、早停、NOT 特征排除集与重算、相对深度阈值子集化、深度比约束——逐阶段推理与端到端 A/B 实验双重确认:跳过已拒绝像元不改变任何存活像元的数值与最终判定。
2. **审计发现一个更底层的缺陷,使「逐比特等价」在修复前并不普遍成立:** k0/k1 法方程求解(`B.dot(con.T)`)走 BLAS dgemm,MKL 的核选择/分块随**行数 m** 与**线程数**变化,同一像元在子集调用与全量调用中可得到 ulp 级不同的 k0/k1(实测 3400 像元段上 797 个像元 fit 值不同)。该缺陷同时波及串行(默认 36 线程)与并行(1 线程 worker)路径的位级一致性——`test_parallel` 修复前 `color_enhanced` 有 8 个差异像元。
3. **修复:`_fit_r2_depth` 改用 `np.einsum("mj,kj->mk", con, B)`**(纯 C 循环,无 BLAS)。修复后逐比特等价由「碰巧成立」变为「结构成立」:m 扫描/子集/线程受控实验全部位级一致;端到端 A/B 77 规则 + classify + 编译路径全过;整景计时无回归(nw=8:71.7s,修复前 72.9s;einsum 调用本身仅 1.2–1.9× dgemm 耗时)。
4. **影响面:判定级零差异**(NaN 模式、argmax、约束决策在全部测试中一致);产品级仅 color_enhanced 6 个像元 ±1 级(fit 分档边界翻转)。golden 已按重基线程序审计重写(tests/rebaseline_golden.py,审计逻辑已更新为本变更)。

## 机制:alive_rows 生命周期

```
alive_rows = None                    # 首诊断特征永远全量评估
for 诊断特征:
    若 alive_rows == 空: break       # 早停:后续特征结果必全 NaN
    r, d, fdd, raw_d = _diagnostic_feature(..., rows=alive_rows)
    fit += r; depth += d; fd += fdd; _feat_raw.append(raw_d)
    alive_rows = ~isnan(r) 的位置    # r 为加权 r2;权重 0 → r=0.0(非 NaN)仍存活
for 绝对 NOT 特征:
    bad = _not_absolute_feature(..., rows=alive_rows)   # 排除集 ⊆ alive
    fit[bad] = NaN; 若 bad 非空: alive_rows = ~isnan(fit) 的位置
for 相对 NOT 特征:
    RELATIVE_FEATURE_DEPTH = _feat_raw[0]               # 第 1 诊断特征原始深度
    bad = _not_relative_feature(..., rows=alive_rows)   # 阈值 = 阈值系数 × RFD[rows]
    fit[bad] = NaN; 若 bad 非空: alive_rows = ~isnan(fit) 的位置
深度比约束(_feat_raw 全长数组,不更新 alive_rows,其后无 rows 受限计算)
加权约束(全长比较,NaN → False → 置 NaN)
```

## 逐项验证表

| # | 验证项 | 方法 | 判定 |
|---|---|---|---|
| 1 | `_diagnostic_feature` rows 子集:4 个返回值在子集位置逐比特一致、子集外全 NaN | check_rows_logic §1(calcite 全特征) | ✅ |
| 2 | `_get_fit` / not_abs / not_rel:子集排除集 = 全集 ∩ 子集 | check_rows_logic §2–3 | ✅ |
| 3 | 累积不变性:被拒像元 fit 已为 NaN,NaN+x=NaN;活像元累加序列与全量相同 | 链路透析 | ✅ |
| 4 | alive 语义 `~isnan(r)`:权重 0 → r=r2×0=0.0(非 NaN)存活——22 条规则携带零权重特征(含全部 4 条绿泥石、calcite/dolomite_abundant);实测 7,524 像元经零权重特征存活(clinochlore 3,831、thuringite 2,756、chlorite_lowFe 867、alunite_K_250C 62、gypsum 8) | check_alive_restriction §2 | ✅ |
| 5 | 早停 `len(alive)==0`:`_feat_raw` 长度与 depth-ratio 的 `len>=2` 守卫协同;全量下等价(后续特征必全 NaN,`_valid` 全 False) | 链路透析 | ✅ |
| 6 | not_rel 阈值 `RELATIVE_FEATURE_DEPTH[rows]`:rows ⊆ 第 1 特征存活集 → 全非 NaN,物理深度比较有效 | 链路透析 + check_rows_logic §3 | ✅ |
| 7 | 深度比约束:全长 `_feat_raw` 数组,`_valid` 三条件守卫;不更新 alive_rows 但其后无 rows 受限计算 | 链路透析 | ✅ |
| 8 | 加权约束:全长比较,NaN → False → 置 NaN(幂等) | 链路透析 | ✅ |
| 9 | **k0/k1 求解的行数/线程独立性** | 受控实验(见下节) | ❌ 修复前(BLAS dgemm)→ ✅ 修复后(einsum) |
| 10 | 端到端:77 规则 (fit, fd) rows-on vs 强制全量,30,000 像元逐比特 | check_alive_restriction §1 | ✅(修复后) |
| 11 | 端到端:classify() 序列(num/fit/depth/mus/chl/cal)两块 tile rows-on vs 强制全量 | check_alive_restriction §3 | ✅(修复后;修复前 tile A fit/depth 1 像元 ulp 差异) |
| 12 | 编译路径:classify_spectrum 200 抽样 top-5 rows-on vs 强制全量 | check_alive_restriction §4 | ✅ |

## BLAS 缺陷:发现、证据与修复

### 证据(本机 numpy 2.4.2 + MKL 2025,36 线程默认)

- **行数依赖**:`B.dot(con.T)`(2×30 @ 30×m)在 m=797 时结果与 m=3400 计算的前 797 行**不一致**;m 扫描显示 MKL 在 m≲150 以下切换小矩阵核、多线程下另有分块重组。单线程(mkl limit=1)后 m 依赖依然存在(小 m 区间异核)。
- **线程依赖**:固定 m=3400,36 线程与 1 线程结果**不一致**。
- **生产暴露**:thuringite 规则 3400 像元段 rows-on vs 强制全量,797 像元 fit 值 ulp 级不同(NaN 模式一致);`test_parallel` 修复前 color_enhanced 8 像元差异。
- **为何既有测试未捕获**:check_rows_logic 用 ~99k 像元及其大子集——m 始终处于同一 MKL 核区间,碰巧一致;check_compiled_path 同理。逐件验证通过 ≠ 链接后等价,这是本轮新增端到端 A/B(check_alive_restriction.py)的原因。

### 修复

`_fit_r2_depth` 中 `k = B.dot(con.T)` → `k = np.einsum("mj,kj->mk", con, B)`。einsum 为 numpy 纯 C 循环、无 BLAS 调用、单线程,逐像元结果只依赖自身行:

- m 扫描(1…3999)、任意子集、线程数(1/36)受控实验:全部位级一致;
- 性能:m=3,400 时 0.157ms vs dgemm 0.083ms(1.9×);m=500,000 时 24.8ms vs 21.4ms(1.16×);整景 nw=8 计时 71.7s vs 修复前 72.9s——**无回归**(k 求解在总运行时长中占比极小);
- 该函数是 `_diagnostic_feature` 与 `_get_fit` 共享的唯一实现,一处修复覆盖全部调用路径(诊断特征、NOT 特征、编译路径、单光谱)。

### 修复后验证矩阵

| 套件 | 结果 |
|---|---|
| check_alive_restriction(新,端到端 A/B) | 全过:77 规则逐比特 + classify 两 tile + 编译路径 200 抽样 |
| check_rows_logic | 全过 |
| check_compiled_path(302 px × 77 规则) | 全过 |
| check_arbitration_independence | 跨族零翻转证据维持 |
| test_core | 21/21 |
| test_custom_rules / test_single_spectrum / test_parallel_isolation | 7/7、7/7、6/6 |
| test_parallel(整景 golden,nw=4) | **5/5 全 True**(修复前 color_enhanced=False,8 像元) |

## golden 重基线记录

einsum 改变全场景 fit/fd 的 ulp 值 → golden 需重基线。tests/rebaseline_golden.py 的守卫式审计已更新为本变更(原 thuringite 审计见 git 历史):四幅判定/中心/正射数组要求逐比特一致,color_enhanced 差异要求处于 ulp 边界量级(<100)。实测:

- orth_rgb / mus_image / chl_image / cal_image:**逐比特一致**;
- color_enhanced:6 像元,均为单通道 ±1 级(fit 分档边界):(135,663)、(737,799)、(908,975)、(947,919)、(1000,755)、(1222,1044)。

## 观察项(不改变结论)

1. **参考侧 B 预计算仍含 BLAS**(`Scc = np.dot(con_, con_)`,_precompute_feature):固定形状、与像元行数无关、按波段配置缓存——机内确定性无问题;跨机/跨 BLAS 的 golden 可移植性本就不保证(README「golden baseline is platform-bound」),维持现状。
2. **严格位级判据**:A/B 比较采用 uint64 位比较(NaN≡NaN 归一化),+0/−0 与 NaN payload 均纳入;修复后全部通过。
3. **einsum 累加顺序依赖 numpy 实现版本**:逐比特声明按「同机同环境」理解,与 golden 同机锚定策略一致;跨环境以判定级一致为保证。
4. **并行 worker 的 BLAS 单线程固定保留**:einsum 已使 k 求解无 BLAS,但保留线程限制作为纵深防御(参考侧/未来 BLAS 用途、内存控制)。
5. **本审计建立的 A/B 方法**(monkeypatch 强制 rows=None 复现真全量计算)是检验一切「跳过计算不改变结果」类优化的通用手段,已固化为 tests/check_alive_restriction.py 常驻套件。
