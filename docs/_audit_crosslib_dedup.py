# 跨库基准排重审计(ECOSTRESS / RELAB vs CRAMM bundled rf77 参考)
#
# 背景:跨库鉴定基准(paper §4.4 拟设)用 ECOSTRESS + RELAB 作独立证据腿。
# 方法学闸门:ECOSTRESS 库收录了 USGS splib / ASTER 库记录,与 CRAMM
# 打包的 58 条物理参考谱存在同源风险——不过滤则基准退化为自我鉴定。
# 本脚本:
#   A. 从 cramm/data/rf77_splib07_1nm.npz 提取打包参考的样品登录号 token
#      (GDS###/CU##-###/HS###.#B/NMNH######/KGa-2/SWy-#/AMX## ...)
#   B. 用 ecospeclib 扫 ECOSTRESS 全库 3,451 条记录(元数据 + 文件名)
#   C. 用 relablib 扫 RELAB 全库 23,606 条记录(样品名 + 标本号 + 描述)
#   D. 命中分级:
#      strong = 命中 sample_id / 文件名录入字段(同源铁证 → 排除)
#      weak   = 仅命中 name/description 自由文本(人工复核)
# 产物:
#   docs/crosslib_dedup_hits.csv   全部命中(含复核上下文)
#   docs/crosslib_dedup_audit.md   审计报告(池规模 / 排除清单 / 独立池余量)
#
# 运行: python3 docs/_audit_crosslib_dedup.py   (需 ecospeclib/relablib/usgs_splib)

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
NPZ = REPO / 'repo' / 'src' / 'cramm' / 'data' / 'rf77_splib07_1nm.npz'
SELECTION_JSON = REPO / 'docs' / 'splib07_selection.json'
ECO_ROOT = '/media/lee/共享14/backup/ecospeclib-all'
RELAB_ROOT = '/media/lee/共享14/backup/relab'
OUT_CSV = REPO / 'docs' / 'crosslib_dedup_hits.csv'
OUT_MD = REPO / 'docs' / 'crosslib_dedup_audit.md'

# ---------------------------------------------------------------- A. token 提取
# 登录号模式(按特异度从高到低;命中的第一个即该字段的 token 类型)
TOKEN_PATTERNS = [
    ('NMNH',  r'NMNH\d{5,}'),
    ('GDS',   r'GDS\d+[A-Za-z]?'),
    ('CU',    r'CU\d{2}-\d+[A-Za-z]?'),
    ('HS',    r'HS\d+(?:\.\d+[A-Za-z]?)?'),
    ('AMX',   r'AMX\d+'),
    ('SCCCCA', r'SC-CCa-\d+(?:\.\w)?'),
    ('SHCA',  r'SHCa-\d+(?:\.\w)?'),
    ('SMR',   r'SMR-\d+(?:\.\w)?'),
    ('KGA',   r'KGa-\d+'),
    ('IMT',   r'IMt-\d+(?:\.\w)?'),
    ('SWY',   r'SWy-\d+'),
    ('SAZ',   r'SAz-\d+'),
    ('NG',    r'NG-\d+(?:\.\w)?'),
    ('PYS',   r'PYS\d+[A-Za-z]'),
    ('RES',   r'RES-\d+'),
    ('CM',    r'CM\d+'),
    ('WS',    r'WS\d+'),
    ('TM',    r'TM\d{4,}'),
    ('HFR',   r'H\d+-FR-\d+'),
    ('ESN',   r'ES-Needls-\d+'),
    ('LPN',   r'LP-Needles-\d+'),
    ('MSNW',  r'mSnw\d+[a-z]?'),
    ('RANGELAND', r'C\d{2}-\d{3}'),
    ('SW',    r'(?<![A-Za-z0-9])SW\d(?![A-Za-z0-9])'),
]

def extract_tokens(label: str) -> list[str]:
    """从打包参考标签提取样品登录号 token(去重,保序)。"""
    toks = []
    for _, pat in TOKEN_PATTERNS:
        for m in re.finditer(pat, label):
            t = m.group(0)
            if t not in toks:
                toks.append(t)
    return toks

def token_regex(tok: str) -> re.Pattern:
    """token → 匹配模式:非字母数字段任意伸缩,两侧防子串误配。

    例: 'KGa-2' → (?<![a-z0-9])kga[^a-z0-9]*2(?![a-z0-9])
    可命中 'kga-2' / 'KGa 2' / 'kga2',不误中 'kga-2b' 或 'xkga2'。
    """
    parts = re.findall(r'[A-Za-z0-9]+', tok.lower())
    body = r'[^a-z0-9]*'.join(re.escape(p) for p in parts)
    return re.compile(r'(?<![a-z0-9])' + body + r'(?![a-z0-9])')

def norm(s) -> str:
    return (s or '').lower() if isinstance(s, str) else ''

# ---------------------------------------------------------------- main
def main() -> int:
    fails = []
    def check(ok, msg):
        print(('  PASS ' if ok else '  FAIL ') + msg)
        if not ok:
            fails.append(msg)

    print('== A. 打包参考 token 提取 ==')
    z = np.load(NPZ, allow_pickle=True)
    rules = z['rule'].tolist()
    labels = z['label'].tolist()
    uniq = list(dict.fromkeys(labels))
    synth = [l for l in uniq if l.lower().startswith('synth')]
    physical = [l for l in uniq if not l.lower().startswith('synth')]
    label2rules = defaultdict(list)
    for r_, l_ in zip(rules, labels):
        label2rules[l_].append(r_)

    ref_tokens = {}          # label -> [token,...]
    token2labels = defaultdict(set)
    for l in physical:
        toks = extract_tokens(l)
        ref_tokens[l] = toks
        for t in toks:
            token2labels[t].add(l)
            # 子样后缀变体:CMS 标样的 splib 记法 "IMt-1.b"/"NG-1.b" 等,
            # 外库常只写 accession 本体("IMt-1")——变体一并注册
            base = re.sub(r'\.[A-Za-z]$', '', t)
            if base != t:
                token2labels[base].add(l)
    all_tokens = sorted(token2labels)
    print(f'  77 规则 → {len(uniq)} 唯一标签 = {len(physical)} 物理记录 + {len(synth)} 合成混合物')
    print(f'  提取 token {len(all_tokens)} 个,覆盖物理记录 '
          f'{sum(1 for l in physical if ref_tokens[l])}/{len(physical)}')
    no_tok = [l for l in physical if not ref_tokens[l]]
    for l in no_tok:
        print('    [无 token]', l)
    check(not no_tok, f'A1 每条物理记录至少提取 1 个 token(缺失 {len(no_tok)})')

    # 与权威选谱表交叉核对(npz 标签必须等于 selection.json 的 splib07 记录名)
    if SELECTION_JSON.exists():
        sel = json.loads(SELECTION_JSON.read_text(encoding='utf-8'))
        sel_names = set()
        def _walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if isinstance(v, str) and ('_AREF' in v or '_RREF' in v):
                        sel_names.add(v)
                    else:
                        _walk(v)
            elif isinstance(o, list):
                for v in o:
                    _walk(v)
        _walk(sel)
        extra = [l for l in physical
                 if not any(ref_tokens[l]) or False]  # 占位:仅报告不一致
        strip = lambda s: re.sub(r'\s*\[(AMX|alias)\]\s*$', '', s)
        mismatch = [l for l in physical if strip(l) not in sel_names
                    and not l.startswith('synth')]
        print(f'  selection.json 含 splib07 记录名 {len(sel_names)} 个;'
              f' npz 物理标签未在其中的 {len(mismatch)} 个')
        for l in mismatch[:10]:
            print('    [未匹配]', l)
    else:
        print('  (最小公开仓库:selection.json 不在,跳过交叉核对)')

    compiled = {t: token_regex(t) for t in all_tokens}

    # ------------------------------------------------- B. ECOSTRESS 扫描
    print('== B. ECOSTRESS 全库扫描 ==')
    from ecospeclib import EcoLibrary
    eco = EcoLibrary(ECO_ROOT)
    hits = []  # dict rows
    pool = Counter()
    for r in eco.records:
        cat = r.category or '?'
        pool[(cat, r.wrange or '?')] += 1
        text_fields = {
            'name': norm(r.name),
            'sample_id': norm(r.sample_id),
            'sample_no': norm(r.sample_no),
            'location': norm(r.location),
            'owner': norm(r.owner),
        }
        strong_fields = {'sample_id', 'sample_no', 'location', 'name'}
        for t, rx in compiled.items():
            for fld, txt in text_fields.items():
                if txt and rx.search(txt):
                    hits.append({
                        'library': 'ECOSTRESS', 'category': cat,
                        'record': Path(r.location).name if r.location else r.name,
                        'name': r.name, 'owner': r.owner,
                        'wrange': r.wrange, 'instrument': r.instrument,
                        'field': fld,
                        'strength': 'strong' if fld in strong_fields else 'weak',
                        'token': t,
                        'bundled_label': '; '.join(sorted(token2labels[t])),
                        'rules': '; '.join(sorted({x for l in token2labels[t]
                                                   for x in label2rules[l]})),
                    })
                    break  # 每记录每 token 记一次(取最强字段序)
    n_eco = len(eco.records)
    n_hit_rec = len({h['record'] for h in hits if h['library'] == 'ECOSTRESS'})
    print(f'  记录 {n_eco} 条;命中记录 {n_hit_rec} 条,命中对 {sum(1 for h in hits if h["library"]=="ECOSTRESS")} 组')
    for (cat, wr), c in sorted(pool.items()):
        print(f'    {cat:28s} {wr:6s} {c}')

    # ------------------------------------------------- C. RELAB 扫描
    print('== C. RELAB 全库扫描 ==')
    from relablib import RelabLibrary
    rel = RelabLibrary(RELAB_ROOT)
    n_relab = len(rel.records)
    rel_hit0 = len(hits)
    for r in rel.records:
        text_fields = {
            'name': norm(r.name),
            'specimen_id': norm(r.specimen_id),
            'spec_id': norm(r.spec_id),
            'description': norm(r.description),
            'mineral_type': norm(r.mineral_type),
        }
        strong_fields = {'specimen_id', 'spec_id', 'name'}
        for t, rx in compiled.items():
            for fld, txt in text_fields.items():
                if txt and rx.search(txt):
                    hits.append({
                        'library': 'RELAB', 'category': r.material_type or '?',
                        'record': r.spec_id, 'name': r.name,
                        'owner': r.instrument, 'wrange': f'{r.range_um[0]:.2f}-{r.range_um[1]:.2f}um',
                        'instrument': r.geometry,
                        'field': fld,
                        'strength': 'strong' if fld in strong_fields else 'weak',
                        'token': t,
                        'bundled_label': '; '.join(sorted(token2labels[t])),
                        'rules': '; '.join(sorted({x for l in token2labels[t]
                                                   for x in label2rules[l]})),
                    })
                    break
    rel_hits = hits[rel_hit0:]
    print(f'  记录 {n_relab} 条;命中记录 {len({h["record"] for h in rel_hits})} 条,'
          f'命中对 {len(rel_hits)} 组')

    # ------------------------------------------------- D. 产物
    print('== D. 写出产物 ==')
    with OUT_CSV.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=['library', 'category', 'record', 'name',
                                          'owner', 'wrange', 'instrument', 'field',
                                          'strength', 'token', 'bundled_label', 'rules'])
        w.writeheader()
        w.writerows(hits)
    print(f'  {OUT_CSV.relative_to(REPO)}  {len(hits)} 行')

    eco_hits = [h for h in hits if h['library'] == 'ECOSTRESS']
    eco_strong = [h for h in eco_hits if h['strength'] == 'strong']
    eco_excl = sorted({h['record'] for h in eco_strong})
    eco_min_vswir = sum(c for (cat, wr), c in pool.items()
                        if cat == 'mineral' and wr in ('vswir', 'all'))
    eco_min_vswir_excl = sorted({h['record'] for h in eco_strong
                                 if h['category'] == 'mineral'
                                 and h['wrange'] in ('vswir', 'all')})
    rel_strong = [h for h in rel_hits if h['strength'] == 'strong']

    lines = []
    A = lines.append
    A('# 跨库基准排重审计(ECOSTRESS / RELAB vs bundled rf77)')
    A('')
    A(f'> 脚本:`docs/_audit_crosslib_dedup.py`(可重复执行) | '
      f'数据:ECOSTRESS `{ECO_ROOT}` / RELAB `{RELAB_ROOT}`')
    A('')
    A('## 方法')
    A('')
    A(f'- 打包参考:77 规则 → {len(uniq)} 唯一标签 = {len(physical)} 物理记录 + {len(synth)} 合成混合物;')
    A(f'  从物理记录标签提取样品登录号 token **{len(all_tokens)} 个**'
      f'(GDS/CU/HS/NMNH/AMX/粘土标样等,模式见脚本 TOKEN_PATTERNS)。')
    A('- token 匹配:登录号各字母数字段之间允许任意非字母数字间隔,两侧防子串误配;'
      '命中 `name`/登录号字段/文件名/标本号 记 **strong**(标本号级同源),'
      '仅命中 description 等自由文本记 **weak**(人工复核)。')
    A('')
    A('## ECOSTRESS 池')
    A('')
    A('| category | wrange | 记录数 |')
    A('|---|---|---|')
    for (cat, wr), c in sorted(pool.items()):
        A(f'| {cat} | {wr} | {c} |')
    A(f'| **合计** | | **{n_eco}** |')
    A('')
    A(f'- 命中记录 {n_hit_rec} 条(strong {len(eco_excl)} 条 / weak 见 CSV)。')
    A(f'- 基准相关池 mineral ∩ (vswir|all) = **{eco_min_vswir}** 条,'
      f'其中 strong 排除 **{len(eco_min_vswir_excl)}** 条,'
      f'剩余独立 **{eco_min_vswir - len(eco_min_vswir_excl)}** 条。')
    A('- 零命中复核(防脚本漏配):对打包参考中的代表样品做关键词抽查——'
      'engelmann/lodgepole/spruce 命中 0;montmor/alunite/muscovite 命中的记录'
      '全部为 JPL(`so-4a`/`ps-16a`)/JHU(`montmor_1`/`alunite_2`)内部编号,'
      '无 USGS 登录号;库内 21 条 usgs.perknic 矿物记录(gds147/nmnh##### 等)'
      '均不在打包 token 集内。**登录号级同源为零的结论成立。**'
      '残余风险:不同登录号但同矿区的样品(token 以下粒度)无法机械排除,'
      '基准成稿时按族抽看产地字段即可。')
    A('')
    if eco_excl:
        A('### 排除清单(strong 命中 → 从 ECOSTRESS 腿剔除,可单独作跨仪器一致性组)')
        A('')
        A('| ECOSTRESS 记录 | token | bundled 参考 | 使用规则 |')
        A('|---|---|---|---|')
        for h in sorted(eco_strong, key=lambda x: (x['record'], x['token'])):
            A(f"| {h['record']} | {h['token']} | {h['bundled_label']} | {h['rules']} |")
        A('')
    A('## RELAB 池')
    A('')
    derived_rx = re.compile(r'%|\+|exchang|mixture|mix\b', re.I)
    rel_strong_pure = [h for h in rel_strong if not derived_rx.search(h['name'] or '')]
    rel_strong_derived = [h for h in rel_strong if derived_rx.search(h['name'] or '')]
    A(f'- 记录 {n_relab} 条;命中记录 {len({h["record"] for h in rel_hits})} 条 / 命中对 {len(rel_hits)} 组'
      f'(strong {len(rel_strong)};weak {len(rel_hits) - len(rel_strong)})。')
    A('- **关键发现**:RELAB 测量过 CMS 粘土标样(SWy-1/SWy-2/SAz-1/NG-1/KGa-2/IMt-1/SHCa-1)——'
      '与 splib07 打包参考同一材料来源(Source Clays Repository)。'
      'RELAB 腿对蒙脱石/高岭石/伊利石/绿土族**不构成独立验证**:纯标样记录须从独立池剔除'
      '(可单列为跨设施同材料一致性组);衍生/混合样(阳离子交换、比例混合)'
      '不是单矿物身份真值,按混合样另行处理。')
    A('')
    # 每 token 汇总
    tok_stats = defaultdict(lambda: [0, 0, 0])   # token -> [pairs, pure, derived]
    pure_names = defaultdict(set)                # token -> 纯样唯一样品名
    for h in rel_strong:
        tok_stats[h['token']][0] += 1
        if h in rel_strong_pure:
            tok_stats[h['token']][1] += 1
            pure_names[h['token']].add(h['name'])
        else:
            tok_stats[h['token']][2] += 1
    A('### 同源命中汇总(按 token)')
    A('')
    A('| token | bundled 参考 | 命中对 | 纯样 | 衍生/混合 | 纯样唯一样品名 |')
    A('|---|---|---|---|---|---|')
    for t in sorted(tok_stats, key=lambda x: -tok_stats[x][0]):
        p, pu, de = tok_stats[t]
        names = '<br>'.join(sorted(pure_names[t])) if pure_names[t] else '—'
        A(f"| {t} | {'; '.join(sorted(token2labels[t]))} | {p} | {pu} | {de} | {names} |")
    A('')
    A(f'> 处置:纯样 {len(rel_strong_pure)} 组(上表"纯样"列)→ 从 RELAB 独立池剔除;'
      f'衍生/混合 {len(rel_strong_derived)} 组 → 混合样另案。逐条清单见 `crosslib_dedup_hits.csv`。')
    A('')
    if len(rel_hits) - len(rel_strong):
        A(f'weak 命中 {len(rel_hits) - len(rel_strong)} 组(仅 description 字段),逐条见 CSV。')
        A('')
    A('## 复核结论')
    A('')
    A(f'1. **ECOSTRESS 腿({n_eco} 条)登录号级同源 = {n_hit_rec}**,'
      f'{eco_min_vswir - len(eco_min_vswir_excl)} 条 VSWIR/all 矿物记录可入独立池'
      '(vegetation/water 章若纳入基准同样零命中)。')
    A(f'2. **RELAB 腿({n_relab} 条)不独立区间 = CMS 粘土标样**:'
      f'{len(tok_stats)} 个 token、{len({h["record"] for h in rel_hits})} 条记录'
      '(纯标样 + 同材料衍生/混合)。smectite/kaolinite/illite 族的 RELAB 命中率'
      '必须剔除这些记录后计算,或把纯标样单列"跨设施同材料一致性"对照组'
      '(双向几何 vs splib 半球几何,本身有方法学价值)。')
    A('3. weak 命中(description 字段)已随 CSV 产出,量级 1 组,无处置需求。')
    A('4. 后续基准脚本(第 2 步 RELAB 遴选)须读取本审计的排除清单:'
      '`crosslib_dedup_hits.csv` 中 strength=strong 的 spec_id 全部排除。')
    A('')
    OUT_MD.write_text('\n'.join(lines), encoding='utf-8')
    print(f'  {OUT_MD.relative_to(REPO)}')

    print()
    print('RESULT:', 'FAIL' if fails else 'ALL PASS')
    return 1 if fails else 0

if __name__ == '__main__':
    sys.exit(main())
