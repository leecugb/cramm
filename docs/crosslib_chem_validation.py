# 跨库基准 · 阶段4 化学验证腿(mus_center / chl_center 产品 vs 实测化学)
#
# 目的:用带实测化学的标样链检验 CRAMM 吸收中心产品的物理一致性——
#   A. 白云母链(USGS splib07,11 样 22 谱):Al₂O₃ 28.03–35.69 wt%
#      vs mus_center(2.2 µm Al-OH 带中心);归档链
#      transfer_chain_validation.csv(fig6 回归 λ=-3.1·Al₂O₃+2308,
#      λ_meas = 2.18–2.50 µm 窗口 3 点二次拟合)
#   B. 绿泥石链(USGS splib07,8 样):Fe# 0.017–0.53 vs chl_center
#      (2.25 µm Fe/Mg-OH 带中心);归档链 chlorite_chem_pos2250.csv
#      (CR 窗口 (2.20,2.30)/有效 (2.24,2.27) 口径)
#   C. RELAB 独立小组(6 样,与 bundled rf77 零同源):
#      绿泥石 4 样(chl_center vs Fe#,化学按重建约定全 Fe 记 Fe²⁺)
#      + 云母组 2 样(CEL101 绿鳞石 / PHL101 金云母,mus_center 探索性)
#
# 与阶段3 不同:本腿不测鉴定准确率,测"产品数值 ↔ 化学"的物理一致性。
# A/B 两链光谱与 bundled 参考同库(部分同材料),定位为工程一致性核验;
# C 组是独立证据(n 小,轶事级)。
#
# 产物:
#   docs/crosslib_chem_validation.csv   逐谱结果
#   docs/crosslib_chem_validation.json  汇总统计
#   docs/crosslib_chem_validation.md    报告
#   docs/crosslib_chem_validation.png   双联散点(化学 vs 产品值)
#
# 运行: python3 docs/crosslib_chem_validation.py

import contextlib
import csv
import io
import json
import sys
import warnings
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np

warnings.filterwarnings('ignore')

REPO = Path(__file__).resolve().parent.parent
# 防呆:脚本方式运行时 sys.path[0]=docs/,`import cramm` 会命中 site-packages
# 里的旧版 pip 包(1.0.2)而非本仓库源码——必须把仓库根插到最前
sys.path.insert(0, str(REPO / "repo" / "src"))
USGS_ROOT = '/media/lee/共享14/backup/usgs_splib07'
RELAB_ROOT = '/media/lee/共享14/backup/relab'
MUS_CHAIN = Path('/media/lee/共享14/backup/gems/results/transfer_chain_validation.csv')
CHL_CHAIN = Path('/media/lee/共享14/backup/gems/results/chlorite_chem_pos2250.csv')
OUT_CSV = REPO / 'docs' / 'crosslib_chem_validation.csv'
OUT_JSON = REPO / 'docs' / 'crosslib_chem_validation.json'
OUT_MD = REPO / 'docs' / 'crosslib_chem_validation.md'
OUT_PNG = REPO / 'docs' / 'crosslib_chem_validation.png'

WL_LO, WL_HI = 0.38, 2.55

# RELAB 独立组: (spec_id, 产品, 说明)
RELAB_POOL = [
    ('c1ch16', 'chl', 'Chamosite CHM102'),
    ('c1ea14', 'chl', 'Clinochlore CLI101'),
    ('c1sr59', 'chl', 'BUR-1340 clinochlore'),
    ('c1sr68', 'chl', 'WAR-1924 chlorite'),
    ('c1ea19a', 'mus', 'Celadonite CEL101'),
    ('c1ea31a', 'mus', 'Phlogopite PHL101'),
]

# 重建约定(2026-08-11 用户定版):全 Fe 视为 Fe²⁺
def fe_number(ox: dict) -> float | None:
    n_fe = 2 * ox.get('Fe2O3', 0.0) / 159.688 + ox.get('FeO', 0.0) / 71.844
    n_mg = ox.get('MgO', 0.0) / 40.304
    return n_fe / (n_fe + n_mg) if (n_fe + n_mg) > 0 else None


def prep(wl, ref):
    win = (wl >= WL_LO) & (wl <= WL_HI)
    w = wl[win].astype('float64')
    y = ref[win].astype('float64').copy()
    ok = np.isfinite(y) & (y > 0) & (y < 10)
    chanels = np.flatnonzero(ok)
    if len(chanels) < 50:
        return None
    y[~ok] = 0.0
    bp = np.maximum(np.abs(np.gradient(w)), 1e-4)
    return w, y, bp, chanels


def centers(eng, w, y, bp, chanels):
    """单谱 → (mus_center_nm, chl_center_nm, cal_center_nm, fd);
    无触发为 0。classify 的 print 警告在此吞掉。"""
    cube = y.reshape(1, 1, -1)
    with contextlib.redirect_stdout(io.StringIO()):
        out = eng.spectrum_analysis(cube, w[chanels], w, bp, chanels,
                                    raw=True, n_workers=1)
    mus, chl, cal, fd = out[5].ravel()[0], out[6].ravel()[0], \
        out[7].ravel()[0], out[8].ravel()[0]
    return float(mus) * 1000, float(chl) * 1000, float(cal) * 1000, float(fd)


def linreg(x, y):
    """→ (slope, intercept, r_pearson, rho_spearman, n)"""
    from scipy import stats
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(x) < 3:
        return None
    lr = stats.linregress(x, y)
    rho = stats.spearmanr(x, y).statistic
    return lr.slope, lr.intercept, lr.rvalue, rho, len(x)


def main() -> int:
    import cramm
    from cramm.mica_engine import MicaEngine
    from usgs_splib import USGSLibrary
    from relablib import RelabLibrary
    print(f'引擎: {cramm.__file__}')
    eng = MicaEngine()
    usgs = USGSLibrary(USGS_ROOT)
    relab = RelabLibrary(RELAB_ROOT)
    usgs_by_stem = {r.location.stem: r for r in usgs.records}
    relab_by_id = {r.spec_id: r for r in relab.records}

    rows = []

    # ====================================== A. 白云母链(USGS splib07)
    print('== A. 白云母链 ==')
    with MUS_CHAIN.open(encoding='utf-8-sig') as f:
        mus_chain = list(csv.DictReader(f))
    n_miss = 0
    for c in mus_chain:
        stem = 'splib07a_' + c['record']
        rec = usgs_by_stem.get(stem)
        if rec is None:
            print(f'  [未找到] {stem}')
            n_miss += 1
            continue
        sp = usgs.load(rec)
        g = prep(sp.wavelength, sp.reflectance)
        if g is None:
            print(f'  [网格不合格] {stem}')
            n_miss += 1
            continue
        mus_c, chl_c, cal_c, fd = centers(eng, *g)
        rows.append({
            'pool': 'A_muscovite_USGS', 'record': c['record'],
            'sample': c['sample'], 'library': 'splib07',
            'chem_key': 'Al2O3_wt', 'chem_val': c['Al2O3_wt'],
            'chem2_key': 'X_FeMg', 'chem2_val': c['X_FeMg'],
            'mus_center_nm': f'{mus_c:.2f}', 'chl_center_nm': f'{chl_c:.2f}',
            'cal_center_nm': f'{cal_c:.2f}', 'fd': f'{fd:.4f}',
            'archived_lambda_nm': c['lambda_meas_nm'],
            'product_fired': int(mus_c > 0),
        })
    print(f'  {sum(1 for r in rows if r["pool"].startswith("A_"))}/{len(mus_chain)} 谱完成'
          f'(缺 {n_miss})')

    # ====================================== B. 绿泥石链(USGS splib07)
    print('== B. 绿泥石链 ==')
    with CHL_CHAIN.open(encoding='utf-8-sig') as f:
        chl_chain = list(csv.DictReader(f))
    for c in chl_chain:
        tok = c['sample']
        # 一样品多传感器记录全收(与归档链 raw_n>1 的口径一致)
        recs = [r for s, r in usgs_by_stem.items()
                if tok.lower() in s.lower() and r.category == 'Minerals']
        if not recs:
            print(f'  [未找到] {tok}')
            continue
        for rec in recs:
            sp = usgs.load(rec)
            g = prep(sp.wavelength, sp.reflectance)
            if g is None:
                continue
            mus_c, chl_c, cal_c, fd = centers(eng, *g)
            rows.append({
                'pool': 'B_chlorite_USGS', 'record': rec.location.stem,
                'sample': tok, 'library': 'splib07',
                'chem_key': 'Fe_frac', 'chem_val': c['Fe_frac'],
                'chem2_key': 'Al2O3_wt', 'chem2_val': c['Al2O3'],
                'mus_center_nm': f'{mus_c:.2f}', 'chl_center_nm': f'{chl_c:.2f}',
                'cal_center_nm': f'{cal_c:.2f}', 'fd': f'{fd:.4f}',
                'archived_lambda_nm': c['CR_mean'],
                'product_fired': int(chl_c > 0),
            })
        print(f'  {tok}: {len(recs)} 谱')

    # ====================================== C. RELAB 独立小组
    print('== C. RELAB 独立组 ==')
    for spec_id, prod, label in RELAB_POOL:
        rec = relab_by_id.get(spec_id)
        if rec is None:
            print(f'  [未找到] {spec_id}')
            continue
        chem = relab.chemistry_rows(rec)
        ox = chem[0]['oxides'] if chem else {}
        sp = relab.load(rec)
        g = prep(sp.wavelength, sp.reflectance)
        if g is None:
            continue
        mus_c, chl_c, cal_c, fd = centers(eng, *g)
        fe = fe_number(ox)
        al = ox.get('Al2O3')
        rows.append({
            'pool': f'C_RELAB_{"chlorite" if prod == "chl" else "mica"}',
            'record': spec_id, 'sample': label, 'library': 'RELAB',
            'chem_key': 'Fe_frac' if prod == 'chl' else 'Al2O3_wt',
            'chem_val': f'{fe:.4f}' if (prod == 'chl' and fe is not None)
                        else (f'{al}' if al else ''),
            'chem2_key': 'Al2O3_wt' if prod == 'chl' else '',
            'chem2_val': f'{al}' if (prod == 'chl' and al) else '',
            'mus_center_nm': f'{mus_c:.2f}', 'chl_center_nm': f'{chl_c:.2f}',
            'cal_center_nm': f'{cal_c:.2f}', 'fd': f'{fd:.4f}',
            'archived_lambda_nm': '',
            'product_fired': int((chl_c if prod == 'chl' else mus_c) > 0),
        })
        print(f'  {spec_id} {label}: mus={mus_c:.1f} chl={chl_c:.1f} '
              f'Fe#={fe if fe is None else round(fe, 3)}')

    # ====================================== 统计
    with OUT_CSV.open('w', newline='', encoding='utf-8-sig') as f:
        wcsv = csv.DictWriter(f, fieldnames=list(rows[0]))
        wcsv.writeheader()
        wcsv.writerows(rows)

    def pool_stats(pool, center_key):
        pr = [r for r in rows if r['pool'] == pool]
        fired = [r for r in pr if float(r[center_key]) > 0]
        x = [float(r['chem_val']) for r in fired]
        y = [float(r[center_key]) for r in fired]
        reg = linreg(x, y)
        arch = [(float(r['archived_lambda_nm']), float(r[center_key]))
                for r in fired if r['archived_lambda_nm']]
        rmse = float(np.sqrt(np.mean([(a - b) ** 2 for a, b in arch]))) if arch else None
        return {'n_spectra': len(pr), 'n_fired': len(fired),
                'regression': None if reg is None else {
                    'slope': round(reg[0], 4), 'intercept': round(reg[1], 3),
                    'r_pearson': round(reg[2], 4), 'rho_spearman': round(reg[3], 4),
                    'n': reg[4]},
                'rmse_vs_archived_nm': None if rmse is None else round(rmse, 3),
                'samples': sorted({r['sample'] for r in pr})}

    stats = {
        'date': str(date.today()),
        'engine': cramm.__file__,
        'pools': {
            'A_muscovite_USGS': pool_stats('A_muscovite_USGS', 'mus_center_nm'),
            'B_chlorite_USGS': pool_stats('B_chlorite_USGS', 'chl_center_nm'),
            'C_RELAB_chlorite': pool_stats('C_RELAB_chlorite', 'chl_center_nm'),
            'C_RELAB_mica': pool_stats('C_RELAB_mica', 'mus_center_nm'),
        },
    }
    OUT_JSON.write_text(json.dumps(stats, ensure_ascii=False, indent=2),
                        encoding='utf-8')

    # ====================================== 图
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))

    ax = axes[0]
    pa = [r for r in rows if r['pool'] == 'A_muscovite_USGS' and float(r['mus_center_nm']) > 0]
    xa = [float(r['chem_val']) for r in pa]
    ya = [float(r['mus_center_nm']) for r in pa]
    ax.scatter(xa, ya, c='tab:red', label='CRAMM mus_center', zorder=3)
    arch = [(float(r['chem_val']), float(r['archived_lambda_nm']))
            for r in pa if r['archived_lambda_nm']]
    if arch:
        ax.scatter([a[0] for a in arch], [a[1] for a in arch], c='0.6',
                   marker='x', label='archived λ_meas (3-pt quad)', zorder=2)
    xx = np.linspace(27.5, 36.5, 50)
    ax.plot(xx, -3.1 * xx + 2308, 'k--', lw=1, label='fig6 λ=-3.1·Al₂O₃+2308')
    ax.set_xlabel('Al$_2$O$_3$ (wt%)')
    ax.set_ylabel('2.2 µm band center (nm)')
    ax.set_title('A. Muscovite chain (USGS splib07, engineering consistency)')
    ax.legend(fontsize=8)

    ax = axes[1]
    for pool, color, label in [('B_chlorite_USGS', 'tab:blue', 'USGS chain'),
                               ('C_RELAB_chlorite', 'tab:green', 'RELAB (independent)')]:
        pb = [r for r in rows if r['pool'] == pool and float(r['chl_center_nm']) > 0]
        ax.scatter([float(r['chem_val']) for r in pb],
                   [float(r['chl_center_nm']) for r in pb],
                   c=color, label=label, zorder=3)
    ax.set_xlabel('Fe# = Fe/(Fe+Mg)')
    ax.set_ylabel('2.25 µm band center (nm)')
    ax.set_title('B. Chlorite chain (chl_center vs Fe#)')
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=200)
    print(f'图: {OUT_PNG.name}')

    # ====================================== 报告
    L = []
    A = L.append
    A('# 化学验证腿(mus_center / chl_center vs 实测化学)')
    A('')
    A(f'> 日期:{date.today()} | 脚本:`docs/crosslib_chem_validation.py`(可重复执行) | '
      '测量:`MicaEngine.spectrum_analysis(raw=True)` 逐谱取 mus_center/chl_center(nm)')
    A('')
    A('## 定位')
    A('')
    A('- A/B 两链光谱来自 USGS splib07——与 bundled rf77 参考同库(部分同材料),'
      '定位为**工程一致性核验**:产品代码路径测出的带中心是否与归档链'
      '(独立脚本、不同测量口径)及化学趋势一致。')
    A('- C 组 RELAB 6 样与 bundled 参考零同源(经阶段1 排重审计),'
      '是独立证据,但 n 小,轶事级。')
    A('- 本腿不测鉴定准确率(阶段3 已测);测"产品数值 ↔ 化学"的物理一致性,'
      '即 [[mus_center/chl_center 相图]] 作为参考标尺的经验地基。')
    A('')
    A('## 结果汇总')
    A('')
    A('| 池 | 谱数 | 产品触发 | 回归(化学→带中心) | Pearson r | Spearman ρ | 与归档 λ 的 RMSE (nm) |')
    A('|---|---|---|---|---|---|---|')
    for name, s in stats['pools'].items():
        reg = s['regression']
        if reg is None:
            reg_s, r_s, rho_s = '—', '—', '—'
        else:
            reg_s = f"{reg['slope']} nm/单位, n={reg['n']}"
            r_s = str(reg['r_pearson'])
            rho_s = str(reg['rho_spearman'])
        rmse_s = '—' if s['rmse_vs_archived_nm'] is None else str(s['rmse_vs_archived_nm'])
        A(f"| {name} | {s['n_spectra']} | {s['n_fired']} | {reg_s} | {r_s} | {rho_s} | {rmse_s} |")
    A('')
    A('## 逐谱数据')
    A('')
    A(f'见 `{OUT_CSV.name}`({len(rows)} 行);双联散点 `{OUT_PNG.name}`。')
    A('')
    A('## 备注')
    A('')
    A('- Fe# 约定(沿用 2026-08-11 重建定版):全 Fe 视为 Fe²⁺,'
      'n(Fe)=2·Fe₂O₃/159.688+FeO/71.844,Fe#=n(Fe)/(n(Fe)+n(Mg))。')
    A('- 产品触发率本身是结果:mus_center 仅在像元被判为白云母规则时非零,'
      'chl_center 同理(产品定义,非缺陷)。')
    A('- SMR-14(Prochlorite 结构异常)与 NMNH83369(归档 CR 拖尾假象)'
      '在归档链中为黑名单;本表保留全部测量,读者可按 sample 列剔除复核。')
    OUT_MD.write_text('\n'.join(L) + '\n', encoding='utf-8')
    print(f'产物: {OUT_CSV.name}, {OUT_JSON.name}, {OUT_MD.name}, {OUT_PNG.name}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
