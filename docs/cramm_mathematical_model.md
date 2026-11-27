# CRAMM 算法抽象与数学模型

> 日期：2026-11-25  
> 对象：当前工作树中的 `cramm/classifier.py`、`rf.json` 与生产输出契约  
> 定位：给出可复现的确定性算法模型，不将规则标签解释为概率，不将混合规则解释为生成式混合反演，不将中心产品解释为直接化学定量。

## 1. 总体抽象

CRAMM 可以写成由传感器配置和规则参数共同决定的确定性映射：

\[
\boxed{
\mathcal F_{\Theta}:(R,w,b,\chi)\longmapsto
(\hat{\boldsymbol j},\boldsymbol c_{\mathrm{mus}},
\boldsymbol c_{\mathrm{chl}},\boldsymbol c_{\mathrm{cal}},
\boldsymbol Q)
}
\]

其中：

- \(R\in\mathbb R^{N\times B}\) 为 \(N\) 个像元、\(B\) 个波段的反射率矩阵；
- \(w\in\mathbb R^B\) 为中心波长，单位 µm；
- \(b\in\mathbb R^B\) 为各波段 FWHM，单位 µm；
- \(\chi\subseteq\{0,\ldots,B-1\}\) 为有效波段索引集合，\(w_{\chi}\) 对应代码中的 `wl`；
- \(\Theta\) 包括规则库、参考谱、特征端点、权重、约束、深度比阈值和仲裁窗口；
- \(\hat{\boldsymbol j}\) 为最终规则归属，允许为无输出 \(\varnothing\)；
- 三个 \(\boldsymbol c\) 为吸收中心数组，\(Q\) 为最佳匹配规则的 fit×depth 输出。

除数值舍入和明确的异常路径外，同一输入与同一 \(\Theta\) 给出同一输出。**像元之间在分类和仲裁阶段不共享统计估计，也不进行迭代优化。**

## 2. 传感器无关的参考重采样

设第 \(j\) 条规则的参考谱为 \(q_j(\lambda)\)，定义在 0.35–2.50 µm 的 1 nm 主网格上。对目标波段 \(k\)，令：

\[
x=w_k,\qquad h=b_k/2,\qquad \sigma_k=h/\sqrt{\ln 2}.
\]

使用严格开区间：

\[
I_k=\{\lambda_i:x-h<\lambda_i<x+h\},
\]

以及权重：

\[
g_k(\lambda_i)=\exp\left[-\frac{(\lambda_i-x)^2}{\sigma_k^2}\right].
\]

在半宽处 \(|\lambda_i-x|=h\)，有 \(g_k=1/2\)。仅保留参考反射率为正且有限的采样：

\[
\widetilde q_{jk}=
\frac{\sum_{i\in I_k,\,q_j(\lambda_i)>0}g_k(\lambda_i)q_j(\lambda_i)}
{\sum_{i\in I_k,\,q_j(\lambda_i)>0}g_k(\lambda_i)}.
\]

若正权重样本为空，则 \(\widetilde q_{jk}=\mathrm{NaN}\)。该模型表达的是**传感器响应坐标变换**，不是重新训练规则，也不是改变参考谱的物理诊断含义。参考侧缓存键必须包含波段配置及规则内容；原地修改规则后需要显式使缓存失效。

代码依据：[classifier.py:251-332](../repo/src/cramm/classifier.py#L251-L332)。

## 3. 诊断特征的连续统移除

对规则 \(j\) 的第 \(f\) 个诊断特征，端点四元组为：

\[
(e_0,e_1,e_2,e_3).
\]

定义左端点集合 \(L=[e_0,e_1]\)、右端点集合 \(U=[e_2,e_3]\) 和特征区间 \(F=[e_0,e_3]\)。计算：

\[
\bar\lambda_L=\operatorname{mean}(w_L),\qquad
\bar\lambda_U=\operatorname{mean}(w_U),
\]

\[
\bar R_L=\operatorname{mean}(R_L),\qquad
\bar R_U=\operatorname{mean}(R_U).
\]

像元连续统为：

\[
C_R(\lambda)=\bar R_L+
\frac{\bar R_U-\bar R_L}{\bar\lambda_U-\bar\lambda_L}
(\lambda-\bar\lambda_L).
\]

参考连续统 \(C_q(\lambda)\) 以同样方式由参考端点均值构造。于是：

\[
y_i=\frac{R(\lambda_i)}{C_R(\lambda_i)},\qquad
x_i=\frac{q(\lambda_i)}{C_q(\lambda_i)},\qquad \lambda_i\in F.
\]

这里 \(x_i\) 是参考连续统移除剖面，\(y_i\) 是像元连续统移除剖面。参考侧 NaN 波段在编译时剔除；像元侧坏波段必须在上游通过 \(\chi\) 移除。

## 4. 2×2 闭式最小二乘、fit 与原始深度

### 4.1 线性形状拟合

CRAMM 拟合：

\[
y_i\approx \hat y_i=k_0x_i+k_1.
\]

令 \(n\) 为有效特征采样数，并定义：

\[
\Delta=n\sum_i x_i^2-(\sum_i x_i)^2.
\]

当 \(\Delta\neq0\) 时：

\[
k_0=\frac{n\sum_i x_i y_i-(\sum_i x_i)(\sum_i y_i)}{\Delta},
\]

\[
k_1=\frac{(\sum_i x_i^2)(\sum_i y_i)-(\sum_i x_i)(\sum_i x_i y_i)}{\Delta}.
\]

仅 \(k_0>0\) 的结果进入后续 fit/depth 计算。\(\Delta=0\) 时返回 NaN。

### 4.2 fit

令 \(\bar y=\frac1n\sum_i y_i\)，则：

\[
r^2=\frac{\sum_i(\hat y_i-\bar y)^2}{\sum_i(y_i-\bar y)^2}.
\]

它表示参考形状经缩放和截距调整后解释像元剖面方差的比例。**fit 不是后验概率，也不是分类正确率。**

### 4.3 原始拟合深度

定义参考深度因子：

\[
a=
\begin{cases}
1-\min_i x_i,&\operatorname{mean}(x)<1,\\
\max_i x_i-1,&\operatorname{mean}(x)\ge1.
\end{cases}
\]

原始拟合深度为：

\[
d=a k_0.
\]

该 \(d\) 是后续相对排除和深度比使用的**未加权深度**。它不等于 `feature_weight × depth`，也不等于 fit×depth。

代码依据：[classifier.py:542-698](../repo/src/cramm/classifier.py#L542-L698)。

## 5. 从特征评价到候选规则

### 5.1 三类聚合量

设规则 \(j\) 有 \(m_j\) 个诊断特征，第 \(i\) 个特征的权重为 \(w_{ji}\)。定义：

\[
F_j=\sum_{i=1}^{m_j}w_{ji}r_{ji}^2
\qquad\text{（weighted fit）},
\]

\[
D_j=\sum_{i=1}^{m_j}w_{ji}d_{ji}
\qquad\text{（weighted depth）},
\]

\[
Q_j=\sum_{i=1}^{m_j}w_{ji}r_{ji}^2d_{ji}
\qquad\text{（fit×depth）}.
\]

必须注意：

\[
Q_j\neq F_jD_j.
\]

最佳匹配使用 \(F_j\)，而 \(Q_j\) 用于材料级约束和输出。即使 \(w_{ji}=0\)，原始深度 \(d_{ji}\) 仍可参与相对排除和深度比。

### 5.2 约束链

令 \(A_j(x)\in\{0,1\}\) 表示规则 \(j\) 是否接受像元 \(x\)。它要求所有适用条件同时成立：

1. 每个诊断特征通过连续统、fit 和 depth 约束；
2. 绝对排除特征不命中；
3. 相对排除特征不命中；
4. 可选深度比约束通过；
5. 材料级聚合约束通过。

绝对排除条件可写为：

\[
r_{\mathrm{not}}^2\ge\tau_r,\qquad d_{\mathrm{not}}\ge\tau_d
\quad\Longrightarrow\quad A_j=0.
\]

相对排除使用第一诊断特征的原始深度 \(d_0\)：

\[
r_{\mathrm{not}}^2\ge\tau_r,\qquad
d_{\mathrm{not}}\ge\tau_{\mathrm{rel}}d_0
\quad\Longrightarrow\quad A_j=0.
\]

材料级约束为：

\[
F_j\ge F_{\min},\qquad
D_{\min}\le D_j\le D_{\max},\qquad
Q_j>Q_{\min},
\]

其中只使用配置中存在的阈值。

### 5.3 CRAMM 深度比扩展

当前实现使用前两个诊断特征的原始拟合深度：

\[
\rho_j(x)=\frac{d_{j1}(x)}{d_{j0}(x)}.
\]

当且仅当 \(d_{j0}>0\) 且两者均为有限值时，该比值参与拒绝：

\[
\rho_j(x)\ge\tau_j
\quad\Longrightarrow\quad A_j(x)=0.
\]

它不是 weighted depth ratio，也不是 fit×depth ratio。纯白云母/伊利石规则当前上限为 0.6，三条高岭石—白云母混合规则为 0.55。该约束只删除候选，不直接生成通用混合标签；高超阈可表示排除纯净归属或排除特定混合解释，语义取决于规则。

代码依据：[classifier.py:983-1125](../repo/src/cramm/classifier.py#L983-L1125)。

## 6. 最佳匹配与无输出

先保存所有被拒绝规则的 NaN 状态，再仅为 argmax 构造：

\[
\widetilde F_j(x)=
\begin{cases}
F_j(x),&A_j(x)=1,\\
0,&A_j(x)=0.
\end{cases}
\]

最佳匹配为：

\[
j_0(x)=\arg\max_j\widetilde F_j(x).
\]

若：

\[
\max_j\widetilde F_j(x)\le0,
\]

则输出 \(j_0(x)=\varnothing\)，即无有效鉴定。并列时 NumPy `argmax` 保留规则库顺序中的第一个索引，因此规则顺序也是确定性契约的一部分。

被拒绝状态的 NaN 快照被保留下来供仲裁验收使用，不能将“被拒绝”与“合法零 fit”混为一谈。

代码依据：[classifier.py:1791-1800](../repo/src/cramm/classifier.py#L1791-L1800)。

## 7. 二次三点吸收中心估计

对当前赢家规则的首个诊断特征，在连续统移除剖面 \(y(\lambda)\) 中找到最小值位置 \(m\)。只有 \(m\) 为窗口内部点时才取：

\[
(\lambda_1,y_1)=(\lambda_{m-1},y_{m-1}),\quad
(\lambda_2,y_2)=(\lambda_m,y_m),\quad
(\lambda_3,y_3)=(\lambda_{m+1},y_{m+1}).
\]

过三点的抛物线顶点为：

\[
c=-\frac12
\frac{(y_2-y_1)(\lambda_3^2-\lambda_2^2)
-(y_3-y_2)(\lambda_2^2-\lambda_1^2)}
{(y_3-y_2)(\lambda_2-\lambda_1)
-(y_2-y_1)(\lambda_3-\lambda_2)}.
\]

非有限顶点折叠为 NaN，输出层再记为 0，表示无有效中心。当前实现没有单独的正曲率门控，也没有完整的中心不确定度模型。中心估计的用途是连续变化描述和仲裁，不能单独证明化学成分。

代码依据：[classifier.py:362-407](../repo/src/cramm/classifier.py#L362-L407)。

## 8. 波长仲裁模型

### 8.1 带窗族与目标集合

对每个仲裁族或丰度层 \(G\)，仅保留带窗规则：

\[
G_w=\{j\in G:W_j=[l_j,u_j)\}.
\]

当前赢家 \(j_0\) 只有在 \(j_0\in G_w\)、fit 为正且中心 \(c>0\) 时才参与仲裁。目标集合为：

\[
T(c)=\{j\in G_w:c\in[l_j,u_j)\}.
\]

只有满足以下全部条件时才允许翻转：

\[
|T(c)|=1,\qquad t\neq j_0,\qquad A_t(x)=1,\qquad F_t(x)>0,
\]

其中 \(t\) 为唯一目标。无命中、出窗、歧义、目标未通过完整约束或目标 fit 非正时，均保持 \(j_0\)。

### 8.2 单次重拟合与回退

翻转后，用目标规则的首个诊断特征端点重新估计中心 \(c'\)：

\[
c_{\mathrm{final}}=
\begin{cases}
c',&c'\ \text{有限且}\ c'\in[l_t,u_t),\\
c_0,&\text{否则}.
\end{cases}
\]

这里 \(c_0\) 是仲裁前中心。仲裁只执行一次，不迭代到新的不动点。

该模型在结构上保证：

- 白云母只能在白云母族内变化；
- 绿泥石只能在绿泥石族内变化；
- 碳酸盐只能在 abundant 或 plain 各自层内变化；
- 无窗混合规则不参与仲裁；
- 仲裁不会改变其他族或丰度层的归属。

代码依据：[classifier.py:410-539](../repo/src/cramm/classifier.py#L410-L539)。

## 9. 输出模型与单谱模式差异

整景输出可写为：

\[
Y(x)=
\left(j_{\mathrm{final}}(x),
c_{\mathrm{mus}}(x),c_{\mathrm{chl}}(x),c_{\mathrm{cal}}(x),
Q_{j_{\mathrm{final}}}(x)\right).
\]

五幅 RGB 产品是这些离散/连续输出的可视化，不是额外分类结果。

单光谱 `classify_spectrum` 返回按 fit 排序的 Top-N 候选及诊断信息，呈现的是**仲裁前证据**。因此，单谱 Top-1 与整景仲裁后的最终标签可以不同，不能把两种口径混写。

混合规则名称中的比例或 `mix_intimate` 是带专用参考谱和约束的规则标签。生产算法不估计混合比例，不求解 Hapke 模型，也不执行线性光谱解混。

## 10. 数学不变量

### 10.1 候选集单调性

增加一个有效约束只会缩小候选集：

\[
\mathcal C_{\text{new}}(x)\subseteq\mathcal C_{\text{old}}(x).
\]

深度比和排除特征不会修复或提高已拒绝候选的 fit。

### 10.2 族/层不变量

对任一仲裁族或层 \(G\)：

\[
j_0\in G\ \text{且发生仲裁}
\quad\Longrightarrow\quad j_{\mathrm{final}}\in G.
\]

该性质由仲裁组的显式成员列表保证，而不是依赖数值测试结果。

### 10.3 行与并行不变量

每个像元的法方程、约束和仲裁均独立计算，因此：

\[
\mathcal F(R)=\operatorname{concat}_{s}
\mathcal F(R_{I_s}),
\]

其中 \(I_s\) 为任意行子集。当前实现使用无 BLAS 的逐像元 `einsum` 求解，并共享串行/并行仲裁实现；重建后的黄金回归已验证五数组逐位一致。

### 10.4 确定性而非正确性

可复现性表示：

\[
\mathcal F_{\Theta}(R)_1=\mathcal F_{\Theta}(R)_2.
\]

它不表示：

\[
j_{\mathrm{final}}(x)=j_{\mathrm{true}}(x).
\]

后者需要独立矿物真值，不能由相同输入的重复运行推出。

## 11. 计算复杂度与实现映射

设规则数为 \(J\)，规则 \(j\) 的特征采样总数为 \(n_j\)，则单像元主要计算量为：

\[
O\left(\sum_{j=1}^{J}n_j\right),
\]

整景近似为 \(O(N\sum_j n_j)\)，另加三个中心产品和固定次数仲裁。规则之间和行段之间均可并行；分段只改变调度，不改变数学模型。

## 12. 模型边界

1. **非概率模型**：fit、weighted fit 和 fd 不是置信度或后验概率。
2. **非生成式混合模型**：混合标签不等于组分解或丰度反演。
3. **非直接化学反演**：吸收中心是成分代理量，需要独立标定和误差模型。
4. **尺度依赖**：连续统和形状拟合受混合像元、粒度、照明、噪声及参考谱选择影响。
5. **中心边界敏感**：窄窗口与传感器采样间距相近时，小的中心误差即可改变亚型。
6. **真值独立**：库标签一致性、输出覆盖率、无输出率和场景重复性均不能替代独立精度验证。

因此，CRAMM 最准确的数学定位是：

> **一个在传感器条件化参考表示上执行的可审计、约束驱动、逐像元确定性规则映射，辅以族内/层内吸收中心仲裁和连续中心产品。**

## 13. 可执行公式验证

配套脚本：[verify_cramm_mathematical_model.py](verify_cramm_mathematical_model.py)。它对生产函数执行四组数值核验：

1. 高斯 FWHM 窗口、半宽权重和归一化；
2. 闭式 \(k_0/k_1\)、\(r^2\) 和原始深度；
3. 连续统中性条件下已知抛物线的三点顶点；
4. \(Q=\sum w r^2d\) 与 \(F\cdot D\) 的区别。

最终输出为 **4/4 PASS**。手写 \(r^2\) 与生产实现允许存在约 \(10^{-11}\) 的浮点归约顺序差异，不把代数等价误写成逐位相等。验证日志：[verification.log](../output/mathematical_model_20261125/verification.log)。
