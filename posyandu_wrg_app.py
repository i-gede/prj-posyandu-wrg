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
            rt = st.tex_input("rt")
            blok = st.tex_input("blok")
            
            if st.form_submit_button("Simpan Warga Baru"):
                if not all([nik, nama_lengkap]):
                    st.warning("NIK dan Nama Lengkap wajib diisi.")
                else:
                    try:
                        supabase.table("warga").insert({
                            "nik": nik, "nama_lengkap": nama_lengkap, "tanggal_lahir": str(tanggal_lahir),
                            "jenis_kelamin": jenis_kelamin, "alamat": alamat, "telepon": telepon,
                            "rt": rt, "blok": blok
                        }).execute()
                        st.success(f"Warga baru '{nama_lengkap}' berhasil ditambahkan."); st.rerun()
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

        warga_to_manage = st.selectbox(
            "Pilih warga untuk dikelola:",
            options=df_warga['nama_lengkap'] + " (RT-" + df_warga['rt'] + ", BLOK-" + df_warga['blok'] + ")",
            index=None,
            placeholder="Pilih warga..."
        )

        if warga_to_manage:
            selected_nik = warga_to_manage.split('(')[-1].replace(')', '')
            selected_warga_data = df_warga[df_warga['nik'] == selected_nik].iloc[0]

            with st.expander("✏️ Edit Data Diri Warga"):
                with st.form("edit_warga_form"):
                    edit_nama = st.text_input("Nama Lengkap", value=selected_warga_data['nama_lengkap'])
                    edit_tgl_lahir_val = datetime.strptime(selected_warga_data['tanggal_lahir'], '%Y-%m-%d').date()
                    edit_tgl_lahir = st.date_input("Tanggal Lahir", value=edit_tgl_lahir_val)
                    edit_alamat = st.text_area("Alamat", value=selected_warga_data['alamat'])
                    edit_telepon = st.text_input("Nomor Telepon", value=selected_warga_data['telepon'])

                    if st.form_submit_button("Simpan Perubahan Data Diri"):
                        try:
                            update_data = {"nama_lengkap": edit_nama, "tanggal_lahir": str(edit_tgl_lahir), "alamat": edit_alamat, "telepon": edit_telepon}
                            supabase.table("warga").update(update_data).eq("id", selected_warga_data['id']).execute()
                            st.success("Data warga berhasil diperbarui."); st.rerun()
                        except Exception as e:
                            st.error(f"Gagal memperbarui data: {e}")
            
            st.divider()
            st.subheader(f"Riwayat Pemeriksaan untuk {selected_warga_data['nama_lengkap']}")
            
            pemeriksaan_response = supabase.table("pemeriksaan").select("*").eq("warga_id", selected_warga_data['id']).order("tanggal_pemeriksaan", desc=True).execute()
            
            if not pemeriksaan_response.data:
                st.info("Warga ini belum memiliki riwayat pemeriksaan.")
            else:
                df_pemeriksaan = pd.DataFrame(pemeriksaan_response.data)
                st.dataframe(df_pemeriksaan[['tanggal_pemeriksaan', 'tensi_sistolik', 'tensi_diastolik', 'berat_badan_kg', 'gula_darah', 'kolesterol']])

                plot_individual_trends(df_pemeriksaan)

                st.divider()
                st.write("Pilih pemeriksaan untuk dikelola:")
                df_pemeriksaan['display_entry'] = "Data tgl " + pd.to_datetime(df_pemeriksaan['tanggal_pemeriksaan']).dt.strftime('%Y-%m-%d')
                pemeriksaan_to_edit = st.selectbox("Pilih data pemeriksaan:", df_pemeriksaan['display_entry'])
                
                selected_pemeriksaan = df_pemeriksaan[df_pemeriksaan['display_entry'] == pemeriksaan_to_edit].iloc[0]

                with st.expander("Revisi Hasil Pemeriksaan Terpilih"):
                    with st.form("edit_pemeriksaan_form"):
                        st.write(f"Mengubah data untuk pemeriksaan tanggal **{selected_pemeriksaan['tanggal_pemeriksaan']}**")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            edit_tensi_sistolik = st.number_input("Tensi Sistolik (mmHg)", value=int(selected_pemeriksaan['tensi_sistolik']))
                            edit_berat_badan = st.number_input("Berat Badan (kg)", value=float(selected_pemeriksaan['berat_badan_kg']))
                            edit_lingkar_perut = st.number_input("Lingkar Perut (cm)", value=float(selected_pemeriksaan['lingkar_perut_cm']))
                            edit_gula_darah = st.number_input("Gula Darah (mg/dL)", value=int(selected_pemeriksaan['gula_darah']))
                        with col2:
                            edit_tensi_diastolik = st.number_input("Tensi Diastolik (mmHg)", value=int(selected_pemeriksaan['tensi_diastolik']))
                            edit_lingkar_lengan = st.number_input("Lingkar Lengan (cm)", value=float(selected_pemeriksaan['lingkar_lengan_cm']))
                            edit_kolesterol = st.number_input("Kolesterol (mg/dL)", value=int(selected_pemeriksaan['kolesterol']))
                        
                        edit_catatan = st.text_area("Catatan", value=selected_pemeriksaan['catatan'])

                        if st.form_submit_button("Simpan Perubahan Pemeriksaan"):
                            try:
                                update_data = {
                                    "tensi_sistolik": edit_tensi_sistolik, "tensi_diastolik": edit_tensi_diastolik,
                                    "berat_badan_kg": edit_berat_badan, "lingkar_perut_cm": edit_lingkar_perut,
                                    "lingkar_lengan_cm": edit_lingkar_lengan, "gula_darah": edit_gula_darah,
                                    "kolesterol": edit_kolesterol, "catatan": edit_catatan
                                }
                                supabase.table("pemeriksaan").update(update_data).eq("id", selected_pemeriksaan['id']).execute()
                                st.success("Data pemeriksaan berhasil diperbarui."); st.rerun()
                            except Exception as e:
                                st.error(f"Gagal memperbarui data pemeriksaan: {e}")
                
                with st.expander("❌ Hapus Hasil Pemeriksaan Terpilih"):
                    st.warning(f"PERHATIAN: Anda akan menghapus data pemeriksaan tanggal **{selected_pemeriksaan['tanggal_pemeriksaan']}**. Tindakan ini tidak dapat diurungkan.")
                    if st.checkbox(f"Saya yakin ingin menghapus data pemeriksaan ini.", key=f"delete_check_{selected_pemeriksaan['id']}"):
                        if st.button("Hapus Pemeriksaan Ini Secara Permanen"):
                            try:
                                supabase.table("pemeriksaan").delete().eq("id", selected_pemeriksaan['id']).execute()
                                st.success("Data pemeriksaan berhasil dihapus."); st.rerun()
                            except Exception as e:
                                st.error(f"Gagal menghapus data pemeriksaan: {e}")

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
        df_warga['display_name'] = df_warga['nama_lengkap'] + " (RT-" + df_warga['rt'] + ", BLOK-" + df_warga['blok'] + ")"
        
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

# ==============================================================================
# HALAMAN 3: DASBOR & LAPORAN
# ==============================================================================

def page_dashboard():
    st.header("📈 Dasbor & Laporan")
    if not supabase: return

    try:
        warga_response = supabase.table("warga").select("id, tanggal_lahir, jenis_kelamin").execute()
        pemeriksaan_response = supabase.table("pemeriksaan").select("tanggal_pemeriksaan, warga_id").execute()

        if not warga_response.data:
            st.info("Belum ada data warga untuk ditampilkan di laporan.")
            return

        df_warga = pd.DataFrame(warga_response.data)
        df_pemeriksaan = pd.DataFrame(pemeriksaan_response.data)
        
        df_warga['tanggal_lahir'] = pd.to_datetime(df_warga['tanggal_lahir'])
        df_warga['usia'] = (datetime.now() - df_warga['tanggal_lahir']).dt.days / 365.25
        
        # --- PERUBAHAN 1: Hitung semua kategori usia ---
        total_warga = len(df_warga)
        jumlah_laki = df_warga[df_warga['jenis_kelamin'] == 'L'].shape[0]
        jumlah_perempuan = total_warga - jumlah_laki
        
        jumlah_bayi = df_warga[df_warga['usia'] <= 0.5].shape[0]
        jumlah_baduta = df_warga[(df_warga['usia'] > 0.5) & (df_warga['usia'] < 2)].shape[0]
        jumlah_balita = df_warga[(df_warga['usia'] >= 2) & (df_warga['usia'] < 5)].shape[0]
        jumlah_anak = df_warga[(df_warga['usia'] >= 5) & (df_warga['usia'] < 10)].shape[0]
        jumlah_remaja = df_warga[(df_warga['usia'] >= 10) & (df_warga['usia'] < 20)].shape[0]
        jumlah_dewasa = df_warga[(df_warga['usia'] >= 20) & (df_warga['usia'] < 60)].shape[0]
        jumlah_lansia = df_warga[df_warga['usia'] >= 60].shape[0]

        # --- PERUBAHAN 2: Tampilkan semua metrik demografi ---
        st.subheader("Demografi Warga Terdaftar")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Warga", total_warga)
        col2.metric("Laki-laki", jumlah_laki)
        col3.metric("Perempuan", jumlah_perempuan)
        
        col_bayi, col_baduta, col_balita, col_anak = st.columns(4)
        col_bayi.metric("Bayi (0-6 bln)", jumlah_bayi)
        col_baduta.metric("Baduta (6 bln - 2 thn)", jumlah_baduta)
        col_balita.metric("Balita (2-5 thn)", jumlah_balita)
        col_anak.metric("Anak-anak (5-10 thn)", jumlah_anak)

        col_remaja, col_dewasa, col_lansia, _ = st.columns(4)
        col_remaja.metric("Remaja (10-20 thn)", jumlah_remaja)
        col_dewasa.metric("Dewasa (20-60 thn)", jumlah_dewasa)
        col_lansia.metric("Lansia (60+ thn)", jumlah_lansia)

        st.divider()

        if df_pemeriksaan.empty:
            st.info("Belum ada data pemeriksaan untuk ditampilkan di laporan.")
            return

        # --- PERUBAHAN 3: Update filter grafik tren ---
        st.subheader("Tren Kehadiran Warga ke Posyandu")
        
        filter_options = ['Semua Warga', 'Laki-laki', 'Perempuan', 'Bayi', 'Baduta', 'Balita', 'Anak-anak', 'Remaja', 'Dewasa', 'Lansia']
        selected_filter = st.selectbox("Tampilkan tren untuk:", filter_options)

        df_pemeriksaan_warga = pd.merge(df_pemeriksaan, df_warga, left_on='warga_id', right_on='id')
        
        df_filtered = df_pemeriksaan_warga
        if selected_filter == 'Laki-laki':
            df_filtered = df_pemeriksaan_warga[df_pemeriksaan_warga['jenis_kelamin'] == 'Laki-laki']
        elif selected_filter == 'Perempuan':
            df_filtered = df_pemeriksaan_warga[df_pemeriksaan_warga['jenis_kelamin'] == 'Perempuan']
        elif selected_filter == 'Bayi':
            df_filtered = df_pemeriksaan_warga[df_pemeriksaan_warga['usia'] <= 0.5]
        elif selected_filter == 'Baduta':
            df_filtered = df_pemeriksaan_warga[(df_pemeriksaan_warga['usia'] > 0.5) & (df_pemeriksaan_warga['usia'] < 2)]
        elif selected_filter == 'Balita':
            df_filtered = df_pemeriksaan_warga[(df_pemeriksaan_warga['usia'] >= 2) & (df_pemeriksaan_warga['usia'] < 5)]
        elif selected_filter == 'Anak-anak':
            df_filtered = df_pemeriksaan_warga[(df_pemeriksaan_warga['usia'] >= 5) & (df_pemeriksaan_warga['usia'] < 10)]
        elif selected_filter == 'Remaja':
            df_filtered = df_pemeriksaan_warga[(df_pemeriksaan_warga['usia'] >= 10) & (df_pemeriksaan_warga['usia'] < 20)]
        elif selected_filter == 'Dewasa':
            df_filtered = df_pemeriksaan_warga[(df_pemeriksaan_warga['usia'] >= 20) & (df_pemeriksaan_warga['usia'] < 60)]
        elif selected_filter == 'Lansia':
            df_filtered = df_pemeriksaan_warga[df_pemeriksaan_warga['usia'] >= 60]
            
        if not df_filtered.empty:
            df_filtered['tanggal_pemeriksaan'] = pd.to_datetime(df_filtered['tanggal_pemeriksaan'])
            kehadiran_per_hari = df_filtered.groupby('tanggal_pemeriksaan').size().reset_index(name='jumlah_hadir')
            
            fig1, ax1 = plt.subplots(figsize=(10, 5))
            ax1.plot(kehadiran_per_hari['tanggal_pemeriksaan'], kehadiran_per_hari['jumlah_hadir'], marker='o', linestyle='-')
            ax1.set_title(f"Jumlah Kehadiran per Tanggal Posyandu ({selected_filter})")
            ax1.set_xlabel("Tanggal"); ax1.set_ylabel("Jumlah Warga Hadir")
            ax1.grid(True, linestyle='--', alpha=0.6); plt.xticks(rotation=45)
            fig1.tight_layout(); st.pyplot(fig1)
        else:
            st.info(f"Tidak ada data kehadiran untuk kategori '{selected_filter}'.")

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
            ax2.axis('equal'); ax2.set_title(f"Proporsi Kehadiran pada {pd.to_datetime(tanggal_terakhir).strftime('%d %B %Y')}")
            st.pyplot(fig2)
        else:
            st.info("Tidak ada data kehadiran pada tanggal terakhir.")

    except Exception as e:
        st.error(f"Gagal membuat laporan: {e}")

# ==============================================================================
# FUNGSI BARU: PLOT TREN INDIVIDU
# ==============================================================================
def plot_individual_trends(df_pemeriksaan):
    st.subheader("📈 Grafik Tren Kesehatan Individu")
    df_pemeriksaan['tanggal_pemeriksaan'] = pd.to_datetime(df_pemeriksaan['tanggal_pemeriksaan'])
    df_pemeriksaan = df_pemeriksaan.sort_values(by='tanggal_pemeriksaan')

    col1, col2 = st.columns(2)

    with col1:
        # Grafik Tensi
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(df_pemeriksaan['tanggal_pemeriksaan'], df_pemeriksaan['tensi_sistolik'], marker='o', label='Sistolik')
        ax.plot(df_pemeriksaan['tanggal_pemeriksaan'], df_pemeriksaan['tensi_diastolik'], marker='o', label='Diastolik')
        ax.set_title("Tren Tensi Darah"); ax.set_ylabel("mmHg"); ax.legend(); ax.grid(True, linestyle=':')
        plt.xticks(rotation=45); fig.tight_layout(); st.pyplot(fig)

        # Grafik Gula Darah
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(df_pemeriksaan['tanggal_pemeriksaan'], df_pemeriksaan['gula_darah'], marker='o', color='g')
        ax.set_title("Tren Gula Darah"); ax.set_ylabel("mg/dL"); ax.grid(True, linestyle=':')
        plt.xticks(rotation=45); fig.tight_layout(); st.pyplot(fig)

    with col2:
        # Grafik Berat Badan
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(df_pemeriksaan['tanggal_pemeriksaan'], df_pemeriksaan['berat_badan_kg'], marker='o', color='r')
        ax.set_title("Tren Berat Badan"); ax.set_ylabel("kg"); ax.grid(True, linestyle=':')
        plt.xticks(rotation=45); fig.tight_layout(); st.pyplot(fig)
        
        # Grafik Kolesterol
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(df_pemeriksaan['tanggal_pemeriksaan'], df_pemeriksaan['kolesterol'], marker='o', color='purple')
        ax.set_title("Tren Kolesterol"); ax.set_ylabel("mg/dL"); ax.grid(True, linestyle=':')
        plt.xticks(rotation=45); fig.tight_layout(); st.pyplot(fig)

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
