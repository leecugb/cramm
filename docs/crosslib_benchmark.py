# 跨库鉴定基准 · 阶段3 基准评分(ECOSTRESS + RELAB → CRAMM 引擎)
#
# 目的:用两库独立光谱检验 CRAMM 的族级鉴定能力,替代缺位的地面核验
#      (paper §4.4 拟设)。
#   - RELAB 腿:docs/relab_selection.csv(551 谱 / 18 族,R1-R9 遴选,
#     CMS 同材料已排除)
#   - ECOSTRESS 腿:mineral ∩ (vswir|all) 全池(排重审计零同源);
#     名称可唯一归族的进"族内测试池",其余进"族外(OOD)池"——
#     OOD 池只统计 Top-1 规则分布(虚警画像),不计准确率
#
# 评分(族级,亚型不作真值):
#   Top-1 hit  : 头名规则的族集合 ⊇ 真值族
#   Top-5 hit  : 前 5 名规则的族集合之并 ⊇ 真值族
#   混淆矩阵   : 仅统计头名为"纯规则"(单族集合)者
#   混合规则头名:单列统计(真值 ∈ 混合组分集合记 mixture_hit)
#   other 规则  : 植被/水/雪规则命中矿物谱 = 虚警,记 miss
#
# 诊断:族内 Top-1 miss 的谱生成特征诊断 PDF(pdf_path),每腿上限
#      MAX_PDF_PER_LEG 份,存 docs/crosslib_diag/
#
# 产物:
#   docs/crosslib_benchmark.csv   逐谱结果
#   docs/crosslib_benchmark.json  汇总指标
#   docs/crosslib_benchmark.md    报告
#
# 运行: python3 docs/crosslib_benchmark.py
#       (需 cramm / relablib / ecospeclib;数据路径见常量)

import csv
import json
import re
import sys
import time
import warnings
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import numpy as np

warnings.filterwarnings('ignore')

REPO = Path(__file__).resolve().parent.parent
# 防呆:脚本方式运行时 sys.path[0]=docs/,`import cramm` 会命中 site-packages
# 里的旧版 pip 包(1.0.2)而非本仓库源码——必须把仓库根插到最前
sys.path.insert(0, str(REPO / "repo" / "src"))
sys.path.insert(0, str(REPO / 'docs'))
from _relab_stage1_selection import FAMILY_PATTERNS, FAMILY_NEGATIVES  # noqa: E402

RELAB_ROOT = '/media/lee/共享14/backup/relab'
ECO_ROOT = '/media/lee/共享14/backup/ecospeclib-all'
SELECTION_CSV = REPO / 'docs' / 'relab_selection.csv'
OUT_CSV = REPO / 'docs' / 'crosslib_benchmark.csv'
OUT_JSON = REPO / 'docs' / 'crosslib_benchmark.json'
OUT_MD = REPO / 'docs' / 'crosslib_benchmark.md'
DIAG_DIR = REPO / 'docs' / 'crosslib_diag'

WL_LO, WL_HI = 0.38, 2.55      # CRAMM 特征窗口(µm)
COV_LO, COV_HI = 0.50, 2.45    # 有效覆盖要求(µm)
MIN_PTS = 100                  # 窗口内有效点下限
MAX_PDF_PER_LEG = 100
TOP_N = 10

# ------------------------------------------------------- 77 规则 → 族集合
# 纯规则 = 单族集合;混合规则 = 多族集合(组分族);other = 非矿物规则
RULE_FAMILY = {
    # --- 非矿物 ---
    'vegetation_green': {'other'},
    'vegetation_npv_and_green': {'other'},
    'snow_melting': {'other'},
    'snow_slush': {'other'},
    'water': {'other'},
    'water_sediment_high': {'other'},
    'water_sediment_low': {'other'},
    'dry_veg_grass': {'other'},
    'dry_veg_grass_2_3um': {'other'},
    'dry_veg_nongrass': {'other'},
    'dry_veg_nongrass_2_3um': {'other'},
    # --- 云母/伊利石 ---
    'muscovite_lowAl': {'muscovite'},
    'muscovite_medAl': {'muscovite'},
    'muscovite_medhighAl': {'muscovite'},
    'muscovite_Fe-rich': {'muscovite'},
    'illite_imt1': {'illite'},
    'illite_gds4': {'illite'},
    # --- 高岭石族 ---
    'kaolinite_wxl': {'kaolinite'},
    'kaolinite_pxl': {'kaolinite'},
    'kaolinite_or_dickite': {'kaolinite'},
    'kaolinite+clay_mica_or_halloysite': {'kaolinite', 'illite', 'muscovite'},
    # --- 铵长石/明矾石/叶蜡石/黄钾铁矾 ---
    'buddingtonite': {'buddingtonite'},
    'buddingtonite+montmorillonite_mix_intimate': {'buddingtonite', 'smectite'},
    'alunite_K_250C': {'alunite'},
    'alunite_Na_450C': {'alunite'},
    'pyrophyllite': {'pyrophyllite'},
    'pyrophyllite.25+kaolinite.75': {'pyrophyllite', 'kaolinite'},
    'jarosite_Na': {'jarosite'},
    'jarosite_K': {'jarosite'},
    # --- 蒙脱石族 ---
    'montmorillonite_Na': {'smectite'},
    'montmorillonite_Ca': {'smectite'},
    'nontronite': {'smectite'},
    'hectorite': {'smectite'},
    # --- 石膏 ---
    'gypsum': {'gypsum'},
    'gypsum.6+montmorilloniteNa.4': {'gypsum', 'smectite'},
    # --- 绿泥石 ---
    'chlorite_lowFe': {'chlorite'},
    'clinochlore': {'chlorite'},
    'clinochlore_Fe': {'chlorite'},
    'thuringite': {'chlorite'},
    # --- 绿帘石 ---
    'epidote': {'epidote'},
    # --- 层状硅酸盐混合规则 ---
    'pyrophyllite.5+alunite.5_mix_intimate': {'pyrophyllite', 'alunite'},
    'alunite.5+kaolinite.5': {'alunite', 'kaolinite'},
    'alunite.25+kaolinite.75': {'alunite', 'kaolinite'},
    'kaolinite.5+muscoviteMedAl.5': {'kaolinite', 'muscovite'},
    'kaolinite.5+muscoviteMedhighAl.5': {'kaolinite', 'muscovite'},
    'kaolinite+muscovite_mix_intimate': {'kaolinite', 'muscovite'},
    'kaolinite+smectite_mix_intimate': {'kaolinite', 'smectite'},
    'jarosite+muscovite_mix_intimate': {'jarosite', 'muscovite'},
    'chlorite+muscovite_mix_intimate': {'chlorite', 'muscovite'},
    'clinochlore_Fe.3+muscovite.7': {'chlorite', 'muscovite'},
    # --- 碳酸盐 ---
    'calcite_abundant': {'calcite'},
    'calcite': {'calcite'},
    'dolomite_abundant': {'dolomite'},
    'dolomite': {'dolomite'},
    'calcite.5+dolomite.5': {'calcite', 'dolomite'},
    # Fe 碳酸盐通用规则:菱铁矿为主,铁白云石(ankerite→dolomite 族)亦合法
    'carbonate_Fe_bearing': {'siderite', 'dolomite'},
    'calcite.18+dolomite.22+montmorilloniteNa.6': {'calcite', 'dolomite', 'smectite'},
    'calcite.18+dolomite.22+montmorilloniteCa.6': {'calcite', 'dolomite', 'smectite'},
    'calcite.8+montmorilloniteNa.2_mix_intimate': {'calcite', 'smectite'},
    'calcite.25+montmorilloniteCa.75': {'calcite', 'smectite'},
    'calcite.25+montmorilloniteNa.75': {'calcite', 'smectite'},
    'calcite.5+muscoviteMedHiAl.5': {'calcite', 'muscovite'},
    'calcite.5+muscoviteMedAl.5': {'calcite', 'muscovite'},
    'calcite.3+muscoviteLowAl.7': {'calcite', 'muscovite'},
    'dolomite.5+montmorilloniteNa.5': {'dolomite', 'smectite'},
    'dolomite.5+montmorilloniteCa.5': {'dolomite', 'smectite'},
    'kaolinite.2+calcite.8_mix_intimate': {'kaolinite', 'calcite'},
    # --- 硅质 ---
    'chalcedony': {'chalcedony'},
    'hydrated_silica': {'opal'},
    # --- 链状/层状镁硅酸盐 ---
    'tremolite_or_talc': {'tremolite', 'talc'},
    'talc_or_tremolite': {'tremolite', 'talc'},
    'serpentine_antigorite_or_calcite+dolomite': {'serpentine', 'calcite', 'dolomite'},
    'serpentine_chrysotile': {'serpentine'},
    'serpentine_antigorite_withironfeat': {'serpentine'},
    'serpentine_chrysotile_withsecondfeat': {'serpentine'},
    'serpentine_antigorite_withsecondfeat': {'serpentine'},
    # --- 黄玉 ---
    'topaz': {'topaz'},
}

FAMILY_RX = [(f, re.compile(p, re.I)) for f, p in FAMILY_PATTERNS]
KNOWN_FAMILIES = {f for f, _ in FAMILY_PATTERNS}


def eco_family(name: str):
    """ECOSTRESS 名称 → 唯一族;零命中/跨族冲突返回 None。"""
    hits = set()
    for f, rx in FAMILY_RX:
        if rx.search(name or ''):
            neg = FAMILY_NEGATIVES.get(f)
            if neg and neg.search(name or ''):
                continue
            hits.add(f)
    return next(iter(hits)) if len(hits) == 1 else None


def winner_kind(fams: set) -> str:
    if fams == {'other'}:
        return 'other'
    return 'pure' if len(fams) == 1 else 'mixture'


def prep_grid(wl_raw, ref):
    """库谱 → CRAMM 契约。w/bp 保留窗口内全部点,chanels 指向有效点
    (同仪器网格内容一致 → 编译缓存命中)。"""
    win = (wl_raw >= WL_LO) & (wl_raw <= WL_HI)
    idx = np.flatnonzero(win)
    if len(idx) < MIN_PTS:
        return None
    w = wl_raw[win].astype('float64')
    y = ref[win].astype('float64')
    ok = np.isfinite(y) & (y > 0)
    chanels = np.flatnonzero(ok)
    if len(chanels) < MIN_PTS:
        return None
    if w[chanels[0]] > COV_LO or w[chanels[-1]] < COV_HI:
        return None
    bp = np.abs(np.gradient(w))
    bp = np.maximum(bp, 1e-4)
    return w, y, bp, chanels


def classify_one(eng, w, y, bp, chanels, pdf_path=None):
    wl = w[chanels]
    spec = y[chanels].reshape(1, -1)
    return eng.classify_spectrum(spec, wl, w, bp, chanels, top_n=TOP_N,
                                 pdf_path=pdf_path)


def score(results, truth):
    """→ (top1_hit, top5_hit, kind, top1_rule, top1_fit, top1_fams)"""
    if not results:
        return False, False, 'no_fire', '', 0.0, ''
    top = results[0]
    fams = RULE_FAMILY[top['name']]
    kind = winner_kind(fams)
    hit1 = truth in fams
    hit5 = any(truth in RULE_FAMILY[r['name']] for r in results[:5])
    return hit1, hit5, kind, top['name'], top['fit'], ';'.join(sorted(fams))


def main() -> int:
    import cramm
    from cramm.mica_engine import MicaEngine
    print(f'引擎: {cramm.__file__}')
    eng = MicaEngine()
    n_rules = len(eng.rf) if hasattr(eng, 'rf') else len(RULE_FAMILY)
    assert set(RULE_FAMILY) == set(json.loads(
        (REPO / 'repo' / 'src' / 'cramm' / 'data' / 'rf.json').read_text())['rf']), \
        'RULE_FAMILY 与 rf.json 的 77 规则不一致'
    DIAG_DIR.mkdir(exist_ok=True)

    rows = []            # 逐谱结果
    legs = {}            # leg -> 聚合
    t0 = time.time()

    def fresh_leg():
        return {'n': 0, 'pool': 'in-family', 'no_fire': 0,
                'top1': 0, 'top5': 0, 'kind': Counter(),
                'mixture_hit': 0, 'mixture_miss': 0,
                'per_family': defaultdict(lambda: [0, 0, 0]),  # fam -> [n, top1, top5]
                'confusion': Counter(),       # (truth, pred) 纯规则头名
                'specimens': defaultdict(list)}  # specimen -> [hit,...]

    # ================================================== RELAB 腿
    print('== RELAB 腿 ==')
    from relablib import RelabLibrary
    rl = RelabLibrary(RELAB_ROOT)
    by_id = {r.spec_id: r for r in rl.records}
    sel = list(csv.DictReader(SELECTION_CSV.open(encoding='utf-8-sig')))
    leg = fresh_leg()
    n_pdf = 0
    for i, s in enumerate(sel):
        rec = by_id[s['spec_id']]
        sp = rl.load(rec)
        g = prep_grid(sp.wavelength, sp.reflectance)
        if g is None:
            print(f'  [跳过-网格] {s["spec_id"]}')
            continue
        w, y, bp, chanels = g
        truth = s['family']
        # 口径修正(2026-09-28):calcite 超族里无 CRAMM 规则覆盖的碳酸盐
        # (magnesite/smithsonite/hydromagnesite/…;siderite 已有独立族)
        # 剥离到 carbonate-other 单列,避免超族口径把引擎的诚实
        # "无触发/判最近规则"压进 calcite Top-1。引擎规则库不变。
        if truth == 'calcite' and re.search(
                r'magnesite|smithsonite|hydromagnesite|gaspeite|hydrocalcite'
                r'|monohydrocalcite|manganocalcite|zincite', s['name'], re.I):
            truth = 'carbonate-other'
        res = classify_one(eng, w, y, bp, chanels)
        hit1, hit5, kind, r1, fit1, fams1 = score(res, truth)
        pdf = ''
        if not hit1 and res and n_pdf < MAX_PDF_PER_LEG:
            pdf_path = DIAG_DIR / f'relab_{s["spec_id"]}.pdf'
            classify_one(eng, w, y, bp, chanels, pdf_path=str(pdf_path))
            if pdf_path.exists():
                pdf = pdf_path.name
                n_pdf += 1
        leg['n'] += 1
        leg['top1'] += hit1
        leg['top5'] += hit5
        leg['kind'][kind] += 1
        if kind == 'no_fire':
            leg['no_fire'] += 1
        elif kind == 'mixture':
            leg['mixture_hit' if hit1 else 'mixture_miss'] += 1
        elif kind == 'pure':
            leg['confusion'][(truth, fams1)] += 1
        pf = leg['per_family'][truth]
        pf[0] += 1; pf[1] += hit1; pf[2] += hit5
        leg['specimens'][s['specimen_id']].append(bool(hit1))
        rows.append({'leg': 'RELAB', 'id': s['spec_id'],
                     'specimen': s['specimen_id'], 'name': s['name'],
                     'family': truth, 'truth_source': s['truth_source'],
                     'pool': 'in-family',
                     'top1_rule': r1, 'top1_fit': f'{fit1:.4f}',
                     'top1_families': fams1, 'winner_kind': kind,
                     'top1_hit': int(hit1), 'top5_hit': int(hit5),
                     'top5_rules': ';'.join(r['name'] for r in res[:5]),
                     'diag_pdf': pdf})
        if (i + 1) % 50 == 0:
            print(f'  {i+1}/{len(sel)}  用时 {time.time()-t0:.0f}s')
    legs['RELAB'] = leg
    print(f'  RELAB 完成 {leg["n"]} 谱,Top-1 {leg["top1"]/leg["n"]:.3f},'
          f'诊断 PDF {n_pdf} 份')

    # ================================================== ECOSTRESS 腿
    print('== ECOSTRESS 腿 ==')
    from ecospeclib import EcoLibrary
    el = EcoLibrary(ECO_ROOT)
    pool = [r for r in el.records
            if r.category == 'mineral' and r.wrange in ('vswir', 'all')]
    leg_in = fresh_leg()
    ood_rules = Counter()
    n_ood = n_skip = n_pdf = n_ood_nofire = 0
    for i, rec in enumerate(pool):
        sp = el.load(rec)
        g = prep_grid(sp.wavelength, sp.reflectance)
        if g is None:
            n_skip += 1
            continue
        w, y, bp, chanels = g
        truth = eco_family(rec.name)
        res = classify_one(eng, w, y, bp, chanels)
        sid = Path(rec.location).stem if rec.location else rec.name
        if truth is None:                       # OOD 池:只统计虚警画像
            n_ood += 1
            if res:
                ood_rules[res[0]['name']] += 1
            else:
                n_ood_nofire += 1
            rows.append({'leg': 'ECOSTRESS', 'id': sid, 'specimen': rec.sample_id or '',
                         'name': rec.name, 'family': '', 'truth_source': '',
                         'pool': 'ood',
                         'top1_rule': res[0]['name'] if res else '',
                         'top1_fit': f'{res[0]["fit"]:.4f}' if res else '0',
                         'top1_families': ';'.join(sorted(RULE_FAMILY[res[0]['name']])) if res else '',
                         'winner_kind': winner_kind(RULE_FAMILY[res[0]['name']]) if res else 'no_fire',
                         'top1_hit': '', 'top5_hit': '',
                         'top5_rules': ';'.join(r['name'] for r in res[:5]),
                         'diag_pdf': ''})
            continue
        hit1, hit5, kind, r1, fit1, fams1 = score(res, truth)
        pdf = ''
        if not hit1 and res and n_pdf < MAX_PDF_PER_LEG:
            pdf_path = DIAG_DIR / f'eco_{sid}.pdf'
            classify_one(eng, w, y, bp, chanels, pdf_path=str(pdf_path))
            if pdf_path.exists():
                pdf = pdf_path.name
                n_pdf += 1
        leg_in['n'] += 1
        leg_in['top1'] += hit1
        leg_in['top5'] += hit5
        leg_in['kind'][kind] += 1
        if kind == 'no_fire':
            leg_in['no_fire'] += 1
        elif kind == 'mixture':
            leg_in['mixture_hit' if hit1 else 'mixture_miss'] += 1
        elif kind == 'pure':
            leg_in['confusion'][(truth, fams1)] += 1
        pf = leg_in['per_family'][truth]
        pf[0] += 1; pf[1] += hit1; pf[2] += hit5
        leg_in['specimens'][rec.sample_id or sid].append(bool(hit1))
        rows.append({'leg': 'ECOSTRESS', 'id': sid,
                     'specimen': rec.sample_id or '', 'name': rec.name,
                     'family': truth, 'truth_source': 'name',
                     'pool': 'in-family',
                     'top1_rule': r1, 'top1_fit': f'{fit1:.4f}',
                     'top1_families': fams1, 'winner_kind': kind,
                     'top1_hit': int(hit1), 'top5_hit': int(hit5),
                     'top5_rules': ';'.join(r['name'] for r in res[:5]),
                     'diag_pdf': pdf})
        if (i + 1) % 100 == 0:
            print(f'  {i+1}/{len(pool)}  用时 {time.time()-t0:.0f}s')
    legs['ECOSTRESS'] = leg_in
    print(f'  ECOSTRESS 完成:族内 {leg_in["n"]} 谱(Top-1 '
          f'{leg_in["top1"]/max(leg_in["n"],1):.3f}),OOD {n_ood} 谱,'
          f'网格跳过 {n_skip},诊断 PDF {n_pdf} 份')

    # ================================================== 产物
    with OUT_CSV.open('w', newline='', encoding='utf-8-sig') as f:
        wcsv = csv.DictWriter(f, fieldnames=list(rows[0]))
        wcsv.writeheader()
        wcsv.writerows(rows)

    def leg_summary(leg):
        n = max(leg['n'], 1)
        spec_hits = [np.mean(v) >= 0.5 for v in leg['specimens'].values()]
        return {
            'n_spectra': leg['n'],
            'top1_acc': round(leg['top1'] / n, 4),
            'top5_acc': round(leg['top5'] / n, 4),
            'winner_kind': dict(leg['kind']),
            'mixture_win': {'hit': leg['mixture_hit'], 'miss': leg['mixture_miss']},
            'per_family': {f: {'n': v[0], 'top1': v[1], 'top5': v[2],
                               'top1_acc': round(v[1] / v[0], 4)}
                           for f, v in sorted(leg['per_family'].items())},
            'confusion': {f'{t}→{p}': c for (t, p), c in
                          sorted(leg['confusion'].items(), key=lambda x: -x[1])},
            'specimen_level': {'n': len(spec_hits),
                               'top1_acc': round(np.mean(spec_hits), 4) if spec_hits else None},
        }

    summary = {
        'date': str(date.today()),
        'engine': cramm.__file__,
        'engine_rules': n_rules,
        'grid_window_um': [WL_LO, WL_HI],
        'coverage_requirement_um': [COV_LO, COV_HI],
        'legs': {name: leg_summary(leg) for name, leg in legs.items()},
        'ecostress_ood': {'n': n_ood, 'grid_skipped': n_skip,
                          'no_fire': n_ood_nofire,
                          'top1_rule_counts': dict(ood_rules.most_common())},
    }
    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                        encoding='utf-8')

    # ------------------------------------------------- 报告
    L = []
    A = L.append
    A('# 跨库鉴定基准(ECOSTRESS + RELAB → CRAMM)')
    A('')
    A(f'> 日期:{date.today()} | 脚本:`docs/crosslib_benchmark.py`(可重复执行) | '
      f'规则库:rf.json {n_rules} 规则 | RELAB 池:`relab_selection.csv`(R1-R9) | '
      f'ECOSTRESS 池:mineral ∩ (vswir|all),排重审计零同源')
    A('')
    A('## 方法')
    A('')
    A('- 每条库谱滤波至 0.38–2.55 µm 窗口(有效点 ≥100 且覆盖 0.5–2.45 µm),'
      '直接以原生网格送入 `MicaEngine.classify_spectrum`(bp = 局部步长),'
      '参考库按同一网格高斯重采样(引擎编译缓存,同仪器网格只算一次)。')
    A('- **族级评分**:77 条规则手工映射到族集合(纯规则=单族,混合规则=组分族集合,'
      '植被/水/雪=other;映射表存档于脚本 `RULE_FAMILY`)。'
      'Top-1 hit = 头名规则族集合 ⊇ 真值族;Top-5 hit = 前 5 名族集合之并 ⊇ 真值族。')
    A('- 混淆矩阵仅统计头名为纯规则者;混合规则头名单列;'
      'other 规则命中矿物谱记虚警(miss)。')
    A('- ECOSTRESS 名称无法唯一归族的记录进 OOD 池,只统计 Top-1 规则分布(虚警画像)。')
    A('- 族内 Top-1 miss 生成特征诊断 PDF(`crosslib_diag/`,每腿上限 '
      f'{MAX_PDF_PER_LEG} 份)。')
    A('')
    A('## 总体结果')
    A('')
    A('| 腿 | 族内光谱 | Top-1 | Top-5 | 标本级 Top-1 | 头名:纯/混合/other/无触发 |')
    A('|---|---|---|---|---|---|')
    for name, leg in legs.items():
        s = summary['legs'][name]
        k = leg['kind']
        A(f"| {name} | {s['n_spectra']} | {s['top1_acc']:.3f} | {s['top5_acc']:.3f} | "
          f"{s['specimen_level']['top1_acc']:.3f} ({s['specimen_level']['n']} 标本) | "
          f"{k.get('pure',0)} / {k.get('mixture',0)} / {k.get('other',0)} / {k.get('no_fire',0)} |")
    A('')
    A(f'- 混合规则头名:RELAB 命中 {legs["RELAB"]["mixture_hit"]}/'
      f'{legs["RELAB"]["mixture_hit"]+legs["RELAB"]["mixture_miss"]},'
      f'ECOSTRESS 命中 {legs["ECOSTRESS"]["mixture_hit"]}/'
      f'{legs["ECOSTRESS"]["mixture_hit"]+legs["ECOSTRESS"]["mixture_miss"]}'
      '(真值 ∈ 混合组分集合,判 hit——库谱本身是单矿物,混合规则头名提示'
      '该矿物与混合参照谱形相似,应视为**弱鉴定**)。')
    A('')
    for name, leg in legs.items():
        A(f'## {name} 腿 · 分族结果')
        A('')
        A('| 族 | n | Top-1 | Top-1 acc | Top-5 acc |')
        A('|---|---|---|---|---|')
        for f, v in sorted(leg['per_family'].items(),
                           key=lambda x: -x[1][0]):
            A(f'| {f} | {v[0]} | {v[1]} | {v[1]/v[0]:.3f} | {v[2]/v[0]:.3f} |')
        A('')
        A(f'### {name} 混淆(纯规则头名)')
        A('')
        A('| 真值 → 预测族 | 次数 |')
        A('|---|---|')
        for (t, p), c in sorted(leg['confusion'].items(), key=lambda x: -x[1]):
            mark = '' if t == p else ' ✗'
            A(f'| {t} → {p} | {c}{mark} |')
        A('')
    A('## ECOSTRESS OOD 池(族外虚警画像)')
    A('')
    A(f'- OOD 光谱 {n_ood} 条(网格不合格跳过 {n_skip} 条),'
      f'其中 **{n_ood_nofire} 条无任何规则触发**(引擎事实拒识,'
      f'占 {n_ood_nofire/max(n_ood,1):.1%})。'
      '其余矿物的 Top-1 规则分布如下,用于评估误吸收风险。')
    A('')
    A('| Top-1 规则 | 次数 |')
    A('|---|---|')
    for r, c in ood_rules.most_common():
        A(f'| {r} | {c} |')
    A('')
    A('## 备注')
    A('')
    A('- 两腿的族真值粒度均为族;RELAB 真值来源 subtype>name>group'
      '(见 `relab_selection.md`),ECOSTRESS 为名称正则唯一命中。')
    A('- `carbonate_Fe_bearing` 映射为 {siderite, dolomite}:Fe 碳酸盐通用规则,'
      '菱铁矿与铁白云石(ankerite→dolomite 族)均为合法命中。')
    A('- `hydrated_silica` 映射为 {opal}(水合二氧化硅);'
      '`tremolite_or_talc`/`talc_or_tremolite` 为 {tremolite, talc} 双族规则。')
    A('- 诊断 PDF 的文件名对应 `crosslib_benchmark.csv` 的 `diag_pdf` 列;'
      '无规则触发(no_fire)的 miss 没有特征可绘,不生成 PDF。')
    OUT_MD.write_text('\n'.join(L) + '\n', encoding='utf-8')
    print(f'产物: {OUT_CSV.name}, {OUT_JSON.name}, {OUT_MD.name}, '
          f'{DIAG_DIR.name}/ ({len(list(DIAG_DIR.glob("*.pdf")))} PDF)')
    print(f'总用时 {time.time()-t0:.0f}s')
    return 0


if __name__ == '__main__':
    sys.exit(main())
