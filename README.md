# Cyberrank report generator

JSON payload -> "Cyber Risk Report" PDF with ReportLab Platypus 5 (flowing story, no HTML/CSS).
AI agents: read [AGENTS.md](AGENTS.md) first.

## Cara pakai (versi super gampang)

Bayangkan mesin cetak: kamu masukkan **satu file data (JSON)**, keluar **satu file PDF report**.

### 1. Siapkan komputernya (sekali saja)

Butuh **Python 3.13**. Lalu di terminal, masuk ke folder ini dan ketik:

    python3.13 -m venv .venv
    .venv/bin/pip install -r requirements.txt

(Windows: ganti `.venv/bin/` dengan `.venv\Scripts\`.)

### 2. Siapkan datanya

Satu file JSON per organisasi. Contoh lengkap yang 100% fiktif: `data/demo-preview.json`.
Isinya, gampangnya:

| Bagian JSON | Isinya apa |
|---|---|
| `identity` | nama organisasi + domain (misal `example.com`) |
| `snapshot` | tanggal assessment, tanggal generate, versi metodologi |
| `sections.<nama>` | hasil tiap aspek: privacy, vulnerabilities, credential_exposure, data_leak_history, data_sovereignty, data_residency, legal_terms, ai_risk_governance, quantum_security, security_resourcing, certifications, fourth_party_vendors, cloud_infrastructure, + executive_overview, priority_actions |
| `appendices` | data register panjang untuk lampiran (credential, quantum, dll.) |

Aturan wajib di data (kalau dilanggar, program berhenti dan bilang salahnya di mana):
- Setiap section punya `state`: `findings`, `clear`, `partial`, `pending_review`, `not_assessed`, `not_applicable`, `unavailable`, atau `none_identified`.
- Nilai yang kosong (`null`) **harus** ada alasannya (`reason_code`). Report tidak pernah menulis 0 untuk data yang tidak ada.
- Setiap angka punya satuan (`unit`).
- Tanggal ditulis `YYYY-MM-DD`.
- Email akun sudah disamarkan oleh sistem (contoh `j*****n@example.com`).
- Dokumen sertifikat upload (opsional): `certificates[].document` = path file PNG/JPG/PDF, relatif ke file JSON.

Daftar lengkap semua field: [data/report-schema.md](data/report-schema.md).
Per aspek (data dari sistem, teks hardcode, aturan if/else): [docs/aspects/](docs/aspects/README.md).

### 3. Cetak reportnya

    .venv/bin/python -m cyberrank_report.build data/demo-preview.json -o output/report.pdf

Selesai. Hasilnya `output/report.pdf` + `output/report.qa.json` (hasil pengecekan otomatis).

- `error: 0` = aman. Ada error = baca `report.qa.json`, di situ tertulis masalahnya.
- Halaman "Supply-chain aggregation" di Appendix C diambil dari PDF lain yang **tidak ada di repo**.
  Kasih tahu lokasinya sebelum mencetak, kalau tidak QA akan melapor 1 error:

      export CYBERRANK_SUPPLY_CHAIN_PDF="/path/ke/report-produksi.pdf"
      export CYBERRANK_SUPPLY_CHAIN_INDEX=44     # nomor halaman, mulai dari 0

### 4. Cek semuanya masih benar (setelah mengubah kode)

    .venv/bin/python -I tests/test_kit.py

Semua baris harus `ok`.

## Install (detail)

    python3.13 -m venv .venv          # Homebrew 3.13/3.14 may have a broken pyexpat; a uv-managed Python works
    .venv/bin/pip install -r requirements.txt
    echo "$PWD" > "$(.venv/bin/python -c 'import site; print(site.getsitepackages()[0])')/cyberrank_report_dev.pth"

The `.pth` line lets `python -I` (isolated mode) import the package from any directory.

## Build

    .venv/bin/python -I -m cyberrank_report.build data/claude-2026-10-02.json -o output/report.pdf
    .venv/bin/python -I -m cyberrank_report.build data/claude-2026-10-02.json -o output/s04.pdf --only s04,appD
    .venv/bin/python -I -m cyberrank_report.build data/claude-2026-10-02.json -o output/bp.pdf --blueprint
    .venv/bin/python -I -m cyberrank_report.component_sheet data/claude-2026-10-02.json -o output/Component_Sheet.pdf
    .venv/bin/python -I tests/test_kit.py

The payload is validated at load (`build.validate`): every `state` in the state enum, every
null with a reason, every metric with a unit, every date (`*_at`, `valid_from`, `valid_until`,
`last_scanned`) ISO 8601 with a `precision` when shorter than a day. A contract error exits 1 and lists each path.
Each build also writes `<out>.qa.json`. Exit code 2 = QA errors. A word broken by character is an
error in prose and label cells; in a URL, hash, host or address it is a warning (character-breakable by
design). Input with a `not_assessed` / `not_applicable` / `unavailable` state and no `reason_code` or
`state_reason` is rejected at load (exit 1).
Section ids: `s01`..`s15`, `appA`..`appD` (layout v15: 01 overview, 02 actions, then the demerit ledger
A–J: 03 privacy, 04 vulnerabilities, 05 credential exposure, 06 data breach and leak history, 07 data
sovereignty, 08 data residency, 09 legal terms & conditions, 10 AI, 11 quantum, 12 security resourcing;
then 13 certifications, 14 fourth-party vendors, 15 cloud). Old payloads with the sub-areas nested under
`sections.privacy` are lifted at load (`sections.lift_privacy_subsections`). `--blueprint` draws frame boundaries and shows
the payload fields of each section instead of its body.

## Layout

    cyberrank_report/
      theme.py            tokens: geometry, colours, grade/impact/state colours, STYLES (all ParagraphStyles)
      fonts.py            registers Poppins Light/Regular/Medium/SemiBold, JetBrains Mono (technical tokens:
                          `tech` styles at 0.9x) and the per-character glyph fallback Noto Sans Math ->
                          Noto Sans Symbols 2 -> Noto Sans SC (CJK subset per build with fontTools); a character
                          no font has -> QA warning missing_glyph
      page.py             ReportDoc (cover / interior / locked templates), header, footer, watermark,
                          Page x of y, outline + anchors, locked external pages, identity_from_report()
      icons.py            Phosphor regular icons (states, aspects, yes/no, quantum categories, PQC) and the
                          severity siren (Critical 5 rays, High 3, Medium/Moderate 2, Low 0). Tables and detail blocks: siren only
                          (SeverityIcon, word as invisible text) + one severity_legend() box; tiles keep labels.
                          Self-check: python -I -m cyberrank_report.icons
      components.py       section_opener, state_card, kpi_strip, compact_table, chips, key_value_list,
                          register_pointer/anchor, tech(), P(), fmt_value(), Contents, Keep
      sections/__init__.py  REGISTRY (SectionSpec), Ctx, render_section() (state dispatch)
      sections/_template.py reference section module -- copy to sections/<spec.module>.py
      geo_map.py          section 08 residency map: country resolver, Equal Earth, automatic mode C / A2 / A3
                          (assets/geo: Natural Earth 1:110m, public domain; regenerate with tools/geo_prep.py)
      build.py            CLI
      component_sheet.py  visual reference of every component and state
      qa.py               overflow checks + PyMuPDF post-render checks -> JSON
      tables.py           CompactTable: a part that continues on a new page opens with
                          '<title> · continued' + 'Rows a–b of N' above the repeated header
      assets/             Poppins, Inter (cover + header title), JetBrains Mono, Noto Sans Math / Symbols 2 / SC Light (all OFL), Cyberrank logo, Bootstrap icons (MIT, footer), Phosphor 2.1.1 (MIT)

## Writing a section

Create `cyberrank_report/sections/<module>.py` (module names are in `REGISTRY`) with
`build(data, ctx) -> list[Flowable]`. The opener and the state card come from
`render_section()`; never draw them, never force page breaks, never pass raw data into `M()`.
Missing values print `Not available (reason)`, never 0. See `sections/_template.py`.
