# pages/2_Input_Pemeriksaan.py

import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import date

# --- KONEKSI & KEAMANAN ---
st.set_page_config(page_title="Input Pemeriksaan", page_icon="🗓️", layout="wide")

if not st.session_state.get("authenticated", False):
    st.error("🔒 Anda harus login untuk mengakses halaman ini.")
    st.stop()

@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Gagal terhubung ke Supabase: {e}")
        return None

supabase = init_connection()

# --- FUNGSI HALAMAN UTAMA ---
def page_input_pemeriksaan():
    st.header("🗓️ Input Kehadiran & Pemeriksaan")
    if not supabase: return

    try:
        response = supabase.table("warga").select("id, nik, nama_lengkap, rt, blok").execute()
        if not response.data:
            st.warning("Belum ada data warga. Silakan tambahkan data warga terlebih dahulu.")
            return

        df_warga = pd.DataFrame(response.data)
        df_warga['display_name'] = df_warga['nama_lengkap'] + " (RT-" + df_warga['rt'].astype(str) + ", BLOK-" + df_warga['blok'].astype(str) + ")"
        
        with st.form("pemeriksaan_form", clear_on_submit=True):
            tanggal_pemeriksaan = st.date_input("Tanggal Posyandu/Pemeriksaan", value=date.today())
            selected_display_name = st.selectbox("Pilih Warga yang Hadir:", options=df_warga['display_name'])
            
            st.divider()
            st.write("Masukkan hasil pemeriksaan:")
            
            col1, col2 = st.columns(2)
            with col1:
                tensi_sistolik = st.number_input("Tensi Sistolik (mmHg)", min_value=0, step=1)
                berat_badan_kg = st.number_input("Berat Badan (kg)", min_value=0.0, step=0.1, format="%.2f")
                lingkar_perut_cm = st.number_input("Lingkar Perut (cm)", min_value=0.0, step=0.5, format="%.1f")
                gula_darah = st.number_input("Gula Darah (mg/dL)", min_value=0, step=1)
            with col2:
                tensi_diastolik = st.number_input("Tensi Diastolik (mmHg)", min_value=0, step=1)
                lingkar_lengan_cm = st.number_input("Lingkar Lengan (cm)", min_value=0.0, step=0.5, format="%.1f")
                kolesterol = st.number_input("Kolesterol (mg/dL)", min_value=0, step=1)
            
            catatan = st.text_area("Catatan Tambahan (Opsional)")

            if st.form_submit_button("Simpan Hasil Pemeriksaan"):
                warga_id = df_warga[df_warga['display_name'] == selected_display_name]['id'].iloc[0]
                
                data_to_insert = {
                    "tanggal_pemeriksaan": str(tanggal_pemeriksaan), "warga_id": warga_id,
                    "tensi_sistolik": int(tensi_sistolik), "tensi_diastolik": int(tensi_diastolik),
                    "berat_badan_kg": berat_badan_kg, "lingkar_perut_cm": lingkar_perut_cm,
                    "lingkar_lengan_cm": lingkar_lengan_cm, "gula_darah": int(gula_darah),
                    "kolesterol": int(kolesterol), "catatan": catatan
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