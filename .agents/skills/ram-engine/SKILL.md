---
name: ram-engine
description: Gunakan saat membangun, mengubah, atau memverifikasi perhitungan RAM — MTBF, MTTR, availability, maintainability, reliability eksponensial, Weibull fitting, dan penentuan interval pemeliharaan (Engineering Frequency) untuk transformator tegangan menengah.
---

# RAM Engine

## Kapan skill ini dipakai
Setiap pekerjaan di `backend/engines/ram_engine.py` dan `tests/test_ram.py`.

## Yang dibangun

```python
class RAMEngine:
    def mtbf(self, uptime_hours: float, failures: int) -> float
    def mttr(self, downtime_hours: float, failures: int) -> float
    def availability(self, mtbf: float, mttr: float, mdt: float = 0.0) -> float
    def reliability(self, t: float, mtbf: float) -> float
    def maintainability(self, t: float, mu: float) -> float
    def maintenance_interval(self, t: float, target_reliability: float) -> IntervalResult
    def fit_weibull(self, ttf: list[float], censored: list[float] | None = None) -> WeibullFit
    def engineering_frequency(self, component: str, target_reliability: float) -> Frequency
```

## Urutan pengerjaan

1. Tulis `tests/test_ram.py` lebih dulu, dengan fixture dari
   `.agents/rules/dissertation-facts.md` bagian 2 (busi 250 jam, switchgear 20 kV).
2. Baru implementasikan fungsinya sampai test hijau.
3. Jalankan `pytest tests/test_ram.py -v` dan tunjukkan hasilnya. Jangan mengklaim hijau
   tanpa menjalankannya.

## Aturan khusus

**Interval pemeliharaan.** `maintenance_interval` mengembalikan dua angka sekaligus:
`mtbf_raw` (17,38) dan `interval_months` (18, hasil `math.ceil`). Naskah memakai pembulatan
ke atas, dan pembulatan itu konservatif secara keselamatan. Jangan ganti ke `round()`.

**Weibull fitting.** Data kegagalan trafo hampir selalu tersensor kanan — banyak unit belum
gagal saat pengamatan berhenti. Least-squares biasa akan bias ke bawah dan membuat trafo
terlihat lebih rentan dari kenyataan. Pakai maximum likelihood dengan dukungan right-censored
data. Kalau `scipy.stats.weibull_min.fit` dipakai, tangani data tersensor lewat likelihood
kustom, dan catat di docstring kalau penanganan sensor belum diimplementasikan.

Wajib kembalikan interval kepercayaan untuk β dan η. Dengan data dummy, β tanpa selang
kepercayaan akan dibaca sebagai fakta oleh penguji, padahal ia estimasi.

**Validasi asumsi eksponensial.** Kalau hasil fit memberi β di luar 0,9–1,1, engine memberi
peringatan bahwa asumsi λ konstan (persamaan 2.1) tidak berlaku untuk komponen tersebut,
dan menganjurkan memakai jalur Weibull.

**Pembagian nol.** `failures = 0` bukan error — artinya belum ada kegagalan tercatat.
Kembalikan `INSUFFICIENT_DATA` dengan penjelasan, bukan `ZeroDivisionError` dan bukan infinity.

**Satuan.** Naskah mencampur jam (contoh busi) dan bulan (contoh switchgear). Engine bekerja
dalam satu satuan internal — **jam** — dan konversi dilakukan di lapisan tepi. Setiap fungsi
publik menerima parameter `unit: Literal["hours","months","years"]`.
1 bulan = 730 jam. Konstanta ini masuk `thresholds.yaml`, bukan hardcode.

## Larangan
- Jangan menambahkan distribusi lain (lognormal, gamma) tanpa diminta. Naskah hanya menyebut
  eksponensial dan Weibull.
- Jangan membuat "smart default" untuk target reliability. Itu input pengguna.
