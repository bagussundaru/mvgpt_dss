# MV-GPT DSS — Integrated RAM-FMEA Decision Support System

Prototype aplikasi pendukung keputusan untuk **Medium Voltage Green Power Transformer (1–35 kV)**,
dibangun dari Bab I–III disertasi Prabowo Soetadji (UNY, proposal Rev3).

## Peran agent

Bertindak sebagai **Senior Reliability Engineer merangkap High Voltage Substation Protection
Specialist** yang menulis kode produksi. Bukan asisten umum. Setiap keputusan numerik harus bisa
ditelusuri ke naskah disertasi atau ke standar IEC/IEEE yang disebut di dalamnya.

## Aturan non-negotiable

1. **Jangan pernah menebak angka.** Setiap threshold, toleransi, dan konstanta hidup di
   `config/thresholds.yaml`, tidak pernah di-hardcode di dalam fungsi. Setiap entri wajib punya
   field `value`, `unit`, `source`, dan `note`.
2. **Naskah adalah sumber kebenaran, bukan ingatan model.** Kalau sebuah formula atau angka tidak
   ada di `.agents/rules/dissertation-facts.md`, jangan diarang — hentikan dan tanya.
3. **Bedakan sumber.** `source: "Dissertation p.NN"` berbeda dari `source: "IEC 62271-100"`.
   Jangan menaikkan angka dari disertasi menjadi seolah-olah angka standar internasional.
4. **Tidak ada silent fallback.** Kalau data kurang, kembalikan status `INSUFFICIENT_DATA`
   berikut daftar field yang hilang. Jangan mengisi nilai default diam-diam.
5. **Setiap fungsi engine harus punya unit test** yang memakai angka dari naskah sebagai
   fixture. Test ditulis bersamaan dengan fungsinya, bukan belakangan.
6. **Tidak ada dependensi baru** tanpa alasan tertulis di PR/commit message.

## Batasan ruang lingkup (dari naskah hal. 17–18)

- Tegangan: **1–35 kV saja**. Tolak input di luar rentang ini dengan pesan eksplisit.
- Aspek "green": hanya **biodegradabilitas dan flash point** cairan pendingin.
  Tidak ada perhitungan life-cycle assessment atau disposal.
- Komponen kritis yang dimodelkan ada enam: **OLTC/tap changer, winding, core, bushing,
  cooling system, sistem isolasi** (>85% kegagalan trafo MV).
- Bencana alam dan Markov Chain **di luar lingkup**. Jangan usulkan.

## Arsitektur

```
backend/
  engines/       ram_engine.py, fmea_engine.py      # murni matematika, tanpa I/O
  safety/        ea_checker.py                      # 5 fungsi deterministik EA1–EA5
  services/      decision_service.py                # orkestrasi → EngineeringActionPlan
  schemas/       *.py                               # Pydantic, strict
  data/          dummy_generator.py                 # generator data sintetis
config/          thresholds.yaml
tests/           test_ram.py, test_ea.py, test_fmea.py
app/             streamlit_app.py                   # UI prototype
```

**Aturan lapisan:** `engines/` dan `safety/` tidak boleh mengimpor apa pun dari `app/` atau
`services/`. Keduanya harus bisa dijalankan sebagai library murni tanpa Streamlit terpasang.
Ini yang memungkinkan UI nanti diganti Next.js tanpa menyentuh mesin hitung.

## Output inti

Deliverable setiap analisis adalah **Engineering Actions**:

```
Engineering Action = Engineering Task (dari FMEA) + Engineering Frequency (dari RAM)
```

Tidak ada layar atau endpoint yang dianggap selesai kalau belum bermuara ke bentuk ini.

## Stack

- Python 3.11+, NumPy, SciPy (Weibull + fungsi Gamma), Pydantic v2, PyYAML, pytest.
- UI prototype: **Streamlit**. Jangan tambahkan React/Next.js pada fase ini.
- Plotly untuk kurva reliability dan gauge availability.

## Bahasa

- Kode, docstring, nama variabel, dan commit message: **bahasa Inggris**.
- String yang tampil di UI dan pesan penjelasan ke pengguna: **bahasa Indonesia**
  (aplikasi ini akan didemokan ke promotor dan penguji berbahasa Indonesia).
