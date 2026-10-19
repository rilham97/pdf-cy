"""Add `account_label_masked` to every credential register row of a fixture (policy option B, 2026-10-15).

usage: python -I add_account_labels.py <fixture.json> <tables.json>
tables.json: output of the matching parse_tables.py (claude: ./parse_tables.py, instagram/, gmail/); its
credential rows carry `label` (as printed when masked, else masked at preparation: first + last character of
the local part kept, rest '*', domain kept) and `masked_here`. Rows are matched by position; each pair must
agree on domain class, email state and period, so a misaligned parse fails instead of mislabelling.
Run after build_fixture.py (which writes the label-free fixture). Everything else is left as is.
"""
import json
import sys

fixture_path, tables_path = sys.argv[1:3]
text = open(fixture_path, encoding='utf-8').read()
indent = len(text.split('\n')[1]) - len(text.split('\n')[1].lstrip(' '))
report = json.loads(text)
src = json.load(open(tables_path, encoding='utf-8'))
src = src['credentials'] if isinstance(src, dict) else src
reg = report['appendices']['d_evidence_registers']['credential_register']
rows = reg['rows']
assert len(rows) == len(src), (len(rows), len(src))

STATE = {'masked_present': 'masked_label_present', 'unmasked_present': 'unmasked_label_dropped'}
masked_here = 0
for r, s in zip(rows, src):
    state = STATE.get(s['email_state'], s['email_state'])
    assert r['email_state'] in (state, 'unmasked_label_masked_at_preparation'), (r['id'], r['email_state'], state)
    dom = s['email_domain']
    assert r['email_domain'] == dom or (r['email_domain'] == 'external' and dom == 'external') \
        or (r['email_domain'] is None and dom is None), (r['id'], r['email_domain'], dom)
    period = ', '.join(s['period'])
    assert r['exposure_period_source'].replace(' ', '') == period.replace(' ', ''), (r['id'], period)
    label = s['label']
    assert label == 'Unknown Email' or '*' in label.split('@')[0], r['id']
    r['account_label_masked'] = label
    if s['masked_here']:
        masked_here += 1
        r['email_state'] = 'unmasked_label_masked_at_preparation'
cols = reg['columns']
if 'account_label_masked' not in cols:
    cols.insert(cols.index('email_state') + 1, 'account_label_masked')

san = report['meta']['sanitisation']
keep = ' Vendor company blurbs (which name founders) are not carried.' if 'Vendor company blurbs' in san.get('rule', '') \
    else ''
san['rule'] = ('Credential rows carry the account label as the Cyberrank system delivers it (masked upstream), copied '
               'from the source PDF; no password/token value or other personal identifier. Labels the source printed '
               'without a mask character were masked at fixture preparation (first and last character of the local '
               'part kept, the rest replaced with *, domain kept).' + keep)
san['removed_fields'] = [f for f in san.get('removed_fields', []) if f != 'credential_register.email_masked']
san.pop('source_rows_with_unmasked_local_part', None)
san['account_labels'] = {'field': 'credential_register.rows[].account_label_masked', 'rows': len(rows),
                         'copied_as_printed': len(rows) - masked_here, 'masked_at_fixture_preparation': masked_here,
                         'email_state_of_those_rows': 'unmasked_label_masked_at_preparation',
                         'mask_rule': 'local[0] + "*" * (len(local) - 2) + local[-1] + "@" + domain'}
san['note'] = (f'{masked_here} of {len(rows)} account labels were printed unmasked in the source and were masked at '
               'fixture preparation; all other labels are copied as the source printed them.')

out = json.dumps(report, ensure_ascii=False, indent=indent).replace(
    'print an unmasked local part (dropped)', 'print an unmasked local part (masked at fixture preparation)')
open(fixture_path, 'w', encoding='utf-8').write(out + '\n')
print(fixture_path, 'rows', len(rows), 'masked_at_preparation', masked_here)
