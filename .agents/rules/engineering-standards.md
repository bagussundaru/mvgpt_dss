---
trigger: always_on
description: Standar rekayasa kode untuk proyek ini — pemisahan lapisan, penanganan error, larangan hardcode, dan disiplin testing.
---

# Standar Rekayasa

## Larangan hardcode

Setiap angka yang punya makna fisik atau normatif dibaca dari `config/thresholds.yaml` lewat
satu loader tunggal (`backend/config_loader.py`). Tidak ada `if c2h2 > 5:` di dalam kode.
Yang benar: `if c2h2 > thresholds.ea1.c2h2_critical.value:`.

Angka yang boleh muncul langsung di kode hanya konstanta matematika murni
(0, 1, 2, 100 untuk persen) dan indeks array.

## Bentuk hasil yang seragam

Setiap fungsi EA checker dan setiap engine mengembalikan objek Pydantic dengan bentuk sama:

```python
class CheckResult(BaseModel):
    code: str                  # "EA1".."EA5"
    status: Literal["SAFE", "WARNING", "DANGER", "INSUFFICIENT_DATA"]
    measured: dict             # nilai input yang dipakai, beserta satuannya
    threshold: dict            # nilai pembanding yang dipakai
    explanation_id: str        # penjelasan bahasa Indonesia untuk pengguna
    reference: str             # "IEC 62271-100" atau "Dissertation p.16"
    missing_fields: list[str] = []
```

`explanation_id` harus menyebut angkanya, bukan hanya vonisnya.
Buruk: "Kapasitas breaker tidak memadai."
Baik: "IR 16 kA lebih kecil dari Isc 20 kA. Breaker berisiko meledak saat memutus gangguan."

## Penanganan data kurang

Jangan melempar exception untuk data yang hilang, dan jangan mengisi default.
Kembalikan `status="INSUFFICIENT_DATA"` dengan `missing_fields` terisi. UI menampilkannya
sebagai kartu abu-abu, bukan hijau. Ini penting: hijau palsu pada aplikasi keselamatan
lebih berbahaya daripada tidak ada jawaban.

## Pemisahan lapisan

`backend/engines/` dan `backend/safety/` adalah pure functions: tidak ada baca file,
tidak ada panggilan jaringan, tidak ada import Streamlit, tidak ada `print`.
Konfigurasi masuk lewat argumen atau lewat objek threshold yang di-inject, bukan dibaca
sendiri di dalam fungsi. Konsekuensinya seluruh mesin hitung bisa diuji tanpa menyalakan UI,
dan UI bisa diganti tanpa menyentuh mesin hitung.

## Testing

- Setiap fungsi publik punya test.
- Fixture numerik diambil dari `.agents/rules/dissertation-facts.md` bagian 2.
- Perbandingan float memakai `pytest.approx(..., abs=0.01)`, tidak pernah `==`.
- Setiap EA checker punya minimal tiga test: kasus SAFE, kasus DANGER, dan kasus
  INSUFFICIENT_DATA.
- `pytest` harus hijau sebelum pekerjaan dianggap selesai. Jalankan, jangan diasumsikan.

## Gaya

- Type hint penuh. Docstring memuat rumus dan rujukan halaman naskah.
- Nama variabel memakai satuan: `mtbf_months`, `isc_ka`, `ambient_temp_c`, `z_pct`.
  Satuan yang tersamar adalah sumber bug paling mahal di domain ini.
- Fungsi maksimal ~40 baris. Kalau lebih panjang, ada tanggung jawab yang harus dipisah.
