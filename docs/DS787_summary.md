# DS787 内容梳理(面向 Computers & Geosciences 论文)

> 原文存档:[../DS787.md](../DS787.md)(由 `D:\CRAMM\DS787.pdf` 经 pypdf 提取,36 页)
>
> **文献**: Kokaly, R.F., King, T.V.V., and Hoefen, T.M., 2013, Surface mineral maps of Afghanistan derived from HyMap imaging spectrometer data, version 2: U.S. Geological Survey Data Series 787, 29 p. http://pubs.usgs.gov/ds/787/
>
> **定位**: MICA 的旗舰应用报告 —— 阿富汗 HyMap 全国矿物填图 version 2。比 IGARSS 2011 四页短文(kokaly2011.md)信息量大得多,含 MICA 算法的首次公式化。

## 1. 数据与处理规模

- 218 条 HyMap 航带(207 标准 + 11 交叉定标),2007-08-22 至 10-02,WB-57 平台 15,240 m
- 覆盖阿富汗 >438,000 km²,0.43–2.48 µm,128 通道,23 m 分辨率
- 镶嵌为 29 个按获取日期组织的 image tiles
- MICA 跑两遍:**1-µm command file**(铁矿物等 VNIR 吸收)+ **2-µm command file**(碳酸盐/层状硅酸盐/硫酸盐等 SWIR 吸收)→ 两张主题图 + summary images + fit/depth 图层

## 2. MICA 算法的公式化(DS787 方程 1–2)

- 连续统去除:**R_C(λ) = R_O(λ) / R_L(λ)** (Clark & Roush 1984)
- 吸收深度:**D(λ) = 1 − R_C(λ)**
- **band center** = 连续统去除特征最小值位置(最大深度处)
- **band depth 不直接计算**:将参考特征缩放(scale)到像元光谱后取值,以抑制遥感噪声影响(Kokaly 2011; Clark et al. 2003)→ CRAMM `_fit_r2_depth` 的深度因子对应此设计
- fit = 连续统去除特征间线性回归的 **r²**;多特征加权平均,**权重 ∈ [0,1] 且 Σ=1**,得 overall/material fit;best match = material fit 最高者

## 3. 约束体系(比 IGARSS 2011 更细)

| 层级 | 内容 |
|---|---|
| 特征约束(逐特征) | fit、depth、F×D 阈值 |
| 连续统约束(逐特征) | 左/右端点 R_c1、R_c2,中点 R_cmind,端点比 R_c2/R_c1 |
| 材料级约束 | 整体 fit / depth / F×D |
| NOT features | **分 absolute 和 relative 两种**(IGARSS 文未区分) |

违反任一约束 → 该材料置零;全部置零 → not classified。

## 4. 指挥文件(.mcf)

- version 2 的两个 .mcf 随报告公开:`mcf_afghan_hymap_1micron_ver2.mcf` / `mcf_afghan_hymap_2micron_ver2.mcf`(含参考光谱清单、诊断特征、阈值)+ 配套 `*_colors.txt` 类别颜色表
- → **CRAMM rf.json(77 规则 + 19 mixture + 53 wavelength_map)的直系祖先**;论文中应说明规则库在 .mcf 基础上的重构/扩展关系
- 参考光谱选自 USGS splib06a(Clark et al. 2007, DS 231)

## 5. 与 CRAMM 直接相关的三个 precedent

1. **白云母 Al 亚型**(Table 2 + Fig. 11 Panjsher Valley AOI):`muscovite_lowAl / medAl / medhighAl / Fe-rich` 四类,用不同 Al 含量参考光谱区分。
   → **CRAMM 的 mus_center 波长仲裁亚型(lowAl/medAl/medhighAl/Fe-rich)将"多参考光谱投票"升级为 2.2 µm 吸收中心连续定量填图** —— C&G 论文最硬的一条创新 lineage
2. **类别合并**(summary image → thematic map):同矿物不同化学成分/粒度的参考光谱结果成图时合并(Na/Ca 蒙脱石→Montmorillonite;绿泥石+绿帘石→Epidote or chlorite)→ 对应 CRAMM 输出层渲染归并
3. **fit/depth 定量图层**公开分发(×10000 存 int16)→ CRAMM `--raw` npz(mus_center + fd)是同一产品理念的延续

## 6. 工程与已知局限(Methods/Discussion 素材)

- 大气校正链:ACORN(按 100 m 高程增量分档)→ RTGC 地面定标(5 个定标场)→ CCRTGC 交叉航带定标;定标不属于 MICA 本身,MICA 输入是反射率立方体 —— 与 CRAMM 读取器/分类器解耦的分层论述一致
- DS787 自承局限:云/云影漏检致 not-classified 或假阳性(绿植被、碳酸盐偶被分出)、航带边缘接缝、太阳角差异、湿土误判为冰雪(>3150 m 重分类补丁)、sortie 28 沙尘暴未校正
- → 可在 CRAMM 论文 Discussion 中呼应"约束审计(NOT features + 五层约束)如何抑制此类假阳性"
- DS787 自指未来方向:未分类像元的光谱特征研究、低 fit 区域的其他矿物可能、接缝区定标改进

## 7. 数据产品(Table 3)

- 两张主题图 + 两张 MICA summary image(byte,ENVI .dat/.hdr/.xml)
- fit/depth 各两张(int16,×10000),37,679 × 39,594 像元,WGS84 经纬度
- wetsoils 矢量(shp/evf)
- 栅格左上角:61.66019664°E, 37.67081649°N;像元 0.00024753° × 0.00020737°
