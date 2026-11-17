# 图:4 条真方解石残差(Top-1 未命中)的逐谱审计——结论:引擎判别全部无误
#
# A. 带中心 × 带深散点:42 条真方解石命中 vs 4 条残差
#    - 阴影 = rf.json 的 calcite [2334,2350] / dolomite [2308,2328] 中心窗
#    - 横虚线 = 规则 min_weighted_depth = 0.02(深度门)
#    → c1hm01 = 带在白云石位置(2320 nm,depth 0.48),判 dolomite_abundant 无误;
#      Mg-calcite ×3 = 评分窗内无带(depth ≤0.003),拒识无误
# B. CR 光谱对照(基线=1,吸收向下;参考谱取自 bundled rf77 1nm 包):
#    4 条残差全部上画,c1hm01 跟随白云石参考,镁方解石组平贴基线
#
# 产物: docs/fig_calcite_true4_cause.{png,pdf}
# 运行: python3 docs/_fig_calcite4_miss.py

import csv
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
RELAB_ROOT = '/media/lee/共享14/backup/relab'
OUT_PNG = REPO / 'docs' / 'fig_calcite_true4_cause.png'
OUT_PDF = REPO / 'docs' / 'fig_calcite_true4_cause.pdf'

CAL_EP = (2.178, 2.208, 2.377, 2.406)   # calcite 规则诊断特征连续统端点(rf.json)
CAL_WIN = (2334, 2350)                   # calcite 中心窗
DOL_WIN = (2308, 2328)                   # dolomite 中心窗
DEPTH_GATE = 0.02                        # min_weighted_depth


def local_cr(w, y, ep=CAL_EP):
    """局部连续统去除 → (w_win, CR = R_O/R_L);端点取 calcite 规则诊断
    特征的连续统区间(左 2.178–2.208,右 2.377–2.406 µm,rf.json)"""
    l1, l2, r1, r2 = ep
    m = (w >= l1 - 0.02) & (w <= r2 + 0.02)
    w, y = w[m], y[m]
    e1 = (w >= l1) & (w <= l2)
    e2 = (w >= r1) & (w <= r2)
    cont = np.interp(w, [w[e1].mean(), w[e2].mean()],
                     [y[e1].mean(), y[e2].mean()])
    return w, y / cont


def band_stats(w, cr):
    """评分窗(连续统端点内部 2.208–2.377 µm)内带中心(argmin CR)与带深(1−CR)"""
    band = (w >= 2.208) & (w <= 2.377)
    i = np.argmin(cr[band])
    return w[band][i] * 1000, 1.0 - cr[band][i]


def main():
    import json
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from relablib import RelabLibrary

    rl = RelabLibrary(RELAB_ROOT)
    by_id = {r.spec_id: r for r in rl.records}

    def load_cr(sid):
        sp = rl.load(by_id[sid])
        w = np.asarray(sp.wavelength, float)
        y = np.asarray(sp.reflectance, float)
        ok = np.isfinite(y) & (y > 0)
        return local_cr(w[ok], y[ok])

    bench = list(csv.DictReader(open(REPO / 'docs' / 'crosslib_benchmark.csv',
                                     encoding='utf-8-sig')))
    cal = [r for r in bench if r['leg'] == 'RELAB' and r['family'] == 'calcite']
    hits = [r for r in cal if r['top1_hit'] == '1'
            and r['name'].lower().startswith('calcite')
            or (r['top1_hit'] == '1' and r['id'].startswith('s3'))]
    # 与正文口径一致:真方解石命中 = is_true_calcite 且 hit
    def is_true_calcite(name):
        n = name.lower()
        for bad in ['magnesite', 'brumado', 'rhodochrosite', 'gaspeite',
                    'manganocalcite', 'hydrocalcite', 'smithsonite']:
            if bad in n:
                return False
        return 'calcite' in n
    hits = [r for r in cal if r['top1_hit'] == '1' and is_true_calcite(r['name'])]

    hit_pts = []
    for r in hits:
        w, d = load_cr(r['id'])
        hit_pts.append(band_stats(w, d))
    fail = {}
    for sid in ['c1hm01', 'c1jb825', 'c1jb826', 'c1jb827']:
        w, d = load_cr(sid)
        fail[sid] = (w, d, band_stats(w, d))

    fig, axes = plt.subplots(1, 2, figsize=(15.8, 5.4),
                             gridspec_kw={'width_ratios': [1.15, 1]})

    # ---------------- A. 位置 × 深度 ----------------
    ax = axes[0]
    ax.axvspan(*DOL_WIN, color='tab:orange', alpha=0.12)
    ax.axvspan(*CAL_WIN, color='tab:blue', alpha=0.12)
    ax.axhline(DEPTH_GATE, color='k', ls='--', lw=1)
    ax.text(2294, DEPTH_GATE + 0.008, 'depth gate 0.02\n(min_weighted_depth, rf.json)',
            fontsize=8, ha='left')
    ax.text(2311, 0.27, 'dolomite window', ha='center', va='center',
            rotation=90, fontsize=8.5, color='tab:orange')
    ax.text(2347.5, 0.27, 'calcite window', ha='center', va='center',
            rotation=90, fontsize=8.5, color='tab:blue')
    hp = np.array(hit_pts)
    ax.scatter(hp[:, 0], hp[:, 1], s=26, color='tab:blue', alpha=0.65,
               label=f'true calcite hits (n={len(hp)})', zorder=3)
    w, d, (c, dep) = fail['c1hm01']
    ax.scatter([c], [dep], s=180, marker='*', color='tab:red', zorder=5,
               label=f'c1hm01 (2320 nm, depth 0.48)\n→ dolomite_abundant, fit 0.973')
    for sid in ['c1jb825', 'c1jb826', 'c1jb827']:
        w, d, (c, dep) = fail[sid]
        ax.scatter([c], [dep], s=70, marker='^', color='tab:green', zorder=5)
    ax.annotate('c1jb825 / 826 / 827\nsynthetic Mg-calcites (25/35 °C)\ndepth ≤ 0.003 ≪ gate',
                xy=(2325, 0.001), xytext=(2362, 0.14), fontsize=8,
                color='tab:green', ha='center',
                arrowprops=dict(arrowstyle='->', color='tab:green', lw=0.8))
    ax.scatter([], [], marker='^', color='tab:green',
               label='synthetic Mg-calcites:\nno 2.3 µm band in window')
    ax.set_xlim(2290, 2380)
    ax.set_ylim(-0.03, 0.56)
    ax.set_xlabel('2.3 µm band center (nm, local CR within calcite-rule endpoints)')
    ax.set_ylabel('band depth (1 − CR)')
    ax.set_title('A. The 4 residual true-calcite non-hits on the center × depth plane:\n'
                 'audit finds every engine decision defensible', fontsize=10)
    ax.legend(fontsize=8, loc='center left', bbox_to_anchor=(1.0, 0.5),
              borderaxespad=0, handlelength=1.4)

    # ---------------- B. CR 谱形对照 ----------------
    ax = axes[1]
    z = np.load(REPO / 'cramm' / 'data' / 'rf77_splib07_1nm.npz',
                allow_pickle=True)
    grid, rules, specs = z['grid'], [str(r) for r in z['rule']], z['spectra']

    def ref_cr(rule_name):
        ref = specs[rules.index(rule_name)]
        m = (grid >= CAL_EP[0] - 0.02) & (grid <= CAL_EP[3] + 0.02)
        w, y = grid[m], ref[m]
        e1 = (w >= CAL_EP[0]) & (w <= CAL_EP[1])
        e2 = (w >= CAL_EP[2]) & (w <= CAL_EP[3])
        cont = np.interp(w, [w[e1].mean(), w[e2].mean()],
                         [y[e1].mean(), y[e2].mean()])
        return w, y / cont

    # CR 光谱叠置(基线 ~1,吸收向下;不使用 1−CR 深度谱)
    # 4 条失败谱全部上画:1 条位置驱动(c1hm01)+ 3 条深度驱动(合成镁方解石)
    OFF = 0.5
    curves = [('calcite', 'tab:blue', 'bundled calcite reference', 'ref'),
              ('c1hm01', 'tab:red',
               'c1hm01 → dolomite_abundant (fit 0.973)', 'pix'),
              ('dolomite', 'tab:orange', 'bundled dolomite reference', 'ref'),
              ('c1jb825', 'tab:green', 'c1jb825 Mg-calcite (25 °C)', 'pix'),
              ('c1jb826', 'tab:green', 'c1jb826 Mg-calcite (35 °C)', 'pix'),
              ('c1jb827', 'tab:green', 'c1jb827 Mg-calcite (35 °C)', 'pix')]
    for k, (key, c, lbl, kind) in enumerate(curves):
        if kind == 'ref':
            w, cr = ref_cr(key)
        else:
            w, cr = fail[key][0], fail[key][1]
        ax.plot(w * 1000, cr + k * OFF, color=c, lw=1.4,
                ls='--' if kind == 'ref' else '-', label=lbl)
    base = len(curves) * OFF
    for nm, name, c in [(2339.4, 'calcite', 'tab:blue'),
                        (2321.2, 'dolomite', 'tab:orange')]:
        ax.axvline(nm, color=c, ls=':', lw=1)
    ax.text(2339.4, 0.44, 'calcite 2339', color='tab:blue', fontsize=8, ha='center')
    ax.text(2321.2, 0.36, 'dolomite 2321', color='tab:orange', fontsize=8, ha='center')
    ax.set_ylim(0.3, base + 1.15)
    ax.set_xlim(2160, 2430)
    ax.set_yticks([])
    ax.set_xlabel('wavelength (nm)')
    ax.set_ylabel('continuum-removed spectrum + offset')
    ax.set_title('B. Continuum-removed band shapes vs bundled references\n'
                 '(calcite-rule feature window; baseline = 1, absorption dips down)',
                 fontsize=10)
    ax.legend(fontsize=8, loc='center left', bbox_to_anchor=(1.01, 0.5),
              borderaxespad=0)

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=300, bbox_inches='tight')
    fig.savefig(OUT_PDF, bbox_inches='tight')
    print(f'产物: {OUT_PNG.name}, {OUT_PDF.name}')
    for sid, (w, d, (c, dep)) in fail.items():
        print(f'  {sid}: center {c:.1f} nm, depth {dep:.3f}')


if __name__ == '__main__':
    main()
