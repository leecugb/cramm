# RELAB 跨库基准 · 阶段1 样品遴选(纪律同 splib07_selection)
#
# 目的:为"已知样品身份 → CRAMM 鉴定 → 族级命中率"基准选出 RELAB 单矿物样。
# 遴选规则(全部可机器复执行):
#   R1 material_type == 'Mineral'(单矿物分离样;岩石/混合物/玻璃/有机质出局)
#   R2 geometry == 'Bidirectional'(RELAB 标准双向几何;biconical 出局)
#   R3 波段覆盖 ⊇ [500, 2450] nm(覆盖 CRAMM 全部 SWIR 特征,碳酸盐 2330 含余量)
#   R4 mineral_type 不含 ';'(多矿物归属出局)
#   R5 名称不含混合/衍生标记: % + mixture cation-exchanged heated treated laid on
#   R6 mineral_subtype 不含 '/'(双重归属如 'Siderite / Fe-rich Dolomite' 出局)
#   R7 族归属唯一:mineral_subtype 优先,name 正则兜底,group 仲裁;
#      零命中或跨族冲突出局(冲突留审计轨迹)
#   R8 排除 docs/crosslib_dedup_hits.csv 中 strength=strong 的 spec_id
#      (CMS 粘土标样与 bundled splib07 参考同材料——不独立)
#   R9 同标本株连带排除:R8 命中记录的 specimen 根号(如 JB-JLB-782)
#      的所有派生分样(-A/-B… 后缀)一并排除——同一批材料的改名分样
#      可能不含登录号字符串而漏网(实例:c1jb782a-f "CMS Standard Illite"
#      = IMt-1 的 JB782 株)
#
# 族真值粒度 = 族(白云母/绿泥石/碳酸盐…),亚型不作真值(见排重审计方法段)。
#
# 产物:
#   docs/relab_selection.json   规则 + 各族 spec_id 清单
#   docs/relab_selection.csv    入选记录全字段
#   docs/relab_selection.md     汇总报告(各族规模 / 排除统计 / 缺族清单)
#
# 运行: python3 docs/_relab_stage1_selection.py

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RELAB_ROOT = '/media/lee/共享14/backup/relab'
DEDUP_CSV = REPO / 'docs' / 'crosslib_dedup_hits.csv'
OUT_JSON = REPO / 'docs' / 'relab_selection.json'
OUT_CSV = REPO / 'docs' / 'relab_selection.csv'
OUT_MD = REPO / 'docs' / 'relab_selection.md'

# ------------------------------------------------------------- 族映射(R7)
# (族名, 名称正则) —— 名称正则同时施加于 subtype 字符串
FAMILY_PATTERNS = [
    ('buddingtonite', r'buddington'),
    ('alunite',       r'alunit'),
    ('calcite',       r'\bcalcite'),
    ('chalcedony',    r'chalcedon'),
    ('chlorite',      r'chlorit|clinochlore|ripidolite|chamosite|pennite'),
    ('dolomite',      r'\bdolomite|\bankerite'),
    ('epidote',       r'epidote|zoisite|clinozoisite'),
    ('gypsum',        r'gypsum'),
    ('illite',        r'\billite'),
    ('jarosite',      r'jarosite'),
    ('kaolinite',     r'kaolin|halloysite|dickite|nacrite'),
    ('muscovite',     r'muscovit'),
    ('opal',          r'\bopal'),
    ('pyrophyllite',  r'pyrophyllite'),
    ('serpentine',    r'serpentine|antigorite|chrysotile|lizardite'),
    ('siderite',      r'siderite'),
    ('smectite',      r'montmoril|nontronite|saponite|hectorite|beidellite|smectite'),
    ('talc',          r'\btalc\b'),
    ('topaz',         r'topaz'),
    ('tremolite',     r'tremolite|actinolite'),
]
FAMILY_RX = [(f, re.compile(p, re.I)) for f, p in FAMILY_PATTERNS]

# 族级否定模式:名称/亚型命中即踢出该族(近缘但非同族矿物)
FAMILY_NEGATIVES = {
    'smectite':  re.compile(r'vermiculite', re.I),   # 蛭石非蒙脱石
    'kaolinite': re.compile(r'hisingerite', re.I),   # 硅铁石非高岭石
}

# R5 混合/衍生标记(名称):百分数/加号混合、阳离子交换、热处理(\b\d{3}C\b = "200C" 温度后缀)、w/C
DERIVED_RX = re.compile(
    r'%|\+|mixture|cation.?exchanged|heated|treated|acidified|laid on|\b\d{3}C\b|w/C\b', re.I)
# 族级否决(名称含这些词则该族不成立,防 "Illite-Smectite Mixed Layer" 进 illite)
MIXED_LAYER_RX = re.compile(r'mixed.?layer', re.I)

# RELAB 的 group 是矿物学超群 taxonomy(非组成):alunite 超群含 jarosite,
# calcite 超群含 siderite/dolomite/magnesite,mica 超群含 illite/muscovite。
# name/subtype 命中族 ∈ 其 group 的超群闭包时不算冲突。
GROUP_SUPERSET = {
    'alunite': {'alunite', 'jarosite'},
    'calcite': {'calcite', 'siderite', 'dolomite', 'magnesite'},
    'mica': {'muscovite', 'illite'},
}

def assign_family(rec):
    """R7:优先级 subtype > name > group;返回 (family, source) 或 (None, reason)。

    - subtype 命中唯一族 → 直接采用(group 为超群 taxonomy,不参与裁决)
    - subtype 无命中且 name 命中唯一族 → 采用,除非 group 命中异族且非超群包容
    - 均无命中且 group 命中唯一族 → 采用(复合组真值受限)
    - subtype 命中多族 / name 命中多族 / name 与 group 实质冲突 → 拒判
    """
    name = rec.name or ''
    subtype = (rec.mineral_subtype or '').strip()
    group = (rec.group or '').strip()
    if MIXED_LAYER_RX.search(name):
        return None, 'mixed-layer 名称'
    hits_name = {f for f, rx in FAMILY_RX if rx.search(name)}
    hits_sub = {f for f, rx in FAMILY_RX if subtype and rx.search(subtype)}
    hits_grp = {f for f, rx in FAMILY_RX if group and rx.search(group)}

    def ok(fam):
        neg = FAMILY_NEGATIVES.get(fam)
        if neg and (neg.search(name) or neg.search(subtype)):
            return False
        return True

    if len(hits_sub) > 1:
        return None, f'亚型跨族冲突 {sorted(hits_sub)}'
    if len(hits_sub) == 1:
        fam = next(iter(hits_sub))
        return (fam, 'subtype') if ok(fam) else (None, f'{fam} 否定模式踢出')
    if len(hits_name) > 1:
        return None, f'名称跨族冲突 {sorted(hits_name)}'
    if len(hits_name) == 1:
        fam = next(iter(hits_name))
        if not ok(fam):
            return None, f'{fam} 否定模式踢出'
        if hits_grp - {fam}:
            sup = GROUP_SUPERSET.get(group, set())
            if fam not in sup:
                return None, f'名称 {fam} 与 group {group!r} 实质冲突'
        return fam, 'name'
    if len(hits_grp) == 1:
        fam = next(iter(hits_grp))
        if not ok(fam):
            return None, f'{fam} 否定模式踢出'
        if ';' in group or '-' in group:
            return None, f'group 复合组 {group!r} 真值不足'
        return fam, 'group'
    if len(hits_grp) > 1:
        return None, f'group 跨族冲突 {sorted(hits_grp)}'
    return None, '族映射零命中'

# ------------------------------------------------------------- main
def main() -> int:
    from relablib import RelabLibrary
    lib = RelabLibrary(RELAB_ROOT)
    recs = lib.records

    # R8 排除集
    excl = set()
    with DEDUP_CSV.open(encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if row['library'] == 'RELAB' and row['strength'] == 'strong':
                excl.add(row['record'])
    print(f'R8 排重排除集: {len(excl)} 个 spec_id')

    # R9 同标本株:R8 记录的 specimen 根号(去尾部 -X 分样后缀)
    root_of = lambda s: re.sub(r'-[A-Za-z]$', '', (s or '').strip())
    excl_roots = {root_of(r.specimen_id) for r in recs
                  if r.spec_id in excl and root_of(r.specimen_id)}
    print(f'R9 连带排除标本根号: {len(excl_roots)} 个')

    funnel = Counter()
    rejected_family = Counter()
    selected = []
    for r in recs:
        if r.material_type != 'Mineral':
            funnel['R1 非单矿物'] += 1; continue
        if r.geometry != 'Bidirectional':
            funnel['R2 非双向几何'] += 1; continue
        if not (r.range_nm[0] <= 500 and r.range_nm[1] >= 2450):
            funnel['R3 波段覆盖不足'] += 1; continue
        if ';' in (r.mineral_type or ''):
            funnel['R4 多矿物归属'] += 1; continue
        grp_ = (r.group or '')
        if ';' in grp_:
            # ';' 组二义:固溶体系列名(clinozoisite;epidote,成员同族)放行;
            # 两相混合物(calcite;graphite 等,匹配成员 <2 或跨族)出局
            members = grp_.split(';')
            mem_match = [any(rx.search(m) for _, rx in FAMILY_RX) for m in members]
            mem_fams = {f for m in members for f, rx in FAMILY_RX if rx.search(m)}
            if sum(mem_match) < 2 or len(mem_fams) > 1:
                funnel['R4 多矿物归属'] += 1; continue
        if DERIVED_RX.search(r.name or ''):
            funnel['R5 混合/衍生名称'] += 1; continue
        if '/' in (r.mineral_subtype or ''):
            funnel['R6 亚型双重归属'] += 1; continue
        fam, src = assign_family(r)
        if fam is None:
            funnel['R7 族外/冲突'] += 1
            rejected_family[src] += 1
            continue
        if r.spec_id in excl:
            funnel['R8 排重(CMS 同材料)'] += 1; continue
        if root_of(r.specimen_id) in excl_roots:
            funnel['R9 同标本株连带'] += 1; continue
        selected.append({
            'spec_id': r.spec_id, 'specimen_id': r.specimen_id,
            'name': r.name, 'family': fam, 'truth_source': src,
            'mineral_type': r.mineral_type, 'mineral_subtype': r.mineral_subtype,
            'group': r.group, 'subdir': r.subdir,
            'range_nm': f'{r.range_nm[0]:.0f}-{r.range_nm[1]:.0f}',
            'instrument': r.instrument,
            'has_chemistry': '',  # 化学验证腿后续回填
            'description': (r.description or '').replace('\n', ' ')[:200],
        })
    funnel['入选'] = len(selected)

    print('== 遴选漏斗 ==')
    total = len(recs)
    for k, v in funnel.most_common():
        print(f'  {k:24s} {v:6d}')
    fam_c = Counter(s['family'] for s in selected)
    fam_spec = defaultdict(set)
    for s in selected:
        fam_spec[s['family']].add(s['specimen_id'])
    print('== 各族入选(光谱 / 标本) ==')
    for f, c in fam_c.most_common():
        print(f'  {f:15s} {c:4d} / {len(fam_spec[f])}')

    # ------------------------------------------------- 产物
    rules_doc = {
        'date': str(date.today()),
        'source': f'relablib @ {RELAB_ROOT}',
        'rules': {
            'R1': "material_type == 'Mineral'",
            'R2': "geometry == 'Bidirectional'",
            'R3': 'range covers [500, 2450] nm',
            'R4': "mineral_type 不含 ';';group ';' 复合组仅固溶体系列(匹配成员≥2 且同族)放行",
            'R5': f'名称不含混合/衍生标记 {DERIVED_RX.pattern}',
            'R6': "mineral_subtype 不含 '/'",
            'R7': '族映射优先级 subtype>name>group;group 为超群 taxonomy(alunite⊃jarosite,calcite⊃siderite/dolomite,mica⊃illite/muscovite);mixed-layer/蛭石/硅铁石否定',
            'R8': '排除 crosslib_dedup_hits.csv strength=strong(CMS 同材料)',
            'R9': 'R8 命中标本根号的分样株(-A/-B…)连带排除(改名分样防漏)',
        },
        'families': {f: sorted(s['spec_id'] for s in selected if s['family'] == f)
                     for f in sorted(fam_c)},
    }
    OUT_JSON.write_text(json.dumps(rules_doc, ensure_ascii=False, indent=2),
                        encoding='utf-8')

    with OUT_CSV.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(selected[0]))
        w.writeheader()
        w.writerows(selected)

    absent = [f for f, _ in FAMILY_PATTERNS if f not in fam_c]
    L = []
    A = L.append
    A('# RELAB 跨库基准 · 阶段1 遴选')
    A('')
    A(f'> 日期:{date.today()} | 脚本:`docs/_relab_stage1_selection.py`(可重复执行) | '
      f'数据:relablib @ `{RELAB_ROOT}` | 排重:`crosslib_dedup_hits.csv`(R8)')
    A('')
    A('## 遴选规则')
    A('')
    for k, v in rules_doc['rules'].items():
        A(f'- **{k}** {v}')
    A('')
    A('## 遴选漏斗')
    A('')
    A('| 阶段 | 记录数 |')
    A('|---|---|')
    A(f'| 全库 | {total} |')
    for k, v in funnel.most_common():
        if k != '入选':
            A(f'| ✗ {k} | {v} |')
    A(f'| **入选** | **{len(selected)}** |')
    A('')
    A('## 各族入选规模')
    A('')
    A('| 族 | 光谱 | 标本 |')
    A('|---|---|---|')
    for f, c in fam_c.most_common():
        A(f'| {f} | {c} | {len(fam_spec[f])} |')
    A(f'| **合计** | **{len(selected)}** | **{len({s["specimen_id"] for s in selected})}** |')
    A('')
    A('## RELAB 缺位族(由 ECOSTRESS 腿补足)')
    A('')
    A('`' + '`, `'.join(absent) + '`' if absent else '无')
    A('')
    A('## 备注')
    A('')
    A('- 族真值 = RELAB 档案矿物归属(subtype 优先,名称兜底);亚型不作真值。')
    A('- 同一标本的多条光谱(粒径/制样变体)全部保留;统计命中率时'
      '可按 specimen_id 做留一标本交叉验证,防粒径相关过拟合。')
    A('- 蒙脱石族入选样本已剔除 CMS 标样(SWy/SAz 等同材料),'
      '剩余为天然蒙脱石/皂石/绿脱石——这才是独立证据。')
    A('- **保留但需在论文中声明的边界样**:CMS 标样中**与 bundled 参考不同材料**者'
      '(STx-1、KGa-1/KGa-1b、IMt-2、SAz-2)构成合法独立测试;合成纯相'
      '(PIG004 方解石 / PIG005 石膏 / PIG006 滑石、Baker 系合成绿脱石)保留——'
      'bundled 参考本身亦含合成样(GDS96/RES-3/GDS99),判据一致。')
    OUT_MD.write_text('\n'.join(L) + '\n', encoding='utf-8')
    print(f'产物: {OUT_JSON.name}, {OUT_CSV.name}, {OUT_MD.name}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
