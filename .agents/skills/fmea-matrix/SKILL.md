---
name: fmea-matrix
description: Gunakan saat membangun matriks FMEA empat baris (F-M-E-A), perhitungan RPN, klasifikasi hidden vs evident, pemetaan uji kelistrikan, dan penggabungan Engineering Task dengan Engineering Frequency menjadi Engineering Actions.
---

# FMEA Matrix Engine

## Struktur empat baris (naskah hal. 65) — ikat, jangan diubah

- **F** — Components & Function: komponen kritis, fungsi nominalnya, dan Functional Failure.
- **M** — Failure Mode: mekanisme fisik/kimia penyebabnya.
- **E** — Failure Effect: dampaknya.
- **A** — Analysis: klasifikasi Hidden/Evident, karakteristik kegagalan, Engineering Tasks.

Skema Pydantic harus mencerminkan empat baris ini secara eksplisit, bukan satu tabel datar.
Penguji akan mencocokkan layar aplikasi dengan struktur di Bab III.

## Enam komponen kritis (naskah hal. 63)

OLTC/tap changer, winding, core, bushing, cooling system, sistem isolasi.
Bertanggung jawab atas >85% kegagalan trafo tegangan menengah. Jangan tambah, jangan kurang.

## RPN

`RPN = Severity × Occurrence × Detection`, masing-masing 1–10, rentang hasil 1–1000.

Naskah belum menetapkan skala rinci untuk ketiga variabel. Karena itu:
- Pakai skala AIAG 1–10 standar sebagai **asumsi**, taruh di `config/rpn_scales.yaml`.
- Tandai jelas di UI dan di docstring bahwa skala ini asumsi implementasi, belum dari naskah.
- Siapkan agar skala bisa diganti satu file ketika penulis menetapkannya di Bab IV.

Jangan diam-diam memakai skala apa pun tanpa label asumsi.

## Hidden vs Evident

- **Evident**: kegagalan yang langsung terlihat operator saat terjadi.
- **Hidden**: baru ketahuan lewat pengujian atau saat ada permintaan fungsi kedua.

Kegagalan Hidden **wajib** punya Engineering Task berupa pengujian terjadwal — itu inti
argumen metodologisnya. Kalau sebuah failure mode diklasifikasi Hidden tapi tidak punya
task pengujian, engine menandainya sebagai inkonsistensi.

## Pemetaan uji untuk failure mode Hidden

Ikuti Tabel 3.1 naskah, dan bawa catatan koreksinya:

| Gejala | Uji | Rujukan naskah | Catatan |
|---|---|---|---|
| Degradasi isolasi | Insulation Resistance (Megger) | IEC 60060 / IEEE 43 | IEEE 43 adalah standar mesin berputar; untuk trafo lazimnya IEEE C57.152 |
| Kelembaban/polarisasi | Polarization Index (PI) | IEEE 43-2013 | idem |
| Kondisi isolasi | DAR | IEC 60270 | IEC 60270 adalah standar partial discharge, bukan DAR |
| Breakdown termal | Tan Delta | — | untuk cairan IEC 60247; untuk winding IEEE C57.152 |
| Latent discharge | Partial Discharge (pC) | IEC 60270 | sesuai |
| Hotspot | Thermovision | — | — |
| Degradasi gas internal | DGA | IEC 60599 / IEEE C57.104 | keduanya disusun untuk minyak mineral; untuk ester lihat IEEE C57.155 |

**Perilaku wajib:** tampilkan rujukan sesuai naskah sebagai nilai utama, dan simpan catatan
koreksi di field `reference_note`. Jangan mengganti diam-diam, jangan pula menyembunyikan
catatannya. Penulis yang memutuskan.

## Engineering Actions

```
Engineering Action = Engineering Task (FMEA, baris A) + Engineering Frequency (RAM)
```

Penggabungan dilakukan per komponen. Satu Engineering Task tanpa frekuensi bukan Engineering
Action dan tidak boleh muncul di rencana akhir — kembalikan sebagai `unscheduled_tasks`
dengan alasannya (biasanya data TTF komponen itu belum cukup untuk menghitung MTBF).

Prioritas urutan rencana: status EA DANGER lebih dulu, lalu RPN tertinggi, lalu interval
terpendek.
