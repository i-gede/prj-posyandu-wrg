# pages/1_Manajemen_Warga.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from supabase import create_client
from datetime import date, datetime
from page_dashboard import format_usia_string

# --- KONEKSI & KEAMANAN ---
st.set_page_config(page_title="Manajemen Warga", page_icon="👨‍👩‍👧‍👦", layout="wide")

# # Blokir akses jika pengguna belum login
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

# --- FUNGSI-FUNGSI PEMBANTU ---
def plot_individual_trends(df_pemeriksaan):
    st.subheader("📈 Grafik Tren Kesehatan Individu")
    df_pemeriksaan['tanggal_pemeriksaan'] = pd.to_datetime(df_pemeriksaan['tanggal_pemeriksaan'])
    df_pemeriksaan = df_pemeriksaan.sort_values(by='tanggal_pemeriksaan')

    col1, col2 = st.columns(2)
    with col1:
        fig, ax = plt.subplots(figsize=(6, 4)); ax.plot(df_pemeriksaan['tanggal_pemeriksaan'], df_pemeriksaan['tensi_sistolik'], marker='o', label='Sistolik'); ax.plot(df_pemeriksaan['tanggal_pemeriksaan'], df_pemeriksaan['tensi_diastolik'], marker='o', label='Diastolik'); ax.set_title("Tren Tensi Darah"); ax.set_ylabel("mmHg"); ax.legend(); ax.grid(True, linestyle=':'); plt.xticks(rotation=45); fig.tight_layout(); st.pyplot(fig)
        fig, ax = plt.subplots(figsize=(6, 4)); ax.plot(df_pemeriksaan['tanggal_pemeriksaan'], df_pemeriksaan['gula_darah'], marker='o', color='g'); ax.set_title("Tren Gula Darah"); ax.set_ylabel("mg/dL"); ax.grid(True, linestyle=':'); plt.xticks(rotation=45); fig.tight_layout(); st.pyplot(fig)
    with col2:
        fig, ax = plt.subplots(figsize=(6, 4)); ax.plot(df_pemeriksaan['tanggal_pemeriksaan'], df_pemeriksaan['berat_badan_kg'], marker='o', color='r'); ax.set_title("Tren Berat Badan"); ax.set_ylabel("kg"); ax.grid(True, linestyle=':'); plt.xticks(rotation=45); fig.tight_layout(); st.pyplot(fig)
        fig, ax = plt.subplots(figsize=(6, 4)); ax.plot(df_pemeriksaan['tanggal_pemeriksaan'], df_pemeriksaan['kolesterol'], marker='o', color='purple'); ax.set_title("Tren Kolesterol"); ax.set_ylabel("mg/dL"); ax.grid(True, linestyle=':'); plt.xticks(rotation=45); fig.tight_layout(); st.pyplot(fig)


# --- FUNGSI HALAMAN UTAMA ---
def page_manajemen_warga():
    st.header("👨‍👩‍👧‍👦 Manajemen Data Warga")
    if not supabase: return

    # --- Fitur Tambah Warga Baru ---
    with st.expander("➕ Tambah Warga Baru"):
        with st.form("new_warga_form", clear_on_submit=True):
            st.write("Masukkan data diri warga baru:")
            nik = st.text_input("NIK")
            nama_lengkap = st.text_input("Nama Lengkap")
            
            col1, col2 = st.columns(2)
            with col1: rt = st.text_input("RT")
            with col2: blok = st.text_input("Blok")

            tanggal_lahir = st.date_input("Tanggal Lahir", min_value=date(1920, 1, 1), max_value=date.today())
            jenis_kelamin_display = st.selectbox("Jenis Kelamin", ["Laki-laki", "Perempuan"])
            alamat = st.text_area("Alamat")
            telepon = st.text_input("Nomor Telepon (Opsional)")
            
            if st.form_submit_button("Simpan Warga Baru"):
                if not all([nik, nama_lengkap, rt, blok]):
                    st.warning("NIK, Nama Lengkap, RT, dan Blok wajib diisi.")
                else:
                    try:
                        jenis_kelamin_db = "L" if jenis_kelamin_display == "Laki-laki" else "P"
                        supabase.table("warga").insert({
                            "nik": nik, "nama_lengkap": nama_lengkap, "tanggal_lahir": str(tanggal_lahir),
                            "jenis_kelamin": jenis_kelamin_db, "alamat": alamat, "telepon": telepon,
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
        # st.dataframe(df_warga)

        # Tabel ringkas (hanya kolom tertentu)
        df_warga_tampil = df_warga[["nik", "nama_lengkap", "tanggal_lahir", "jenis_kelamin", "rt"]]

        # Ganti nama kolom untuk tampilan
        df_warga_tampil = df_warga_tampil.rename(columns={
            "nik": "NIK",
            "nama_lengkap": "Nama Lengkap",
            "tanggal_lahir": "Tanggal Lahir",
            "jenis_kelamin": "Jenis Kelamin",
            "rt": "RT",
            "blok": "Blok"
        })
        st.dataframe(df_warga_tampil)

        df_warga['display_name'] = df_warga['nama_lengkap'] + " (RT-" + df_warga['rt'].astype(str) + ", BLOK-" + df_warga['blok'].astype(str) + ")"
        
        warga_to_manage = st.selectbox(
            "Pilih warga untuk dikelola:",
            options=df_warga['display_name'], index=None, placeholder="Pilih warga..."
        )

        if warga_to_manage:
            selected_warga_data = df_warga[df_warga['display_name'] == warga_to_manage].iloc[0]

            with st.expander("✏️ Edit Data Diri Warga"):
                with st.form("edit_warga_form"):
                    edit_nik = st.text_input("NIK", value=selected_warga_data['nik']) #13082025 field edit NIK
                    edit_nama = st.text_input("Nama Lengkap", value=selected_warga_data['nama_lengkap'])
                    
                    col_edit1, col_edit2 = st.columns(2)
                    with col_edit1: edit_rt = st.text_input("RT", value=selected_warga_data.get('rt', ''))
                    with col_edit2: edit_blok = st.text_input("Blok", value=selected_warga_data.get('blok', ''))

                    edit_tgl_lahir_val = datetime.strptime(selected_warga_data['tanggal_lahir'], '%Y-%m-%d').date()
                    edit_tgl_lahir = st.date_input("Tanggal Lahir", value=edit_tgl_lahir_val)
                    edit_alamat = st.text_area("Alamat", value=selected_warga_data['alamat'])
                    edit_telepon = st.text_input("Nomor Telepon", value=selected_warga_data.get('telepon', ''))

                    if st.form_submit_button("Simpan Perubahan Data Diri"):
                        try:
                            update_data = {
                                "nik": edit_nik, "nama_lengkap": edit_nama, "tanggal_lahir": str(edit_tgl_lahir), 
                                "alamat": edit_alamat, "telepon": edit_telepon,
                                "rt": edit_rt, "blok": edit_blok
                            }
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

                df_pemeriksaan['usia_thn_bln'] = df_pemeriksaan['tanggal_lahir'].apply(
                    lambda tgl: format_usia_string(tgl, df_pemeriksaan['tanggal_pemeriksaan'])
                ) #13082025 tambahkolom usia dalam tahun bulan

                st.dataframe(df_pemeriksaan[['tanggal_pemeriksaan', 'usia_thn_bln', 'berat_badan_kg', 'tinggi_badan_kg', 'lingkar_lengan_cm', 'lingkar_kepala_cm', 'tensi_sistolik', 'tensi_diastolik', 'gula_darah', 'kolesterol']])

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
                # Sisa logika untuk edit dan hapus data pemeriksaan... (bisa ditambahkan di sini)

    except Exception as e:
        st.error(f"Gagal mengambil data warga: {e}")

# --- JALANKAN HALAMAN ---
page_manajemen_warga()