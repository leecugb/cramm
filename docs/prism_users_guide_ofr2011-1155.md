# PRISM User's Guide (OFR 2011-1155) — 官方安装与环境信息归档

- 源文件: `D:\paper\PRISM User's Guide.pdf`（7 页节选：目录残页 + 正文 pp. 1–6）
- 完整文档: Kokaly, R.F., 2011, PRISM: Processing Routines in IDL for Spectroscopic Measurements (Installation Manual and User's Guide, Version 1.0), U.S. Geological Survey Open-File Report 2011-1155（目录显示全文至 p. 430）
- 本地全文复核来源（2026-11-25）: `/home/lee/Documents/ofr2011-1155-17oct2011.pdf`
- 方法复核: Module 4 明确参考谱与观测谱须具有等效采样和 FWHM；fit 为 r²；weighted fit 为特征 fit 加权和；depth 为参考特征拟合到观测谱后的 scaled depth；附录 A6 明确 weighted fit×depth 为各诊断特征 fit×depth 乘权后求和，支持 \(Q=\sum_iw_ir_i^2d_i\)，不支持改写为 \(F\cdot D\)。
- 分发复核: 安装章节要求复制 `usgsprism_v1_envi48.sav` 到 ENVI `save_add`，因此应将软件环境准确写为 compiled PRISM/IDL byte code，而非仅依据 4 页会议论文删除编译属性。
- 归档日期: 2026-08-24 ｜ 提取方式: pymupdf 全文抽取
- 用途: 算法背景 / 传感器绑定论证 / benchmark.md PRISM 计时 protocol 的官方环境依据

---

## 1. 官方运行环境要求（p. 2，原文）

> "PRISM version 1.0 was compiled using a full ENVI 4.8+IDL 8.0 license running on a computer with a 64-bit version of the Windows 7 operating system. PRISM requires a licensed version of ENVI 4.8. Full functionality requires the iTools component of IDL. PRISM was tested on computers with full ENVI+IDL versions installed on 32-bit Windows XP, 64-bit Red Hat Linux, and Apple OSX 10.6 systems. PRISM operated correctly in runtime versions of ENVI 4.8 on these systems."

- **编译环境**: ENVI 4.8 + IDL 8.0 全许可，64 位 Windows 7
- **运行门槛**: 必须有 ENVI 4.8 许可；完整功能需 IDL iTools 组件
- **官方测试平台**: 32 位 Windows XP / 64 位 Red Hat Linux / Apple OSX 10.6（ENVI 4.8 runtime 可运行）

## 2. 分发形式 = 闭源的一手证据（p. 4，Installation 节）

安装步骤（原文五步）：
1. ENVI 4.8 必须已安装；
2. 从 http://pubs.usgs.gov/of/2011/1155/ 下载（或光盘）；
3. 解压 `usgsprism.zip` 到 `C:\usgsprism\`（Windows）或 `/var/local/usgsprism/`（Linux）；
4. **将编译好的 `usgsprism_v1_envi48.sav` 拷入 ENVI 的 `save_add` 目录**（典型路径 `C:\Program Files\ITT\IDL\IDL80\products\ENVI48\save_add\`）；
5. 启动 ENVI，菜单栏出现 PRISM 六项。

**要点**：分发物是 IDL 编译字节码 `.sav` 文件，不附源代码——这是 "distributed only as compiled IDL byte-code" 软件环境说明的官方出处。

## 3. 软件结构（pp. 1–4）

- PRISM = 四模块：(1) ViewSPECPR；(2) spectral analysis functions；(3) image processing functions；(4) **MICA**；
- 数据库格式 SPECPR（Clark, 1993），记录头含波长记录与 bandpass（FWHM）记录指针，历史字段可追溯每谱来源；
- 随附 splib06a（USGS Spectral Library Version 6，Clark et al., 2007）；
- **Function 2.8（spectral interpolation）与 Function 2.9（convolution）**：将 USGS 光谱库从其原生光谱特性转换到成像光谱仪（AVIRIS、HyMap 等）的波段配置——即"换传感器 = 重建参考库"链的官方功能出处；
- MICA 命令文件为用户创建/编辑文档，定义参考谱、诊断特征连续统端点、fit/depth/连续统约束；附录 A 关键词表（目录摘录）：A1 可选 setup 关键词（p. 280）、A2 NOT 特征定义（p. 285）、A3 参考谱设置（p. 286）、A4 诊断特征定义（p. 288）、A5 NOT 特征调用（p. 291）、A6 WEIGHTED_FIT_DEPTH_CONSTRAINTS（p. 294）；
- MICA 分析入口：Function 4.1（单谱/多谱）、Function 4.2（影像立方体）；输出每种参考材料的 fit 影像 + 综合材料图。

## 4. 参考文献条目

- Kokaly, R.F., 2011. PRISM: Processing Routines in IDL for Spectroscopic Measurements (Installation Manual and User's Guide, Version 1.0). U.S. Geological Survey Open-File Report 2011-1155.（页数按目录约 430 p.，正式条目待核）
- 与 IGARSS 会议论文区分：Kokaly, R.F., King, T.V.V., Hoefen, T.M., 2011. Mapping the distribution of materials in hyperspectral data using the USGS Material Identification and Characterization Algorithm (MICA). IGARSS 2011, pp. 1569–1572.（归档：`docs/kokaly2011.md`）——**两篇同为 2011，正文引用须用 Kokaly (2011) vs Kokaly et al. (2011) 区分**。

## 5. 对 CRAMM 技术文档的直接供给

| 文档位置 | 本档案供给的事实 |
|---|---|
| Introduction P3（gap） | 未提供实现源代码的编译 `.sav` 字节码，以及商业 ENVI/IDL 许可环境的官方出处 |
| Section 2 P3（传感器绑定） | Function 2.8/2.9 卷积链 = "换传感器必重建库"的官方功能证据 |
| benchmark.md（PRISM 计时 protocol） | 官方环境基线：PRISM v1.0 编译/要求 ENVI 4.8 + IDL 8.0（2011 年代环境）；作者 25 min 实测所用的现代 ENVI 版本须另行声明 |
