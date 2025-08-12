# pages/2_Input_Pemeriksaan.py

import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import date, datetime
from dateutil.relativedelta import relativedelta #11082025 untuk tampilan tahun..bulan

# --- KONEKSI & KEAMANAN ---
st.set_page_config(page_title="Input Pemeriksaan", page_icon="🗓️", layout="wide")

# if not st.session_state.get("authenticated", False):
#     st.error("🔒 Anda harus login untuk mengakses halaman ini.")
#     st.stop()

# --- KONEKSI & KEAMANAN ---
if not st.session_state.get("authenticated", False):
    st.error("🔒 Anda harus login untuk mengakses halaman ini.")
    st.stop()

# Ambil koneksi super-admin dari session state yang sudah dibuat saat login
supabase = st.session_state.get('supabase_client')
if not supabase:
    st.error("Koneksi Supabase tidak ditemukan. Silakan login kembali.")
    st.stop()


## <<< PERUBAHAN: Fungsi bantuan untuk menghitung umur
def calculate_age(birth_date, reference_date):
    """
    Menghitung umur dalam tahun dan bulan.
    Mengembalikan tuple (tahun, bulan), atau None jika tanggal lahir tidak valid.
    """
    if not birth_date or not isinstance(birth_date, str):
        return None
    try:
        birth_date_obj = datetime.strptime(birth_date, '%Y-%m-%d').date()
    except ValueError:
        return None

    # Hitung selisih waktu menggunakan relativedelta
    delta = relativedelta(reference_date, birth_date_obj)
    
    return (delta.years, delta.months)

# --- FUNGSI HALAMAN UTAMA ---
def page_input_pemeriksaan():
    st.header("🗓️ Input Kehadiran & Pemeriksaan")
    if not supabase: return

    try:
        response = supabase.table("warga").select("id, nik, nama_lengkap, rt, blok, tanggal_lahir").execute()
        if not response.data:
            st.warning("Belum ada data warga. Silakan tambahkan data warga terlebih dahulu.")
            return

        df_warga = pd.DataFrame(response.data)
        df_warga['display_name'] = df_warga['nama_lengkap'] + " (RT-" + df_warga['rt'].astype(str) + ", BLOK-" + df_warga['blok'].astype(str) + ")"
        
        # === LANGKAH 1: Widget pemilihan ditaruh DI LUAR FORM ===
        tanggal_pemeriksaan = st.date_input("Tanggal Posyandu/Pemeriksaan", value=date.today())
        
        # Pastikan tidak ada duplikat pada display_name untuk menghindari error
        options_warga = df_warga['display_name'].unique().tolist()
        selected_display_name = st.selectbox("Pilih Warga yang Hadir:", options=options_warga)
        
        # Ambil data lengkap warga yang dipilih
        selected_warga_data = df_warga[df_warga['display_name'] == selected_display_name].iloc[0]
        
        st.divider()

        # === LANGKAH 2: Lakukan pengecekan dan tampilkan info SEBELUM FORM ===
        #umur = calculate_age(selected_warga_data['tanggal_lahir'], tanggal_pemeriksaan)
        # Sekarang 'age_tuple' akan berisi (tahun, bulan), contoh: (1, 3) atau (5, 11)
        age_tuple = calculate_age(selected_warga_data['tanggal_lahir'], tanggal_pemeriksaan)

        # ---- Untuk Debugging (bisa dihapus nanti) ----
        st.info(f"Nama: {selected_display_name}, Tanggal Lahir: {selected_warga_data['tanggal_lahir']}, Umur: {age_tuple[0]} Tahun {age_tuple[1]} Bulan")
        #st.write(f"1. Nama Dipilih: `{selected_display_name}`")
        #st.write(f"2. Tanggal Lahir dari Database: `{selected_warga_data['tanggal_lahir']}`")
        #st.write(f"3. Umur Dihitung: `{umur}` tahun")
        # ---- Akhir Debugging ----

        if age_tuple is None:
            st.error(f"Data tanggal lahir untuk '{selected_display_name}' tidak ada atau formatnya salah di database. Mohon perbarui data warga.")
            return
        # Ekstrak tahun dan bulan untuk logika dan tampilan
        tahun, bulan = age_tuple
        umur_dalam_tahun = tahun # Tetap gunakan ini untuk logika if-else

        # Format string umur untuk ditampilkan di UI
        umur_display_string = f"{tahun} Tahun {bulan} Bulan"

        # === LANGKAH 3: FORM HANYA BERISI INPUT DATA & TOMBOL SUBMIT ===
        with st.form("pemeriksaan_form", clear_on_submit=True):
            st.write(f"**Silakan Masukkan Hasil Pemeriksaan**")# `{selected_display_name}`**")
            
            # Inisialisasi variabel
            tensi_sistolik = tensi_diastolik = gula_darah = kolesterol = 0
            berat_badan_kg = tinggi_badan_cm = lingkar_perut_cm = lingkar_lengan_cm = lingkar_kepala_cm = 0.0

            if umur_dalam_tahun < 5:
                col1, col2 = st.columns(2)
                with col1:
                    berat_badan_kg = st.number_input("Berat Badan (kg)", min_value=0.0, step=0.1, format="%.2f")
                    lingkar_lengan_cm = st.number_input("Lingkar Lengan (cm)", min_value=0.0, step=0.5, format="%.1f")
                with col2:
                    tinggi_badan_cm = st.number_input("Tinggi Badan (cm)", min_value=0.0, step=0.1, format="%.2f")
                    lingkar_kepala_cm = st.number_input("Lingkar Kepala (cm)", min_value=0.0, step=0.5, format="%.1f")
            elif umur_dalam_tahun < 15:
                col1, col2 = st.columns(2)
                with col1:
                    berat_badan_kg = st.number_input("Berat Badan (kg)", min_value=0.0, step=0.1, format="%.2f")
                    lingkar_lengan_cm = st.number_input("Lingkar Lengan (cm)", min_value=0.0, step=0.5, format="%.1f")
                with col2:
                    tinggi_badan_cm = st.number_input("Tinggi Badan (cm)", min_value=0.0, step=0.1, format="%.2f")
                    #lingkar_kepala_cm = st.number_input("Lingkar Kepala (cm)", min_value=0.0, step=0.5, format="%.1f")
            else:
                col1, col2 = st.columns(2)
                with col1:
                    tensi_sistolik = st.number_input("Tensi Sistolik (mmHg)", min_value=0, step=1)
                    berat_badan_kg = st.number_input("Berat Badan (kg)", min_value=0.0, step=0.1, format="%.2f")
                    lingkar_perut_cm = st.number_input("Lingkar Perut (cm)", min_value=0.0, step=0.5, format="%.1f")
                    gula_darah = st.number_input("Gula Darah (mg/dL)", min_value=0, step=1)
                with col2:
                    tensi_diastolik = st.number_input("Tensi Diastolik (mmHg)", min_value=0, step=1)
                    tinggi_badan_cm = st.number_input("Tinggi Badan (cm)", min_value=0.0, step=0.1, format="%.2f")
                    lingkar_lengan_cm = st.number_input("Lingkar Lengan (cm)", min_value=0.0, step=0.5, format="%.1f")
                    kolesterol = st.number_input("Kolesterol (mg/dL)", min_value=0, step=1)
            
            catatan = st.text_area("Catatan Tambahan (Opsional)")

            submitted = st.form_submit_button("Simpan Hasil Pemeriksaan")
            
            if submitted:
                warga_id = selected_warga_data['id'] # Variabel ini aman karena didefinisikan di luar form
                
                data_to_insert = {
                    "tanggal_pemeriksaan": str(tanggal_pemeriksaan), "warga_id": warga_id,
                    "tensi_sistolik": int(tensi_sistolik), "tensi_diastolik": int(tensi_diastolik),
                    "berat_badan_kg": berat_badan_kg, "tinggi_badan_cm": tinggi_badan_cm,
                    "lingkar_perut_cm": lingkar_perut_cm, "lingkar_lengan_cm": lingkar_lengan_cm, 
                    "gula_darah": int(gula_darah), "kolesterol": int(kolesterol), 
                    "lingkar_kepala_cm": lingkar_kepala_cm,
                    "catatan": catatan
                }
                try:
                    supabase.table("pemeriksaan").insert(data_to_insert).execute()
                    st.success(f"Data pemeriksaan untuk '{selected_display_name}' berhasil disimpan.")
                except Exception as e:
                    st.error(f"Gagal menyimpan data pemeriksaan: {e}")

    except Exception as e:
        st.error(f"Terjadi kesalahan saat memuat data: {e}")

# --- JALANKAN HALAMAN ---
page_input_pemeriksaan()