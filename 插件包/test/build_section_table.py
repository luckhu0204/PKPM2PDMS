# -*- coding: utf-8 -*-
"""从侦察转化表生成随包发布的内置截面转化表（架构包）。

输入（**只读**）：D:\\AI_Work\\PKPM数据解析\\_recon\\dbsect\\pkpm_pdms_section_table.csv
                  （3,176 行 × 38 列，UTF-8 带 BOM）
输出：engine/section_table.csv        —— 契约 §k.2 冻结的 15 列布局（UTF-8 带 BOM + CRLF）
      engine/section_table.meta.json —— 来源与校验和（UTF-8 无 BOM）

投影规则（逐条对应 CONTRACT §k.2，**纯机械映射 + 族码规则解码**，不修改源数据）：
  key             = pkpm_name 非空 ? pkpm_name : pdms_spec_path      （实测唯一）
  pkpm_name       = 源列 pkpm_name
  family_code     = int(源列 family_code) or 0
  family_name_cn  = 源列 family_cn
  kind            = int(源列 jwd_kind) or int(源列 pdt_kind) or 0
  shapeval        = 源列 shapeval_encoding（DLL 编码串，原样）
  dims            = 由 shapeval 按族码位置规则解出（键与 CONTRACT §a.4 同空间）
  mat             = 5（内置表默认=钢；来源见 §k.2 说明）
  pdms_spec_path  = 源列 pdms_spec_path
  pdms_catalogue  = 源列 pdms_catalogue
  is_parametric   = 源列 is_parametric == 'true'
  params          = zip(param_names 按 '|' 拆, para_values 按空白拆)
                    → [{name, desp_index: is_parametric ? i+1 : 0, default}]
  confidence      = 源列 confidence（high|medium|low）
  source          = 源列 source（组合串，原样）
  extra           = 其余列原样（含 in_*/jwd_*/pdt_*/conflict/name_variants/...）
  extra.dll_siblings = **派生**（本次 R2 修复新增，CONTRACT §k.2/§l.5）：recon §2.6 的 DLL 名集
                    （_dll_tokens.json + _dll_pairs_full.json，抽取规则与 test/acceptance_r2.py
                    的 _dll_variant_index 一致）里、归一键（norm_pkpm2）与该行相同、而该行
                    `dll_table_entry`/`name_variants` 未记录的拼写，以 ';' 连接。
                    背景：源表对"冷弯/热轧同名异族"的行（如 3-L25x16x3 与 L25X16X3、
                    8-B100*4.00 与 6-B100*4.00）把两行都标成了同一个 DLL 拼写，导致包内表
                    丢失 8 个键的另一种 DLL 拼写、§l.5 的 759 对大小写/写法差异只归类出 751 对。
                    源表在 _recon（只读），故在**派生列**补齐，不改源数据。

运行：python test/build_section_table.py
"""
import csv
import hashlib
import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
SRC = r'D:\AI_Work\PKPM数据解析\_recon\dbsect\pkpm_pdms_section_table.csv'
OUT_CSV = os.path.join(PKG, 'engine', 'section_table.csv')
OUT_META = os.path.join(PKG, 'engine', 'section_table.meta.json')

# recon §2.6 的 DLL 名集数据（只读；抽取规则与 test/acceptance_r2.py 的 _dll_variant_index 一致）
_DLL_TOKENS = os.path.join(os.path.dirname(SRC), '_dll_tokens.json')
_DLL_PAIRS = os.path.join(os.path.dirname(SRC), '_dll_pairs_full.json')
_CJK_RE = re.compile(r'^[\u4e00-\u9fff]+')
_NUMP_RE = re.compile(r'^\d+-')


def norm_pkpm(n):
    """recon §2.6 口径：去前导中文 + 大写。"""
    return _CJK_RE.sub('', (n or '').strip()).upper()


def norm_pkpm2(n):
    """再剥前导族码前缀（`3-`/`8-`…）：冷弯与热轧同尺寸截面按同一键归并。"""
    return _NUMP_RE.sub('', norm_pkpm(n))


def dll_name_set():
    """recon DLL 名集（显式 name↔code 对 + 码后相邻 token），规则同验收测试。"""
    import collections
    tokens = json.load(open(_DLL_TOKENS, encoding='utf-8'))
    pairs = json.load(open(_DLL_PAIRS, encoding='utf-8'))
    code_re = re.compile(r'^[-\d]+(,[^,]*)*$')
    lo, hi = 0x20640, 0x33A90
    explicit, carry, last = {}, {}, None
    for t in tokens:
        if code_re.match(t['s']):
            last = t['s']
        elif last is not None:
            carry[t['s']] = last
    for p in pairs:
        if lo <= p['name_off'] <= hi and lo <= p['code_off'] <= hi:
            explicit[p['name']] = p['code']
    return set(list(explicit) + list(carry))

#: 冻结列序（CONTRACT §k.2）——不得增删改序
COLUMNS = ['key', 'pkpm_name', 'family_code', 'family_name_cn', 'kind', 'shapeval',
           'dims_json', 'mat', 'pdms_spec_path', 'pdms_catalogue', 'is_parametric',
           'params_json', 'confidence', 'source', 'extra_json']

#: 已解族码 → shapeval 参数字段的位置规则（CONTRACT §k.3 表；键同 §a.4）
#:   ('位置键', 下标)  下标自 0 起，作用于 shapeval 去掉族码后的参数字段
FAM_RULES = {
    31: [('subtype', 0), ('name', 1)],
    32: [('subtype', 0), ('name', 1)],
    33: [('subtype', 0), ('b', 1), ('b2', 2), ('t', 3)],   # 等边 3 参 / 不等边 4 参
    36: [('H', 0), ('B', 1)],
    37: [('H', 0), ('B', 1)],
    38: [('H', 0), ('B', 1)],
    39: [('H', 0), ('B', 1)],
    40: [('H', 0), ('B', 1), ('order', 2)],
    66: [('h', 0), ('b', 1)],
    71: [('subtype', 0), ('name', 1)],
    72: [('subtype', 0), ('h', 1), ('b', 2), ('t', 3)],
    73: [('subtype', 0), ('b1', 1), ('b2', 2), ('b3', 3), ('t', 4)],
    77: [('lib_family', 0)],
}

#: DTSET 具名参数 → dims 键（§a.4 键空间）的对照；**只有尺寸类**进 dims，
#: 力学类（A/g/Ix/Wx/Sx/ix/Iy/Wy/iy/Iw/It/Ww/e0/x0/k/Ct/r1…）只留在 extra['params_named']
NAME_TO_KEY = {'h': 'H', 'b': 'B', 'tw': 'tw', 'tf': 'tf', 't': 't', 'd': 'd', 'r': 'r'}


def param_name_key(name):
    """`'h(mm)'` → `'H'`；不在对照表内返回 None（力学量/未知量不进行）。"""
    base = (name or '').split('(')[0].strip().lower()
    return NAME_TO_KEY.get(base)


def num_or_str(s):
    s = (s or '').strip()
    if s == '':
        return ''
    try:
        f = float(s)
    except ValueError:
        return s
    return int(f) if f.is_integer() else f


def decode_dims(family_code, shapeval):
    """族码 + 编码串 → dims（键同 §a.4；未知族返回 {}）。"""
    sv = (shapeval or '').strip()
    if not sv:
        return {}
    parts = [p.strip() for p in sv.split(',')]
    if not parts or parts[0] == '':
        return {}
    try:
        fam = int(float(parts[0]))
    except ValueError:
        return {}
    body = parts[1:]
    d = {'family': fam}
    rule = FAM_RULES.get(fam)
    if not rule:
        return d                     # 族码已知但字段含义未解（如 19/TRAPEZOID）→ 只记族码
    for key, idx in rule:
        if idx < len(body):
            d[key] = num_or_str(body[idx])
    return d


def main():
    raw = open(SRC, 'rb').read()
    src_sha = hashlib.sha256(raw).hexdigest()
    rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    print('源表：%d 行 × %d 列  sha256=%s' % (len(rows), len(rows[0]), src_sha[:16]))
    dll_names = dll_name_set()
    by_key2 = {}
    for n in dll_names:
        by_key2.setdefault(norm_pkpm2(n), []).append(n)
    print('DLL 名集（recon §2.6 口径）：%d 个，%d 个归一键' % (len(dll_names), len(by_key2)))

    out = []
    for r in rows:
        name = (r['pkpm_name'] or '').strip()
        path = (r['pdms_spec_path'] or '').strip()
        cfg = (r['family_code'] or '').strip()
        fam = int(float(cfg)) if cfg else 0
        kd = (r['jwd_kind'] or '').strip() or (r['pdt_kind'] or '').strip()
        try:
            kind = int(float(kd)) if kd else 0
        except ValueError:
            kind = 0
        para = [t for t in (r['para_values'] or '').split(' ') if t.strip()]
        names = [t for t in (r['param_names'] or '').split('|') if t.strip()]
        param_list = []
        for i, nm in enumerate(names):
            param_list.append({'name': nm,
                               'desp_index': (i + 1) if r['is_parametric'] == 'true' else 0,
                               'default': para[i] if i < len(para) else ''})
        # 具名参数（PARA 值 × DTSET 名）= 权威对位；已进 params[]（name/default）
        # ⇒ extra 里**不再**复制一份，仅在"长度不等"时保留原文（无损且避免三重复制）
        cat_names = [t for t in (r['stcategory_params'] or '').split('|') if t.strip()]
        key_names = cat_names or names
        params_named = {}
        for i, nm in enumerate(key_names):
            if i < len(para):
                params_named[nm] = para[i]
        # dims：位置解码（族码规则）为主，DTSET 具名参数补缺/校验（契约 §k.2）
        dims = decode_dims(fam, r['shapeval_encoding'])
        checks = []
        for nm, val in params_named.items():
            k = param_name_key(nm)
            if not k:
                continue
            v = num_or_str(val)
            if k in dims:
                if str(dims[k]) != str(v):
                    checks.append('%s: 位置=%s PARA=%s' % (k, dims[k], v))
            else:
                dims[k] = v
        extra = {}
        for c in rows[0].keys():
            if c in ('pkpm_name', 'family_cn', 'family_code', 'shapeval_encoding',
                     'pdms_spec_path', 'pdms_catalogue', 'param_names', 'is_parametric',
                     'para_values', 'confidence', 'source', 'jwd_kind', 'pdt_kind'):
                continue
            if r[c] not in (None, ''):
                extra[c] = r[c]
        if len(para) != len(names) and (para or names):
            extra['param_len_mismatch'] = '%d values vs %d names' % (len(para), len(names))
            extra['params_raw'] = {'names': key_names, 'values': para}
        if checks:
            extra['param_check'] = 'mismatch: ' + '; '.join(checks)
        # DLL 同键拼写（派生，§k.2/§l.5）：源表把"冷弯/热轧同名异族"两行标成同一个 DLL 拼写，
        # 包内表因此缺 8 个键的另一种拼写（§l.5 的 759 对只归出 751 对）。此处按 recon §2.6 的
        # DLL 名集补齐——只补 DLL 里真实存在的拼写，不引入表外字符串（口径不得放大）。
        own_names = set()
        if extra.get('dll_table_entry'):
            own_names.add(str(extra['dll_table_entry']).strip())
        for m in re.finditer(r'dll=([^;]+)', str(extra.get('name_variants') or '')):
            own_names.add(m.group(1).strip())
        k2 = norm_pkpm2(name or path)
        siblings = sorted(n for n in by_key2.get(k2, ()) if n not in own_names)
        if siblings:
            extra['dll_siblings'] = ';'.join(siblings)
        rec = {
            'key': name or path,
            'pkpm_name': name,
            'family_code': fam,
            'family_name_cn': r['family_cn'] or '',
            'kind': kind,
            'shapeval': (r['shapeval_encoding'] or '').strip(),
            'dims_json': json.dumps(dims,
                                    ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')),
            'mat': 5,
            'pdms_spec_path': path,
            'pdms_catalogue': (r['pdms_catalogue'] or '').strip(),
            'is_parametric': 'true' if r['is_parametric'] == 'true' else 'false',
            'params_json': json.dumps(param_list, ensure_ascii=False, sort_keys=True,
                                      separators=(',', ':')),
            'confidence': (r['confidence'] or '').strip(),
            'source': (r['source'] or '').strip(),
        }
        rec['extra_json'] = json.dumps(extra, ensure_ascii=False, sort_keys=True,
                                       separators=(',', ':'))
        out.append(rec)

    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator='\r\n')
    w.writeheader()
    for rec in out:
        w.writerow(rec)
    text = buf.getvalue()
    nonascii = [c for c in text if ord(c) > 127]
    data = text.encode('utf-8')
    with open(OUT_CSV, 'wb') as f:
        f.write(b'\xef\xbb\xbf' + data)          # UTF-8 带 BOM（与源表一致，Excel 可直开）
    out_sha = hashlib.sha256(data).hexdigest()

    keys = [r['key'] for r in out]
    paths = [r['pdms_spec_path'] for r in out]
    names = [r['pkpm_name'] for r in out if r['pkpm_name']]
    meta = {
        'schema': 'section_table/1.0',
        'contract': 'spec/CONTRACT.md §k.2',
        'generated_by': 'test/build_section_table.py',
        'source': SRC,
        'source_sha256': src_sha,
        'source_rows': len(rows),
        'output': 'engine/section_table.csv',
        'output_rows': len(out),
        'output_columns': COLUMNS,
        'output_sha256_no_bom': out_sha,
        'output_bytes_with_bom': len(data) + 3,
        'column_chars': None,          # 见 build 日志；params_json/extra_json 占大头（具名参数 + 溯源）
        'encoding': 'UTF-8 with BOM',
        'line_ending': 'CRLF',
        'dll_siblings': {              # 派生列的溯源（CONTRACT §k.2 / §l.5 的 759 对口径）
            'rule': 'recon §2.6 的 DLL 名集（norm_pkpm2 同键、行内未记录的拼写），'
                    '与 test/acceptance_r2.py _dll_variant_index 同一规则',
            'source': os.path.basename(_DLL_TOKENS) + ' + ' + os.path.basename(_DLL_PAIRS),
            'rows_with': len([r for r in out if 'dll_siblings' in json.loads(r['extra_json'])]),
            'names_total': len(dll_names),
        },
        'stats': {
            'keys_unique': len(set(keys)),
            'pkpm_name_nonempty': len(names),
            'pkpm_name_unique': len(set(names)),
            'pdms_spec_path_unique': len(set(paths)),
            'shapeval_nonempty': len([r for r in out if r['shapeval']]),
            'is_parametric_true': len([r for r in out if r['is_parametric'] == 'true']),
            'family_code_known': len([r for r in out if r['family_code']]),
            'kind_known': len([r for r in out if r['kind']]),
            'confidence': {c: len([r for r in out if r['confidence'] == c])
                           for c in ('high', 'medium', 'low')},
        },
    }
    with open(OUT_META, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(meta, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write('\n')

    print('写出 %s（%d 行）' % (OUT_CSV, len(out)))
    print('写出 %s' % OUT_META)
    print('stats=%s' % json.dumps(meta['stats'], ensure_ascii=False))
    print('非 ASCII 字符数=%d（中文名等，来自源列的 family_cn/pkpm_name）' % len(nonascii))
    print('\n抽查（应与 .jwd/.pdt 样本一致）：')
    for want in ('HN450X200', 'HN300X150', '2-[18a', '6-B250*10.00', 'RECT', 'CIRCLE',
                 '3-B25X1.5'):
        hit = [r for r in out if r['key'] == want]
        if hit:
            r = hit[0]
            print('  %-14s fam=%-3s kind=%-3s dims=%-52s spec=%s' %
                  (r['key'], r['family_code'], r['kind'], r['dims_json'],
                   r['pdms_spec_path']))
        else:
            print('  %-14s (不在表内)' % want)
    return 0


if __name__ == '__main__':
    sys.exit(main())
