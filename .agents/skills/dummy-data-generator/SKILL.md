---
name: dummy-data-generator
description: Gunakan saat membuat atau mengubah data sintetis untuk prototipe — riwayat kegagalan transformator, TTF, downtime, nameplate, hasil DGA, dan data lingkungan tropis — agar hasil analisis bisa diverifikasi balik terhadap parameter yang diketahui.
---

# Dummy Data Generator

Fase ini memakai data dummy atas permintaan penulis disertasi. Data aktual menyusul.

## Prinsip yang menentukan segalanya

**Generate dari parameter yang diketahui, lalu verifikasi bahwa engine menemukannya kembali.**

Data acak murni membuat angka di dashboard tidak bermakna dan tidak bisa dipertanggungjawabkan
saat didemokan ke promotor. Kalau TTF dibangkitkan dari Weibull dengan β=1,8 dan η=42.000 jam,
maka `fit_weibull` harus mengembalikan β dan η mendekati itu. Inilah yang membuktikan mesin
hitungnya benar — dan inilah demo yang meyakinkan di depan penguji.

Setiap dataset yang dihasilkan disimpan bersama file `*_truth.json` berisi parameter
pembangkitnya. `tests/test_roundtrip.py` memverifikasi recovery parameter dalam toleransi
selang kepercayaan.

## Parameter default

- **30 unit** transformator, **10 tahun** riwayat operasi (naskah hal. 65: periode ±10 tahun
  adalah rekomendasi minimum statistik RAM).
- Rentang tegangan **1–35 kV** saja.
- Seed acak **tetap dan tercatat** (`--seed 20260929`). Dataset harus reproducible;
  demo yang angkanya berubah tiap dijalankan tidak bisa dipertahankan.

## Distribusi β per komponen

Naskah hal. 23 menegaskan >80% kegagalan bersifat acak dan hanya <20% terkait umur
(68% infant mortality, 14% random). Data dummy harus mencerminkan itu, bukan membuat
semua komponen tampak wear-out:

| Komponen | β | Alasan |
|---|---|---|
| Winding | 1,8 | wear-out, kelelahan termal-mekanis |
| Sistem isolasi | 2,2 | penuaan jelas terkait umur |
| OLTC / tap changer | 1,4 | keausan mekanis bertahap |
| Bushing | 0,8 | infant mortality, cacat manufaktur/pemasangan |
| Cooling system | 1,0 | random failure |
| Core | 0,9 | infant mortality |

Sensor kanan **wajib ada**: sebagian unit belum gagal sampai akhir jendela pengamatan.
Tanpa itu, generator menghasilkan data yang lebih mudah daripada kenyataan dan menyembunyikan
kelemahan fitting.

## Konteks tropis

Naskah hal. 61 menyebut kelembaban >80% RH mempercepat oksidasi minyak isolasi — ini bagian
dari kebaruan penelitian. Generator memproduksi RH bulanan 70–95% dengan pola musiman
Indonesia, dan menaikkan laju kegagalan komponen isolasi pada bulan-bulan RH tinggi.

## Data per unit

Nameplate: kVA, tegangan primer/sekunder, %Z, vector group, tipe pendinginan, jenis cairan.
Sengaja sisipkan kasus yang memicu tiap EA, supaya dashboard punya sesuatu untuk ditampilkan:
- satu pasang unit dengan selisih %Z > 10% → EA4
- satu pasang dengan vector group berbeda (Dyn11 vs Dyn1) → EA5
- satu unit dengan IR 16 kA dan Isc 20 kA → EA2, persis contoh naskah hal. 16
- satu unit dengan C₂H₂ 7 ppm → EA1
- satu unit ONAN pada beban 115% → EA3

Catat kasus-kasus ini di `_truth.json` sebagai `expected_ea_triggers`, dan uji bahwa
EA checker benar-benar memicunya.

## Larangan
- Jangan pakai nama perusahaan nyata (Pertamina LNG dan lainnya) di data dummy.
  Pakai `UTIL-A`, `UTIL-B`. Data aktual tunduk NDA (naskah hal. 65).
- Jangan menghasilkan angka di luar batas fisik yang masuk akal hanya demi variasi.
