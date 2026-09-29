---
name: ea-safety-checker
description: Gunakan saat membangun atau mengubah lima pemeriksa keselamatan Electrical Accident (EA1 DGA/flash point, EA2 interrupting rating, EA3 kecukupan pendinginan, EA4 impedansi paralel, EA5 vector group) untuk transformator tegangan menengah.
---

# EA Safety Checker

Lima fungsi deterministik di `backend/safety/ea_checker.py`. Deterministik artinya: input yang
sama selalu memberi output yang sama, tidak ada keacakan, tidak ada pemanggilan model bahasa,
tidak ada heuristik. Ini modul keselamatan.

Semua mengembalikan `CheckResult` (lihat `.agents/rules/engineering-standards.md`).

## EA1 — `check_dga_fire_risk(c2h2_ppm, fluid_type, flash_point_c=None)`

- C₂H₂ > ambang kritis → **DANGER**. Ambang dari naskah: 5 ppm (hal. 16).
- Ambang bersifat per jenis cairan. Baca `thresholds.ea1.c2h2_critical[fluid_type]`.
  `fluid_type` ∈ {`mineral`, `natural_ester`, `synthetic_ester`}.
- Kalau `flash_point_c` diberikan dan berada di bawah ambang jenis cairannya → **DANGER**
  terpisah dengan penjelasan sendiri.
- `reference` untuk ambang C₂H₂ adalah `"Dissertation p.16"`, bukan nama standar IEC.
  Naskah mengutip Martin et al. 2023 dan Ahmad et al. 2025, bukan langsung IEC 60599.
  Salah atribusi di sini akan terbaca sebagai kecerobohan ilmiah saat sidang.

## EA2 — `check_breaker_interrupting_capacity(ir_ka, isc_ka)`

Tiga tingkat, bukan dua:

| Kondisi | Status |
|---|---|
| IR < Isc | DANGER |
| Isc ≤ IR < margin × Isc | WARNING (margin cukup tipis) |
| IR ≥ margin × Isc | SAFE |

`margin` dibaca dari `thresholds.ea2.safety_margin` (default 1,2).
Versi lama aturan ini berbunyi "IR < Isc **atau** IR < 1,2·Isc" — itu redundan, karena
kondisi kedua sudah mencakup yang pertama. Jangan ditulis ulang seperti itu.

Fixture test dari naskah hal. 16: IR 16 kA vs Isc 20 kA → DANGER.

Sertakan di `explanation_id` bahwa Isc berubah seiring penambahan kapasitas sistem,
sehingga verifikasi ini perlu diulang secara berkala — inilah yang frekuensinya ditentukan RAM.

## EA3 — `check_cooling_adequacy(cooling_type, load_kva, rated_kva, ambient_temp_c)`

Jangan buat ini sekadar lulus/gagal. Naskah (hal. 16) memberi aturan yang lebih berguna:
**setiap kenaikan 7 °C di atas batas mempercepat penuaan isolasi sekitar 30 %.**

Maka fungsi ini mengembalikan, selain status:
- `hotspot_estimate_c`
- `excess_temp_c` (selisih terhadap batas)
- `aging_acceleration_factor` = 1,30 ^ (excess_temp_c / 7)
- `estimated_life_reduction_pct`

Batas suhu dibaca dari `thresholds.ea3`, dipisah tiga: kenaikan rata-rata winding,
kenaikan hotspot, dan hotspot absolut. Ketiganya tidak sama dan sering tertukar.

Tipe pendinginan yang dikenali: **ONAN, ONAF, OFAF**. Kalau beban melampaui kapasitas
tipe terpasang sementara tipe yang lebih tinggi tersedia, sebutkan transisi yang dianjurkan
di `explanation_id` (naskah hal. 44 memakai contoh ONAN dipakai pada beban tinggi yang
seharusnya OFAF).

## EA4 — `check_parallel_impedance(z_pct_a, z_pct_b, kva_a=None, kva_b=None, ...)`

- Selisih **relatif**: `abs(z_a − z_b) / mean(z_a, z_b)`. Bukan selisih absolut.
  Ambang dari `thresholds.ea4.max_relative_diff_pct` (default 10).
- Hitung dan kembalikan **arus sirkulasi** — naskah hal. 17 menyebutnya sebagai mekanisme
  kerusakan, jadi angkanya harus muncul, bukan cuma vonis.
- Kalau `kva_a`/`kva_b` tersedia, periksa juga rasio kVA (umumnya maksimum 3:1)
  dan laporkan terpisah.
- Status DANGER memblokir rekomendasi sinkronisasi paralel di `decision_service`.

## EA5 — `check_vector_group_compatibility(vector_a, vector_b)`

- Parse notasi vector group: huruf sisi HV (D/Y/Z), huruf sisi LV (d/y/z/n),
  dan angka jam (0–11). Contoh: `Dyn11`.
- Angka jam × 30° = pergeseran fasa. Beda jam ≠ 0 → **DANGER**, paralel dilarang.
- Notasi yang tidak bisa diparse → `INSUFFICIENT_DATA`, bukan menebak.
- Ini satu-satunya EA yang murni biner: tidak ada WARNING. Naskah hal. 17 menyebut kondisi
  ini "dapat berakibat fatal".

## Larangan
- Jangan menambah EA6 atau memecah salah satu EA. Lima EA ini adalah kerangka disertasi.
- Jangan menaruh threshold apa pun di dalam kode fungsi.
- Jangan mengembalikan SAFE saat ada field yang hilang.
