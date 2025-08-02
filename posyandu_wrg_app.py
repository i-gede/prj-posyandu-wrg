# posyandu_wrg_app.py

import streamlit as st
from supabase import create_client, Client

# ==============================================================================
# KONEKSI & OTENTIKASI
# ==============================================================================

# Inisialisasi koneksi ke Supabase
@st.cache_resource
def init_connection():
    """Membuat dan mengembalikan koneksi ke database Supabase."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Gagal terhubung ke Supabase: {e}")
        st.info("Pastikan Anda sudah mengatur SUPABASE_URL dan SUPABASE_KEY di Streamlit Secrets.")
        return None

supabase = init_connection()

# Fungsi untuk menampilkan halaman login
def login_page():
    """Menampilkan halaman login dan menangani proses otentikasi."""
    st.header("🔑 Login Admin Posyandu Mawar")
    
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if not supabase:
                st.error("Koneksi database tidak tersedia.")
                return
            
            if not email or not password:
                st.warning("Mohon masukkan email dan password.")
                return

            try:
                # Coba login menggunakan Supabase Auth
                session = supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })
                
                # Jika berhasil, tandai bahwa pengguna sudah terotentikasi
                st.session_state.authenticated = True
                st.session_state.user_email = session.user.email
                
                st.rerun()

            except Exception:
                st.error("Gagal login. Pastikan email dan password benar.")

# Fungsi untuk halaman utama setelah login
def main_page():
    """Menampilkan halaman utama dan tombol logout setelah login berhasil."""
    st.sidebar.success(f"Login sebagai: {st.session_state.get('user_email', 'Admin')}")
    st.sidebar.divider()
    
    st.title("Selamat Datang di Aplikasi Posyandu Mawar")
    st.header("Lingkungan Karang Baru Utara (KBU)")
    st.markdown("Silakan pilih halaman yang ingin Anda akses dari menu navigasi di sebelah kiri.")
    st.info("Aplikasi ini digunakan untuk manajemen data, input pemeriksaan, dan melihat laporan kesehatan warga.")

    if st.sidebar.button("🔒 Logout"):
        st.session_state.authenticated = False
        if 'user_email' in st.session_state:
            del st.session_state['user_email']
        st.rerun()

# ==============================================================================
# ALUR UTAMA APLIKASI
# ==============================================================================

st.set_page_config(page_title="Posyandu Mawar", page_icon="🏥", layout="wide")

if not st.session_state.get("authenticated", False):
    login_page()
else:
    main_page()