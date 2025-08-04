# posyandu_wrg_app.py

import streamlit as st
from supabase import create_client, Client

# Fungsi login akan menggunakan client publik (anon key)
def login_page():
    st.header("🔑 Login Admin Posyandu Mawar")
    
    # Inisialisasi client publik HANYA untuk login
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase_public = create_client(url, key)

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            try:
                # 1. Lakukan login dengan client publik
                session = supabase_public.auth.sign_in_with_password({
                    "email": email, "password": password
                })
                
                # 2. Jika berhasil, buat client baru dengan KUNCI SUPER ADMIN
                service_key = st.secrets["SUPABASE_SERVICE_KEY"]
                supabase_service_client = create_client(url, service_key)

                # 3. Simpan client super admin ini di session_state
                st.session_state.authenticated = True
                st.session_state.user_email = session.user.email
                st.session_state.supabase_client = supabase_service_client # INI KUNCINYA
                
                st.rerun()

            except Exception as e:
                st.error("Gagal login. Pastikan email dan password benar.")

def main_page():
    st.sidebar.success(f"Login sebagai: {st.session_state.get('user_email', 'Admin')}")
    st.sidebar.divider()
    
    st.title("Selamat Datang di Aplikasi Posyandu Mawar")
    st.markdown("Silakan pilih halaman dari menu di sebelah kiri.")

    if st.sidebar.button("🔒 Logout"):
        # Hapus semua state saat logout
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

# --- ALUR UTAMA ---
st.set_page_config(page_title="Posyandu Mawar", page_icon="🏥", layout="wide")

if not st.session_state.get("authenticated", False):
    login_page()
else:
    main_page()