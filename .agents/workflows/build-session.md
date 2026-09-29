# Workflow: Build Session

Empat sesi pembangunan MV-GPT DSS. Jalankan berurutan. Jangan lompat — tiap sesi
bergantung pada verifikasi sesi sebelumnya.

Sebelum sesi mana pun: baca `AGENTS.md`, `.agents/rules/dissertation-facts.md`,
dan `config/thresholds.yaml`.

---

## Sesi 1 — Fondasi dan RAM Engine

```
Siapkan struktur proyek sesuai AGENTS.md, lalu bangun config loader dan RAM Engine
mengikuti skill ram-engine. Tulis tests/test_ram.py LEBIH DULU memakai fixture dari
dissertation-facts.md bagian 2 (busi 250 jam: R(50)=81,87%, R(130)=59,45%;
switchgear 20 kV: MTBF 17,38 bulan, interval 18 bulan, A=99,63%). Baru implementasikan
sampai test hijau. Jalankan pytest dan tunjukkan outputnya.
```

**Kriteria selesai:** `pytest tests/test_ram.py -v` hijau, semua fixture naskah lolos,
tidak ada angka hardcode di `ram_engine.py`.

---

## Sesi 2 — EA Safety Checker

```
Bangun backend/safety/ea_checker.py mengikuti skill ea-safety-checker. Lima fungsi
deterministik, semua mengembalikan CheckResult. Baca seluruh threshold dari
config/thresholds.yaml. EA2 tiga tingkat (DANGER/WARNING/SAFE), EA3 mengembalikan
aging acceleration factor, EA4 memakai selisih relatif dan menghitung arus sirkulasi,
EA5 biner. Tiap fungsi minimal 3 test: SAFE, DANGER, INSUFFICIENT_DATA.
```

**Kriteria selesai:** fixture naskah IR 16 kA vs Isc 20 kA memberi DANGER;
tidak ada satu pun threshold tertulis di dalam fungsi; `INSUFFICIENT_DATA` tidak pernah
jatuh menjadi SAFE.

---

## Sesi 3 — FMEA Engine dan Data Dummy

```
Bangun backend/engines/fmea_engine.py mengikuti skill fmea-matrix (struktur 4 baris
F-M-E-A, RPN dengan skala AIAG yang ditandai asumsi, klasifikasi hidden/evident,
pemetaan uji dengan reference_note). Lalu bangun backend/data/dummy_generator.py
mengikuti skill dummy-data-generator: 30 unit, 10 tahun, seed 20260929, beta per komponen
sesuai tabel, sensor kanan, dan lima kasus pemicu EA. Simpan _truth.json dan tulis
tests/test_roundtrip.py yang memverifikasi fit_weibull menemukan kembali beta dan eta.
```

**Kriteria selesai:** roundtrip test hijau (parameter ditemukan kembali dalam selang
kepercayaan); kelima `expected_ea_triggers` benar-benar terpicu oleh EA checker.

---

## Sesi 4 — Decision Service dan Dashboard

```
Bangun backend/services/decision_service.py yang memadukan RAM, FMEA, dan EA checks
menjadi EngineeringActionPlan. Engineering Action = Engineering Task + Engineering
Frequency; task tanpa frekuensi masuk unscheduled_tasks dengan alasannya. Urutkan:
EA DANGER dulu, lalu RPN tertinggi, lalu interval terpendek.

Lalu bangun app/streamlit_app.py: kurva reliability Weibull dengan pita kepercayaan,
gauge availability, badge EA1-EA5 (merah/kuning/hijau/abu-abu untuk INSUFFICIENT_DATA),
tabel FMEA empat baris, dan kalender Engineering Actions. Semua label UI bahasa Indonesia.
Setiap angka di layar menampilkan sumbernya saat di-hover.
```

**Kriteria selesai:** aplikasi jalan dengan data dummy; tidak ada angka di layar tanpa
sumber; badge abu-abu muncul untuk data yang kurang, bukan hijau.

---

## Sesi 5 (opsional) — Paket untuk sidang

```
Buat halaman "Metodologi" di aplikasi yang memetakan tiap layar ke bagian naskah
(persamaan 2.1-2.5, struktur FMEA hal. 65, lima EA hal. 6), dan ekspor PDF ringkas
berisi Engineering Action Plan untuk dilampirkan ke Bab IV.
```
