import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from supabase import create_client, Client
from datetime import date, datetime

# ==============================================================================
# KONEKSI KE DATABASE SUPABASE
# ==============================================================================

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

# ==============================================================================
# HALAMAN 1: MANAJEMEN DATA WARGA
# ==============================================================================

def page_manajemen_warga():
    st.header("👨‍👩‍👧‍👦 Manajemen Data Warga")
    if not supabase: return

    # --- Fitur Tambah Warga Baru ---
    with st.expander("➕ Tambah Warga Baru"):
        with st.form("new_warga_form", clear_on_submit=True):
            st.write("Masukkan data diri warga baru:")
            nik = st.text_input("NIK")
            nama_lengkap = st.text_input("Nama Lengkap")
            tanggal_lahir = st.date_input("Tanggal Lahir", min_value=date(1920, 1, 1), max_value=date.today())
            jenis_kelamin = st.selectbox("Jenis Kelamin", ["Laki-laki", "Perempuan"])
            alamat = st.text_area("Alamat")
            telepon = st.text_input("Nomor Telepon (Opsional)")
            
            if st.form_submit_button("Simpan Warga Baru"):
                if not all([nik, nama_lengkap]):
                    st.warning("NIK dan Nama Lengkap wajib diisi.")
                else:
                    try:
                        supabase.table("warga").insert({
                            "nik": nik, "nama_lengkap": nama_lengkap, "tanggal_lahir": str(tanggal_lahir),
                            "jenis_kelamin": jenis_kelamin, "alamat": alamat, "telepon": telepon
                        }).execute()
                        st.success(f"Warga baru '{nama_lengkap}' berhasil ditambahkan.")
                    except Exception as e:
                        st.error(f"Gagal menambahkan warga: {e}")

    st.divider()

    # --- Menampilkan dan Mengelola Data Warga yang Ada ---
    st.subheader("Daftar Warga Terdaftar")
    try:
        response = supabase.table("warga").select("*").order("created_at", desc=True).execute()
        if not response.data:
            st.info("Belum ada data warga yang terdaftar.")
            return

        df_warga = pd.DataFrame(response.data)
        st.dataframe(df_warga)

        # --- Fitur Edit dan Hapus ---
        warga_to_manage = st.selectbox(
            "Pilih warga untuk diedit atau dihapus:",
            options=df_warga['nama_lengkap'] + " (" + df_warga['nik'] + ")",
            index=None,
            placeholder="Pilih warga..."
        )

        if warga_to_manage:
            selected_nik = warga_to_manage.split('(')[-1].replace(')', '')
            selected_warga_data = df_warga[df_warga['nik'] == selected_nik].iloc[0]

            with st.expander("✏️ Edit Data Warga Terpilih"):
                with st.form("edit_warga_form"):
                    edit_nama = st.text_input("Nama Lengkap", value=selected_warga_data['nama_lengkap'])
                    edit_tgl_lahir_val = datetime.strptime(selected_warga_data['tanggal_lahir'], '%Y-%m-%d').date()
                    edit_tgl_lahir = st.date_input("Tanggal Lahir", value=edit_tgl_lahir_val)
                    edit_alamat = st.text_area("Alamat", value=selected_warga_data['alamat'])
                    edit_telepon = st.text_input("Nomor Telepon", value=selected_warga_data['telepon'])

                    if st.form_submit_button("Simpan Perubahan"):
                        try:
                            update_data = {"nama_lengkap": edit_nama, "tanggal_lahir": str(edit_tgl_lahir), "alamat": edit_alamat, "telepon": edit_telepon}
                            supabase.table("warga").update(update_data).eq("id", selected_warga_data['id']).execute()
                            st.success("Data warga berhasil diperbarui."); st.rerun()
                        except Exception as e:
                            st.error(f"Gagal memperbarui data: {e}")
            
            with st.expander("❌ Hapus Data Warga Terpilih"):
                st.warning(f"PERHATIAN: Menghapus data warga '{selected_warga_data['nama_lengkap']}' juga akan menghapus **semua riwayat pemeriksaannya**.")
                if st.checkbox("Saya mengerti dan yakin ingin menghapus data warga ini."):
                    if st.button("Hapus Permanen"):
                        try:
                            supabase.table("warga").delete().eq("id", selected_warga_data['id']).execute()
                            st.success("Data warga dan semua riwayatnya berhasil dihapus."); st.rerun()
                        except Exception as e:
                            st.error(f"Gagal menghapus data: {e}")

    except Exception as e:
        st.error(f"Gagal mengambil data warga: {e}")

# ==============================================================================
# HALAMAN 2: INPUT KEHADIRAN & PEMERIKSAAN
# ==============================================================================

def page_input_pemeriksaan():
    st.header("🗓️ Input Kehadiran & Pemeriksaan")
    if not supabase: return

    try:
        response = supabase.table("warga").select("id, nik, nama_lengkap").execute()
        if not response.data:
            st.warning("Belum ada data warga. Silakan tambahkan data warga terlebih dahulu di halaman 'Manajemen Data Warga'.")
            return

        df_warga = pd.DataFrame(response.data)
        df_warga['display_name'] = df_warga['nama_lengkap'] + " (" + df_warga['nik'] + ")"
        
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
                    "tensi_sistolik": tensi_sistolik, "tensi_diastolik": tensi_diastolik,
                    "berat_badan_kg": berat_badan_kg, "lingkar_perut_cm": lingkar_perut_cm,
                    "lingkar_lengan_cm": lingkar_lengan_cm, "gula_darah": gula_darah,
                    "kolesterol": kolesterol, "catatan": catatan
                }
                try:
                    supabase.table("pemeriksaan").insert(data_to_insert).execute()
                    st.success(f"Data pemeriksaan untuk '{selected_display_name}' berhasil disimpan.")
                except Exception as e:
                    st.error(f"Gagal menyimpan data pemeriksaan: {e}")

    except Exception as e:
        st.error(f"Gagal mengambil daftar warga: {e}")

# ==============================================================================
# HALAMAN 3: DASBOR & LAPORAN
# ==============================================================================

def page_dashboard():
    st.header("📈 Dasbor & Laporan")
    if not supabase: return

    try:
        # Ambil semua data yang diperlukan
        warga_response = supabase.table("warga").select("id", count='exact').execute()
        pemeriksaan_response = supabase.table("pemeriksaan").select("tanggal_pemeriksaan").execute()

        total_warga = warga_response.count
        df_pemeriksaan = pd.DataFrame(pemeriksaan_response.data)

        if df_pemeriksaan.empty:
            st.info("Belum ada data pemeriksaan untuk ditampilkan di laporan.")
            return

        st.metric("Total Warga Terdaftar", total_warga)
        
        st.divider()

        # --- Grafik Tren Kehadiran ---
        st.subheader("Tren Kehadiran Warga ke Posyandu")
        df_pemeriksaan['tanggal_pemeriksaan'] = pd.to_datetime(df_pemeriksaan['tanggal_pemeriksaan'])
        kehadiran_per_hari = df_pemeriksaan.groupby('tanggal_pemeriksaan').size().reset_index(name='jumlah_hadir')
        
        fig1, ax1 = plt.subplots(figsize=(10, 5))
        ax1.plot(kehadiran_per_hari['tanggal_pemeriksaan'], kehadiran_per_hari['jumlah_hadir'], marker='o', linestyle='-')
        ax1.set_title("Jumlah Kehadiran per Tanggal Posyandu")
        ax1.set_xlabel("Tanggal")
        ax1.set_ylabel("Jumlah Warga Hadir")
        ax1.grid(True, linestyle='--', alpha=0.6)
        plt.xticks(rotation=45)
        fig1.tight_layout()
        st.pyplot(fig1)

        st.divider()

        # --- Grafik Proporsi Kehadiran ---
        st.subheader("Proporsi Kehadiran pada Posyandu Terakhir")
        tanggal_terakhir = df_pemeriksaan['tanggal_pemeriksaan'].max()
        hadir_terakhir = df_pemeriksaan[df_pemeriksaan['tanggal_pemeriksaan'] == tanggal_terakhir].shape[0]
        tidak_hadir = total_warga - hadir_terakhir

        if hadir_terakhir > 0:
            labels = 'Hadir', 'Tidak Hadir'
            sizes = [hadir_terakhir, tidak_hadir]
            colors = ['#4CAF50', '#FFC107']
            
            fig2, ax2 = plt.subplots()
            ax2.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors, wedgeprops={'edgecolor': 'white'})
            ax2.axis('equal')  # Pastikan pie chart berbentuk lingkaran.
            ax2.set_title(f"Proporsi Kehadiran pada {tanggal_terakhir.strftime('%d %B %Y')}")
            st.pyplot(fig2)
        else:
            st.info("Tidak ada data kehadiran pada tanggal terakhir.")

    except Exception as e:
        st.error(f"Gagal membuat laporan: {e}")

# ==============================================================================
# BAGIAN UTAMA APLIKASI (MAIN)
# ==============================================================================

st.set_page_config(page_title="Posyandu Warga", layout="wide")
st.sidebar.title("🏥 Aplikasi Posyandu Warga")

page_options = {
    "👨‍👩‍👧‍👦 Manajemen Data Warga": page_manajemen_warga,
    "🗓️ Input Kehadiran & Pemeriksaan": page_input_pemeriksaan,
    "📈 Dasbor & Laporan": page_dashboard
}

selected_page = st.sidebar.radio("Pilih Halaman:", page_options.keys())
page_options[selected_page]()