# Workflow Aplikasi: Sison & Sistem Kamera

Berikut adalah alur sistem (Sison & Sistem Kamera) berdasarkan spesifikasi yang diberikan. 

```mermaid
flowchart TD
    subgraph Sison [Sison - Tahap Awal]
        Start([Operator Scan Barcode Kanban Int & Ext]) --> CheckMatch{p_no_ext == p_no_int ?}
        
        CheckMatch -- Tidak --> LockUISison[UI Input Sison Terkunci]
        LockUISison --> SupervisorUnlock[Pengawas Input Unlock]
        SupervisorUnlock --> Start
        
        CheckMatch -- Ya --> SaveData[Simpan Data Kanban]
        %% ponytail: data = id_kanban, lot, p_no, unique_no, p_name, qty
        SaveData --> TampilHarigami[Tampil Harigami]
        TampilHarigami --> LockUIMenunggu[UI Mengunci]
        LockUIMenunggu --> SendAPICamera[Kirim API ke Sistem Kamera]
    end
    
    subgraph Kamera [Sistem Kamera Python]
        SendAPICamera --> InitSistem[Load best.pt & Tarik Aturan Resep dari DB]
        InitSistem --> ModelReady[Sistem Siap Inspeksi]
        
        ModelReady --> LetakPart[Operator Meletakkan Part]
        LetakPart --> Deteksi[YOLO Deteksi Realtime]
        
        Deteksi --> Evaluasi{Sesuai Aturan Sisi Aktif?}
        
        %% Flow NG
        Evaluasi -- NG / Anomali --> Sirene[Sirene / UI Merah Muncul]
        Sirene --> InputPIN[Pengawas Input PIN]
        InputPIN --> ValidasiPIN{PIN Benar?}
        ValidasiPIN -- Salah --> InputPIN
        ValidasiPIN -- Benar --> LetakPart
        
        %% Flow Sisi OK (State Machine)
        Evaluasi -- OK --> CekSisi{Semua Sisi Selesai?}
        CekSisi -- Belum --> PutarPart[Instruksi: Putar Part]
        PutarPart --> Deteksi
        
        %% Flow Part Lulus Total
        CekSisi -- Sudah --> Hitung[Kurangi Qty: qty = qty - 1]
        Hitung --> CekTarget{Target Qty Terpenuhi?}
        CekTarget -- Belum --> LetakPart
        
        CekTarget -- Ya --> SimpanLog[Simpan Histori Log ke DB]
        SimpanLog --> SendAPISison[Kirim Callback API JSON ke Sison]
        %% ponytail: status '0=GAGAL', '1=SUKSES', '2=PROSES'
    end
    
    subgraph Sison_Akhir [Sison - Tahap Akhir]
        SendAPISison --> UnlockSison[Sison Menerima API & Unlock UI]
        UnlockSison --> End([Operator Dapat Scan Kanban Berikutnya])
    end
```

## Spesifikasi Data API
### 1. Sison -> Kamera
- **Format**: JSON
- **Data**: `id_trans`, `lot`, `p_no`, `unique_no`, `p_name`, `qty`

### 2. Kamera -> Sison (Callback)
- **Format**: JSON
- **Data**: `id_trans`, `status`
- **Status Value**: `0` (GAGAL), `1` (SUKSES), `2` (PROSES)
