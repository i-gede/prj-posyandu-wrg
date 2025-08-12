# pages/2_Input_Pemeriksaan.py

import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import date, datetime

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
    """Menghitung umur dalam tahun."""
    if birth_date is None:
        return 0
    # Mengonversi string tanggal lahir ke objek date
    try:
        birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        # Jika format salah atau None, anggap sebagai anak-anak untuk keamanan data
        return 0 
    
    age = reference_date.year - birth_date.year - ((reference_date.month, reference_date.day) < (birth_date.month, birth_date.day))
    return age

# --- FUNGSI HALAMAN UTAMA ---
def page_input_pemeriksaan():
    st.header("🗓️ Input Kehadiran & Pemeriksaan")
    if not supabase: return

    try:
        response = supabase.table("warga").select("id, nik, nama_lengkap, rt, blok, tanggal_lahir").execute()#11082025 nambah field tanggal_lahir
        if not response.data:
            st.warning("Belum ada data warga. Silakan tambahkan data warga terlebih dahulu.")
            return

        df_warga = pd.DataFrame(response.data)
        df_warga['display_name'] = df_warga['nama_lengkap'] + " (RT-" + df_warga['rt'].astype(str) + ", BLOK-" + df_warga['blok'].astype(str) + ")"
        
        with st.form("pemeriksaan_form", clear_on_submit=True):
            tanggal_pemeriksaan = st.date_input("Tanggal Posyandu/Pemeriksaan", value=date.today())
            selected_display_name = st.selectbox("Pilih Warga yang Hadir:", options=df_warga['display_name'])
            
            st.divider()

            ## <<< PERUBAHAN: Logika untuk menampilkan input berdasarkan umur 11082025
            # Dapatkan data lengkap dari warga yang dipilih
            selected_warga_data = df_warga[df_warga['display_name'] == selected_display_name].iloc[0]
            
            # Hitung umur warga
            umur = calculate_age(selected_warga_data['tanggal_lahir'], tanggal_pemeriksaan)
            
            # Inisialisasi semua variabel ke None atau 0
            tensi_sistolik = tensi_diastolik = gula_darah = kolesterol = 0
            berat_badan_kg = tinggi_badan_cm = lingkar_perut_cm = lingkar_lengan_cm = lingkar_kepala_cm = 0.0
            catatan = ""

            st.write("Masukkan hasil pemeriksaan:")
            
            # Jika umur di bawah 5 tahun (balita)
            if umur < 5:
                st.info(f"Pasien terdeteksi sebagai balita (Umur: {umur} tahun). Menampilkan input khusus balita.")
                col1, col2 = st.columns(2)
                with col1:
                    berat_badan_kg = st.number_input("Berat Badan (kg)", min_value=0.0, step=0.1, format="%.2f")
                    lingkar_lengan_cm = st.number_input("Lingkar Lengan (cm)", min_value=0.0, step=0.5, format="%.1f")
                with col2:
                    tinggi_badan_cm = st.number_input("Tinggi Badan (cm)", min_value=0.0, step=0.1, format="%.2f")
                    lingkar_kepala_cm = st.number_input("Lingkar Kepala (cm)", min_value=0.0, step=0.5, format="%.1f")
            
            # Jika umur 5 tahun atau lebih (dewasa)
            else:
                st.info(f"Pasien terdeteksi sebagai dewasa (Umur: {umur} tahun).")
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

            if st.form_submit_button("Simpan Hasil Pemeriksaan"):
                warga_id = selected_warga_data['id']
                
                ## <<< PERUBAHAN: Data yang akan disimpan disesuaikan
                data_to_insert = {
                    "tanggal_pemeriksaan": str(tanggal_pemeriksaan), "warga_id": warga_id,
                    "tensi_sistolik": int(tensi_sistolik), "tensi_diastolik": int(tensi_diastolik),
                    "berat_badan_kg": berat_badan_kg, "tinggi_badan_cm": tinggi_badan_cm,
                    "lingkar_perut_cm": lingkar_perut_cm, "lingkar_lengan_cm": lingkar_lengan_cm, 
                    "gula_darah": int(gula_darah),"kolesterol": int(kolesterol), 
                    "lingkar_kepala_cm": lingkar_kepala_cm, # Nilai akan 0 jika dewasa, dan terisi jika balita
                    "catatan": catatan
                }
                try:
                    supabase.table("pemeriksaan").insert(data_to_insert).execute()
                    st.success(f"Data pemeriksaan untuk '{selected_display_name}' berhasil disimpan.")
                except Exception as e:
                    st.error(f"Gagal menyimpan data pemeriksaan: {e}")

    except Exception as e:
        st.error(f"Gagal mengambil daftar warga: {e}")

# --- JALANKAN HALAMAN ---
page_input_pemeriksaan()