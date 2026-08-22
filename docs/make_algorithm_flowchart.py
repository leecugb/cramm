# -*- coding: utf-8 -*-
"""
CRAMM 算法流程图 · Nature 期刊风格
五层分层架构:输入 -> 预处理 -> 决策规则核心 -> 综合判读 -> 产品输出
后端:Python / matplotlib(nature-figure skill 规范)
导出:SVG + PDF + TIFF(600dpi) + PNG
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, FancyBboxPatch
from matplotlib.lines import Line2D

mpl.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Microsoft YaHei', 'Arial', 'Helvetica', 'DejaVu Sans'],
    'svg.fonttype': 'none',
    'pdf.fonttype': 42,
    'axes.spines.right': False,
    'axes.spines.top': False,
    'axes.unicode_minus': False,
})

# Okabe-Ito 色盲安全色族(与项目既有流程图一致)
L = {
    'a': dict(color='#0072B2', fill='#DCEAF5'),   # 输入层 · 蓝
    'b': dict(color='#E69F00', fill='#FBEACB'),   # 预处理层 · 橙
    'c': dict(color='#009E73', fill='#CBEAE0'),   # 决策规则核心 · 绿(hero)
    'd': dict(color='#CC79A7', fill='#F2DBE7'),   # 综合判读层 · 粉
    'e': dict(color='#7030A0', fill='#EAE1F5'),   # 产品输出层 · 紫
}
TXT = '#1a1a1a'
FLOW = '#333333'   # 主流
SIDE = '#8a8a8a'   # 注入/注释

fig, ax = plt.subplots(figsize=(7.2, 8.6))   # 183 mm 双栏宽
ax.set_xlim(-20, 106)
ax.set_ylim(2, 104)
ax.axis('off')


def box(cx, cy, w, h, text, key, fs=9, bold=False, tc=TXT, lw=1.4, z=2):
    ax.add_patch(Rectangle((cx - w / 2, cy - h / 2), w, h,
                           facecolor=L[key]['fill'], edgecolor=L[key]['color'],
                           linewidth=lw, zorder=z))
    ax.text(cx, cy, text, ha='center', va='center', fontsize=fs, color=tc,
            fontweight='bold' if bold else 'normal', linespacing=1.3, zorder=3)


def layer_label(y, letter, name, en, key):
    ax.text(-2.5, y + 4.6, letter, ha='right', va='center', fontsize=15,
            fontweight='bold', color=L[key]['color'], zorder=3)
    ax.text(-2.5, y, name, ha='right', va='center', fontsize=10.5,
            fontweight='bold', color=TXT, zorder=3)
    ax.text(-2.5, y - 4.6, en, ha='right', va='center', fontsize=7,
            color='#999', style='italic', zorder=3)


def arrow(p1, p2, color=FLOW, lw=2.4, ms=17, ls='-', rad=0.0, z=3):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle='-|>', mutation_scale=ms,
                                 color=color, lw=lw, linestyle=ls, zorder=z,
                                 connectionstyle=f'arc3,rad={rad}',
                                 shrinkA=0, shrinkB=0))


def poly_arrow(pts, color=FLOW, lw=2.0, ms=14, ls='-', z=3):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    if len(pts) > 2:
        ax.add_line(Line2D(xs[:-1], ys[:-1], color=color, lw=lw,
                           linestyle=ls, zorder=z, solid_capstyle='round'))
    ax.add_patch(FancyArrowPatch(pts[-2], pts[-1], arrowstyle='-|>',
                                 mutation_scale=ms, color=color, lw=lw,
                                 linestyle=ls, zorder=z, shrinkA=0, shrinkB=0))


GUT = 2          # 内容区左边界(gutter 右侧)
XC1, XC2, XC3 = 20, 52, 84   # 三列中心
W1 = 29                       # 标准盒宽

# ---------------- a 输入层 ----------------
ya, ha = 94, 12
layer_label(ya, 'a', '输入层', 'Inputs', 'a')
box(XC1, ya, W1, ha, '高光谱反射率立方体\n任意 VNIR–SWIR 传感器\n(内置 EMIT L2A 读取器)', 'a', fs=8.5)
box(XC2, ya, W1, ha, '规则库 rf.json\n77 条决策规则\n黏土·云母·碳酸盐·硫酸盐…', 'a', fs=8.5)
box(XC3, ya, W1, ha, 'USGS splib06b\n参考光谱库', 'a', fs=8.5)

# ---------------- b 预处理层 ----------------
yb, hb = 74, 12
layer_label(yb, 'b', '预处理层', 'Preprocessing', 'b')
box(XC1, yb, W1, hb, '坏波段剔除 · 波段配置\n(w, bp, chanels)\nfloat32 立方体', 'b', fs=8.5)
box(XC2, yb, W1, hb, '参考光谱重采样\n高斯核 → 传感器波段\n(缓存)', 'b', fs=8.5)
box(XC3, yb, W1, hb, '规则编译\n端点/索引/法方程常数 B\n深度因子(两级缓存)', 'b', fs=8.5)

# ---------------- c 决策规则核心层(hero) ----------------
yc, hc = 47, 26
layer_label(yc, 'c', '决策规则\n核心层', 'Decision-rule core', 'c')
# 外框:77 条规则并行
ax.add_patch(FancyBboxPatch((GUT + 1, yc - hc / 2), 100, hc,
                            boxstyle='round,pad=0,rounding_size=2',
                            facecolor='#F2FAF7', edgecolor=L['c']['color'],
                            linewidth=1.8, zorder=1))
ax.text(GUT + 3, yc + hc / 2 - 2.2, '对每条规则(77 条,跨规则并行 · 串行≡并行位级一致)',
        fontsize=8.5, color=L['c']['color'], fontweight='bold', ha='left',
        va='center', zorder=3)
c_steps = [
    ('① 连续统去除\ndiagnostic features', 20),
    ('② 2×2 闭式最小二乘\nfit (r²) · depth', 44),
    ('③ 排除特征过滤\nnot-absorption /\nnot-related', 68),
    ('④ 约束审计\n五层约束 +\nCRAMM 深度比约束', 92),
]
for t, cx in c_steps:
    box(cx, yc - 3, 20, 13, t, 'c', fs=8)
for i in range(len(c_steps) - 1):
    arrow((c_steps[i][1] + 10, yc - 3), (c_steps[i + 1][1] - 10, yc - 3),
          color='#4d7a6c', lw=1.5, ms=11)

# ---------------- d 综合判读层 ----------------
yd, hd = 22, 12
layer_label(yd, 'd', '综合判读层', 'Integration', 'd')
box(XC1, yd, W1, hd, '最佳匹配\n逐像素 argmax\nfit × depth', 'd', fs=8.5)
box(XC2, yd, W1, hd, '白云母 2.2 µm 吸收中心\n二次拟合 mus_center', 'd', fs=8.5)
box(XC3, yd, W1, hd, '波长仲裁亚型归属\nabsorption_center_range\nlowAl/medAl/medhighAl/\nFe-rich', 'd', fs=8)

# ---------------- e 产品输出层 ----------------
ye, he = 6.5, 9
layer_label(ye, 'e', '输出层', 'Products', 'e')
box(28, ye, 44, he, '整景:矿物图 · 彩色增强图 · 白云母中心图\n+ 原始浮点数组 → GeoTIFF / npz', 'e', fs=8.5)
box(76, ye, 40, he, '单光谱:Top-N 矿物排序\n+ PDF 诊断报告', 'e', fs=8.5)

# ============ 主数据流(粗箭头) ============
bot_a, top_b = ya - ha / 2, yb + hb / 2
bot_b, top_c = yb - hb / 2, yc + hc / 2
bot_c, top_d = yc - hc / 2, yd + hd / 2
bot_d, top_e = yd - hd / 2, ye + he / 2

arrow((XC1, bot_a), (XC1, top_b), lw=2.8)              # 立方体 → 坏波段剔除
arrow((XC1, bot_b), (XC1, top_c), lw=2.8)              # 预处理立方体 → 规则核心
arrow((XC1, bot_c), (XC1, top_d), lw=2.8)              # 规则核心 → 最佳匹配
arrow((XC1, bot_d), (28, top_e), lw=2.8)               # 最佳匹配 → 整景产品
arrow((XC3, bot_d), (46, top_e), lw=2.0, ms=14)        # 仲裁结果 → 整景产品

# ============ 输入注入(细箭头) ============
poly_arrow([(XC3, bot_a), (XC2 + 6, top_b)], color=SIDE, lw=1.6, ms=12)  # splib06b → 重采样
poly_arrow([(XC2, bot_a), (XC3 - 6, top_b)], color=SIDE, lw=1.6, ms=12)  # rf.json → 规则编译
poly_arrow([(XC2, bot_b), (30, top_c)], color=SIDE, lw=1.6, ms=12)       # 重采样参考 → 规则核心
poly_arrow([(XC3, bot_b), (60, top_c)], color=SIDE, lw=1.6, ms=12)       # 编译规则 → 规则核心

# ============ d 层内(细箭头) ============
arrow((XC1 + W1 / 2, yd), (XC2 - W1 / 2, yd), color='#8a5578', lw=1.5, ms=11)  # 最佳匹配 → 中心拟合
arrow((XC2 + W1 / 2, yd), (XC3 - W1 / 2, yd), color='#8a5578', lw=1.5, ms=11)  # mus_center → 仲裁

# ============ 单光谱支路(右侧,细) ============
poly_arrow([(98, yc - 3), (102, yc - 3), (102, ye), (76 + 20, ye)],
           color=SIDE, lw=1.6, ms=12)
ax.text(104.2, 30, '单光谱模式', fontsize=7.5, color=SIDE, rotation=90,
        ha='center', va='center')

plt.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)

out = os.path.join(os.path.dirname(os.path.abspath(__file__)))
base = os.path.join(out, 'cramm_algorithm_flowchart_nature')
fig.savefig(base + '.svg', bbox_inches='tight', facecolor='white')
print('saved', base + '.svg')
fig.savefig(base + '.pdf', bbox_inches='tight', facecolor='white')
print('saved', base + '.pdf')
fig.savefig(base + '.tiff', dpi=600, bbox_inches='tight', facecolor='white')
print('saved', base + '.tiff')
fig.savefig(base + '.png', dpi=600, bbox_inches='tight', facecolor='white')
print('saved', base + '.png')
