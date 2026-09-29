---
trigger: always_on
description: Angka, formula, dan definisi yang diambil langsung dari naskah disertasi. Satu-satunya sumber kebenaran numerik.
---

# Fakta Terverifikasi dari Naskah Disertasi

Sumber: `Prabowo_Soetadji_Proposal_BabI-III_Rev3.pdf`. Nomor halaman adalah halaman naskah.

**Aturan pemakaian:** kalau sebuah angka tidak ada di file ini, agent tidak boleh memakainya.
Hentikan pekerjaan dan minta klarifikasi.

## 1. Formula RAM

| Persamaan | Rumus | Hal. |
|---|---|---|
| (2.1) | R(t) = e^(−λt) = e^(−t/MTBF), dengan MTBF = 1/λ | 23 |
| (2.2) | MTBF = t / ln[1 / R(t)] | 23 |
| (2.3) | A = MTBF / (MTBF + MTTR); bentuk diperluas A = MTBF / (MTBF + MTTR + MDT) | 24 |
| (2.4) | M(t) = 1 − e^(−μt), μ = restoration rate | 24 |
| (2.5) | Weibull: R(t) = e^(−(t/η)^β) | 24 |

Interpretasi β: β<1 infant mortality, β=1 random failure, β>1 wear-out.
MTBF Weibull = η · Γ(1 + 1/β).

Persamaan (2.1) hanya valid pada fase random failure kurva bathtub. Engine harus menolak
memakai model eksponensial kalau hasil fitting Weibull memberi β di luar rentang 0,9–1,1,
dan memberi peringatan bahwa asumsi λ konstan tidak berlaku.

Availability > 99% umumnya disyaratkan untuk trafo yang terintegrasi energi terbarukan (hal. 24).

## 2. Test case wajib (fixture unit test)

**Contoh 1 — Busi (hal. 27–28).** MTBF = 250 jam.
- R(50) = 81,87 %
- R(130) = 59,45 %
- F(130) = 1 − R = 40,55 %

**Contoh 2 — MV Switchgear 20 kV (hal. 28–29).** Target R = 75 % pada t = 5 bulan,
durasi inspection & testing 1 hari = 0,033 bulan.
- MTBF = 5 / ln(1/0,75) = 5 / 0,2877 = **17,38 bulan**
- Naskah membulatkan ke atas menjadi **18 bulan (1,5 tahun)** sebagai interval pemeliharaan
- A = 18 / (18 + 0,033) = **99,63 %**

Engine mengembalikan 17,38 sebagai `mtbf_raw` dan 18 sebagai `maintenance_interval_months`
(pembulatan ke atas, konservatif). Keduanya wajib muncul di output, jangan salah satu saja.
Toleransi test: ±0,01.

## 3. Lima Electrical Accidents (hal. 6 dan 46)

| Kode | Kecelakaan |
|---|---|
| EA 1 | Kebakaran akibat flash point cairan pendingin yang rendah |
| EA 2 | Ledakan MV circuit breaker/fuse akibat IR < Isc |
| EA 3 | Kebakaran akibat pemilihan tipe pendinginan yang tidak tepat |
| EA 4 | Kerusakan akibat operasi paralel: ketidaksesuaian impedansi (%Z berbeda) |
| EA 5 | Kerusakan akibat operasi paralel: ketidaksesuaian vector group |

Urutan ini mengikat. Jangan diubah, jangan ditambah EA baru.

## 4. Angka pendukung tiap EA

**EA 1 (hal. 16).** DGA dengan kadar asetilena (C₂H₂) melebihi **5 ppm** menandai kondisi rawan
kebakaran, akurasi ~95%, mencegah 25–30% potensi insiden. Sumber naskah: Martin et al. 2023;
Ahmad et al. 2025. → `source: "Dissertation p.16"`, **bukan** IEC.
Green power transformer didefinisikan lewat pemakaian **synthetic ester** yang flash point-nya
tinggi dan biodegradable (hal. 6).

**EA 2 (hal. 16).** Contoh eksplisit naskah: IR 16 kA versus Isc 20 kA → kegagalan katastrofik.
Gaya elektromagnetik >100 kN/m, energi panas >50 MJ, arc flash >40 cal/cm².
Berkontribusi 10–15% kegagalan proteksi MV; 0,01–0,03% insiden ledakan trafo global.
Catatan naskah: Isc berubah seiring penambahan kapasitas sistem, jadi verifikasi IR vs Isc
harus punya frekuensi berulang (ini yang ditentukan RAM).

**EA 3 (hal. 16 dan 44).** Pemilihan pendinginan salah → hotspot melampaui batas IEEE C57.91.
Aturan kunci naskah: **setiap kenaikan 7 °C di atas batas mempercepat penuaan isolasi ~30 %**.
Cooling tidak memadai menyumbang 15–20% kegagalan power transformer. Kesalahan aplikasi
(mis. ONAN dipakai pada beban tinggi yang butuh OFAF) menyumbang ~15% kegagalan trafo ramah
lingkungan, padam 3–6 jam, kerugian USD 30.000–80.000 per insiden.
→ Implementasikan sebagai **aging acceleration factor**, bukan sekadar batas lulus/gagal.

**EA 4 (hal. 17).** %Z berbeda → arus sirkulasi, pembagian beban tidak merata, overheating,
penuaan isolasi dipercepat.

**EA 5 (hal. 17).** Vector group tidak kompatibel → operasi di luar fase, risiko short circuit,
ketidakstabilan tegangan, ketidakseimbangan beban. Terjadi pada 10–15% insiden operasi paralel.

## 5. Struktur FMEA empat baris (hal. 65)

- **Baris F** — Components & Function: komponen kritis dan fungsi nominalnya; serta
  Functional Failure, yaitu kondisi ketika komponen gagal memenuhi fungsinya.
- **Baris M** — Failure Mode: mekanisme fisik/kimia penyebab kegagalan fungsional
  (mis. degradasi isolasi akibat oksidasi termal, kegagalan belitan akibat short-circuit).
- **Baris E** — Failure Effect: dampak kegagalan.
- **Baris A** — Analysis: klasifikasi Hidden vs Evident, karakteristik kegagalan,
  dan Engineering Tasks.

## 6. Pola kegagalan (hal. 23, Gulati 2013)

Age-related <20% total kegagalan: 4% bathtub, 2% langsung terkait umur, 5% fatigue.
Sisanya >80% acak: 14% random failure, 68% infant mortality.
Konsekuensi desain: **jangan asumsikan wear-out sebagai default.** Prior β untuk data dummy
harus condong ke β ≈ 1 dan β < 1.

## 7. Data dan metode (hal. 61, 63, 65)

- Data sekunder dari Pertamina LNG dan utilitas lain, periode operasi ± **10 tahun**
  (rekomendasi minimum statistik RAM).
- Field yang dikumpulkan: jenis kegagalan, komponen yang gagal, downtime, TTF (Time To Fail),
  kondisi lingkungan saat kegagalan.
- Konteks tropis Indonesia: **kelembaban >80% RH** mempercepat oksidasi minyak isolasi dan
  degradasi sistem isolasi. Ini variabel tambahan yang jadi kebaruan penelitian.
- Model hibrida: RAM → Engineering Frequency, FMEA → Engineering Tasks,
  gabungan → **Engineering Actions**.
- Penelitian berjalan Juli 2026 – April 2028. **Data aktual belum ada.**
  Fase sekarang memakai data dummy.

## 8. Catatan koreksi yang belum disetujui penulis

Tabel 3.1 Instrumen Penelitian (hal. 63) merujuk Insulation Resistance ke IEC 60060 / IEEE 43,
dan DAR ke IEC 60270. Untuk transformator, rujukan yang lazim adalah **IEEE C57.152**
(IR/PI/DAR/tan δ pada trafo); IEEE 43 adalah standar untuk mesin berputar dan IEC 60270
adalah standar partial discharge.

**Sampai penulis memutuskan, aplikasi tetap memakai rujukan sesuai naskah**, tetapi setiap
entri di `thresholds.yaml` membawa `note:` yang mencatat alternatifnya. Jangan diam-diam
mengganti. Jangan pula diam-diam mengikuti naskah tanpa mencatat.
