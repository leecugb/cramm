# 图:RELAB calcite 族误判根因三面板(供 §4.4 / 补充材料)
#
# A. taxonomy 构成 × 结局:105 条 "calcite 族" 池按真实物种拆分,
#    结局 = 命中 / 无触发(拒识) / 误判 dolomite / 误判其他
# B. fit 签名:真方解石命中 vs 菱镁矿→dolomite 的 fit 分布(中位 0.99 vs 0.69)
# C. 2.3 µm 谱形证据(局部连续统去除,叠置):
#    真方解石命中 / c1hm01(唯一真混淆) / 菱镁矿→dolomite / 菱镁矿拒识 /
#    合成镁方解石拒识;竖线 = cal_center 七锚点中的三个(magnesite 2311.3 /
#    dolomite 2321.2 / calcite 2339.4 nm,§5.3)
#
# 产物: docs/fig_calcite_miss_cause.{png,pdf}
# 运行: python3 docs/_fig_calcite_miss.py

import csv
from collections import Counter
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
RELAB_ROOT = '/media/lee/共享14/backup/relab'
OUT_PNG = REPO / 'docs' / 'fig_calcite_miss_cause.png'
OUT_PDF = REPO / 'docs' / 'fig_calcite_miss_cause.pdf'

# C 面板代表谱:(spec_id, 标签, 颜色)
PANEL_C = [
    ('c1xt10',  'true calcite → calcite_abundant (fit 0.997)', 'tab:blue'),
    ('c1hm01',  'true calcite HYD-BLT-1a → dolomite_abundant (0.973)', 'tab:red'),
    ('cbcc06',  'magnesite → dolomite (0.773)', 'tab:orange'),
    ('cabe256', 'magnesite → no rule fires', '0.55'),
    ('c1jb825', 'synthetic Mg-calcite → no rule fires', 'tab:green'),
]
# cal_center 锚点(§5.3, nm)
ANCHORS = [(2311.3, 'magnesite'), (2321.2, 'dolomite'), (2339.4, 'calcite')]


def is_true_calcite(name):
    n = name.lower()
    for bad in ['magnesite', 'brumado', 'rhodochrosite', 'gaspeite',
                'manganocalcite', 'hydrocalcite', 'smithsonite']:
        if bad in n:
            return False
    return 'calcite' in n


def species_group(name):
    n = name.lower()
    if is_true_calcite(name):
        return 'true calcite'
    if 'hydromagnesite' in n:
        return 'hydromagnesite'
    if 'magnesite' in n or 'brumado' in n:
        return 'magnesite'
    return 'other group members'


def outcome(r):
    if r['top1_hit'] == '1':
        return 'hit'
    if r['winner_kind'] == 'no_fire':
        return 'no rule fires'
    if 'dolomite' in r['top1_rule']:
        return '→ dolomite'
    return '→ other rules'


def local_cr(w, y, lo=2.16, hi=2.43):
    """局部线性连续统去除(端点取 calcite 规则诊断特征的连续统区间:
    左 2.178–2.208,右 2.377–2.406 µm,rf.json)→ (w_win, depth=1-CR)"""
    m = (w >= lo) & (w <= hi)
    w, y = w[m], y[m]
    e1 = (w >= 2.178) & (w <= 2.208)
    e2 = (w >= 2.377) & (w <= 2.406)
    c1, c2 = np.mean(y[e1]), np.mean(y[e2])
    x1, x2 = np.mean(w[e1]), np.mean(w[e2])
    cont = c1 + (c2 - c1) * (w - x1) / (x2 - x1)
    return w, 1.0 - y / cont


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from relablib import RelabLibrary

    bench = list(csv.DictReader(open(REPO / 'docs' / 'crosslib_benchmark.csv',
                                     encoding='utf-8-sig')))
    cal = [r for r in bench if r['leg'] == 'RELAB' and r['family'] == 'calcite']

    fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.2),
                             gridspec_kw={'width_ratios': [1.05, 0.9, 1.35]})

    # ---------------- A. taxonomy × outcome ----------------
    ax = axes[0]
    groups = ['true calcite', 'magnesite', 'hydromagnesite', 'other group members']
    outs = ['hit', 'no rule fires', '→ dolomite', '→ other rules']
    colors = {'hit': 'tab:blue', 'no rule fires': '0.75',
              '→ dolomite': 'tab:orange', '→ other rules': 'tab:red'}
    tally = {g: Counter() for g in groups}
    for r in cal:
        tally[species_group(r['name'])][outcome(r)] += 1
    bottoms = np.zeros(len(groups))
    for o in outs:
        vals = np.array([tally[g][o] for g in groups], float)
        ax.barh(range(len(groups)), vals, left=bottoms, color=colors[o],
                label=o, edgecolor='white')
        for i, (v, b) in enumerate(zip(vals, bottoms)):
            if v > 0:
                ax.text(b + v / 2, i, f'{v:.0f}', ha='center', va='center',
                        fontsize=9, color='white' if o == 'hit' else 'black')
        bottoms += vals
    ax.set_yticks(range(len(groups)))
    ax.set_yticklabels([f'{g}\n(n={sum(tally[g].values())})' for g in groups],
                       fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel('spectra')
    ax.set_title('A. RELAB "calcite group" pool (n=105):\ntrue species × engine outcome',
                 fontsize=10)
    ax.legend(fontsize=8, loc='lower right')

    # ---------------- B. fit 签名 ----------------
    ax = axes[1]
    tc_hit = [float(r['top1_fit']) for r in cal
              if r['top1_hit'] == '1' and is_true_calcite(r['name'])]
    mg_dol = [float(r['top1_fit']) for r in cal
              if r['top1_hit'] == '0' and 'dolomite' in r['top1_rule']
              and species_group(r['name']) == 'magnesite']
    rng = np.random.default_rng(7)
    for i, (vals, label, c) in enumerate([
            (tc_hit, f'true calcite hits (n={len(tc_hit)})', 'tab:blue'),
            (mg_dol, f'magnesite → dolomite (n={len(mg_dol)})', 'tab:orange')]):
        ax.boxplot(vals, positions=[i], widths=0.35, showfliers=False,
                   medianprops=dict(color='black'))
        ax.scatter(rng.normal(i, 0.06, len(vals)), vals, s=18, alpha=0.6,
                   color=c, label=label, zorder=3)
    hm = [r for r in cal if r['id'] == 'c1hm01'][0]
    ax.scatter([0], [float(hm['top1_fit'])], s=90, marker='*', color='tab:red',
               zorder=4, label='c1hm01: true calcite →\ndolomite_abundant (0.973)')
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['true calcite\nhits', 'magnesite\n→ dolomite'], fontsize=9)
    ax.set_ylabel('winner fit (r²)')
    ax.set_ylim(0.55, 1.05)
    ax.axhline(np.median(tc_hit), color='tab:blue', ls=':', lw=1)
    ax.axhline(np.median(mg_dol), color='tab:orange', ls=':', lw=1)
    ax.text(1.42, np.median(tc_hit), f'median {np.median(tc_hit):.2f}',
            color='tab:blue', fontsize=8, va='center')
    ax.text(1.42, np.median(mg_dol), f'median {np.median(mg_dol):.2f}',
            color='tab:orange', fontsize=8, va='center')
    ax.set_xlim(-0.6, 2.1)
    ax.set_title('B. Fit signature separates\nrejection-grade from hit-grade', fontsize=10)
    ax.legend(fontsize=8, loc='lower left')

    # ---------------- C. 谱形证据 ----------------
    ax = axes[2]
    rl = RelabLibrary(RELAB_ROOT)
    by_id = {r.spec_id: r for r in rl.records}
    for k, (sid, label, color) in enumerate(PANEL_C):
        sp = rl.load(by_id[sid])
        w = np.asarray(sp.wavelength, float)
        y = np.asarray(sp.reflectance, float)
        ok = np.isfinite(y) & (y > 0)
        ww, d = local_cr(w[ok], y[ok])
        ax.plot(ww * 1000, d + k * 0.16, color=color, lw=1.2, label=label)
        band = (ww >= 2.28) & (ww <= 2.38)          # 带中心搜索限在特征窗内
        ax.plot(ww[band][np.argmax(d[band])] * 1000,
                d[band].max() + k * 0.16, 'v', color=color, ms=5)
    label_kw = {'magnesite': dict(ha='right', dx=-4, dy=0.0),
                'dolomite': dict(ha='center', dx=0, dy=-0.065),
                'calcite': dict(ha='left', dx=4, dy=0.0)}
    for nm, name in ANCHORS:
        kw = label_kw[name]
        ax.axvline(nm, color='k', ls='--', lw=0.8, alpha=0.5)
        ax.text(nm + kw['dx'], -0.075 + kw['dy'], f'{name} {nm:.0f} nm',
                ha=kw['ha'], va='top', fontsize=8)
    ax.set_ylim(-0.19, len(PANEL_C) * 0.16 + 0.06)
    ax.set_xlabel('wavelength (nm)')
    ax.set_ylabel('local continuum-removed depth + offset')
    ax.set_yticks([])
    ax.set_xlim(2200, 2450)
    ax.set_title('C. 2.3 µm band shapes (local CR, stacked):\nanchors from the §5.3 cal_center sequence',
                 fontsize=10)
    ax.legend(fontsize=8, loc='upper right')

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=300)
    fig.savefig(OUT_PDF)
    print(f'产物: {OUT_PNG.name}, {OUT_PDF.name}')


if __name__ == '__main__':
    main()
