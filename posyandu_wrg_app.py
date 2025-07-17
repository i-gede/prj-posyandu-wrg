import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from supabase import create_client, Client
from datetime import date, datetime, timedelta
# --- PERUBAHAN 1: Menambahkan impor untuk membuat PDF ---
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
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
# FUNGSI BARU: PEMBUAT LAPORAN PDF
# ==============================================================================

def generate_pdf_report(filters, metrics, df_rinci, fig_tren, fig_pie):
    """
    Membuat laporan PDF dari data yang sudah difilter.
    Fungsi ini menerima figure objects (fig_tren, fig_pie) langsung.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='Left', alignment=TA_LEFT))

    elements = []

    # Judul Laporan
    elements.append(Paragraph("Laporan Posyandu Mawar - KBU", styles['h1']))
    elements.append(Spacer(1, 0.2 * inch))
    
    filter_text = f"<b>Laporan:</b><br/>- Tanggal: {filters['selected_date_str']}<br/>- Wilayah: {filters['rt']}<br/>- Kategori Usia: {filters['kategori']}<br/>- Jenis Kelamin: {filters['gender']}"
    elements.append(Paragraph(filter_text, styles['Normal']))
    elements.append(Spacer(1, 0.3 * inch))

    # Ringkasan Metrik
    elements.append(Paragraph("Ringkasan Laporan", styles['h2']))
    
    metric_data = [
        ['Total Warga', f": {metrics['total_warga']}"],
        ['Jumlah Kunjungan', f": {metrics['hadir_hari_ini']}"],
        ['Tingkat Partisipasi', f": {metrics['partisipasi_hari_ini']:.1f}%"]
    ]
    metric_table = Table(metric_data, colWidths=[2.5*inch, 2.5*inch])
    metric_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'LEFT'), ('FONTNAME', (0,0), (-1,-1), 'Helvetica')]))
    elements.append(metric_table)
    elements.append(Spacer(1, 0.3 * inch))

    # Grafik Pie Chart
    if fig_pie:
        img_buffer_pie = BytesIO()
        fig_pie.savefig(img_buffer_pie, format='png', dpi=300, bbox_inches='tight')
        img_buffer_pie.seek(0)
        elements.append(Image(img_buffer_pie, width=4*inch, height=4*inch))
        # --- PERBAIKAN: Menghapus .close() ---
        # img_buffer_pie.close() 
    
    elements.append(PageBreak())
    elements.append(Paragraph("Tren Kunjungan Warga", styles['h2']))
    if fig_tren:
        img_buffer_tren = BytesIO()
        fig_tren.savefig(img_buffer_tren, format='png', dpi=300, bbox_inches='tight')
        img_buffer_tren.seek(0)
        elements.append(Image(img_buffer_tren, width=6*inch, height=3*inch))
        # --- PERBAIKAN: Menghapus .close() ---
        # img_buffer_tren.close()
    
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph("Data Rinci Kunjungan", styles['h2']))
    elements.append(Spacer(1, 0.2 * inch))
    
    table_data = [df_rinci.columns.to_list()] + df_rinci.values.tolist()
    data_rinci_table = Table(table_data, repeatRows=1)
    data_rinci_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12), ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    elements.append(data_rinci_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer

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
            
            # Menambahkan input RT dan Blok
            col1, col2 = st.columns(2)
            with col1:
                rt = st.text_input("RT")
            with col2:
                blok = st.text_input("Blok")

            tanggal_lahir = st.date_input("Tanggal Lahir", min_value=date(1920, 1, 1), max_value=date.today())
            jenis_kelamin_display = st.selectbox("Jenis Kelamin", ["Laki-laki", "Perempuan"])
            alamat = st.text_area("Alamat")
            telepon = st.text_input("Nomor Telepon (Opsional)")
            
            if st.form_submit_button("Simpan Warga Baru"):
                if not all([nik, nama_lengkap, rt, blok]):
                    st.warning("NIK, Nama Lengkap, RT, dan Blok wajib diisi.")
                else:
                    try:
                        # --- PERUBAHAN: Konversi 'Laki-laki'/'Perempuan' menjadi 'L'/'P' ---
                        jenis_kelamin_db = "L" if jenis_kelamin_display == "Laki-laki" else "P"
                        # Menyimpan data RT dan Blok
                        supabase.table("warga").insert({
                            "nik": nik, "nama_lengkap": nama_lengkap, "tanggal_lahir": str(tanggal_lahir),
                            "jenis_kelamin": jenis_kelamin_db, # Simpan 'L' atau 'P'
                            "alamat": alamat, "telepon": telepon,
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

        # Membuat display_name menggunakan kolom 'rt' dan 'blok'
        df_warga['display_name'] = df_warga['nama_lengkap'] + " (RT-" + df_warga['rt'].astype(str) + ", BLOK-" + df_warga['blok'].astype(str) + ")"
        
        warga_to_manage = st.selectbox(
            "Pilih warga untuk dikelola:",
            options=df_warga['display_name'],
            index=None,
            placeholder="Pilih warga..."
        )

        if warga_to_manage:
            # --- PERBAIKAN LOGIKA PENCARIAN DI SINI ---
            # Mencari baris data berdasarkan 'display_name' yang cocok, bukan dengan memecah string.
            selected_warga_data = df_warga[df_warga['display_name'] == warga_to_manage].iloc[0]

            with st.expander("✏️ Edit Data Diri Warga"):
                with st.form("edit_warga_form"):
                    edit_nama = st.text_input("Nama Lengkap", value=selected_warga_data['nama_lengkap'])
                    
                    col_edit1, col_edit2 = st.columns(2)
                    with col_edit1:
                        edit_rt = st.text_input("RT", value=selected_warga_data.get('rt', ''))
                    with col_edit2:
                        edit_blok = st.text_input("Blok", value=selected_warga_data.get('blok', ''))

                    edit_tgl_lahir_val = datetime.strptime(selected_warga_data['tanggal_lahir'], '%Y-%m-%d').date()
                    edit_tgl_lahir = st.date_input("Tanggal Lahir", value=edit_tgl_lahir_val)
                    edit_alamat = st.text_area("Alamat", value=selected_warga_data['alamat'])
                    edit_telepon = st.text_input("Nomor Telepon", value=selected_warga_data['telepon'])

                    if st.form_submit_button("Simpan Perubahan Data Diri"):
                        try:
                            update_data = {
                                "nama_lengkap": edit_nama, "tanggal_lahir": str(edit_tgl_lahir), 
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
        # --- PERUBAHAN 1: Mengambil kolom 'rt' dan 'blok' dari database ---
        response = supabase.table("warga").select("id, nik, nama_lengkap, rt, blok").execute()
        if not response.data:
            st.warning("Belum ada data warga. Silakan tambahkan data warga terlebih dahulu di halaman 'Manajemen Data Warga'.")
            return

        df_warga = pd.DataFrame(response.data)
        
        # --- PERUBAHAN 2: Membuat display_name menggunakan RT dan Blok ---
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

# ==============================================================================
# HALAMAN 3: DASBOR & LAPORAN (VERSI BARU INTERAKTIF)
# ==============================================================================

def page_dashboard():
    # st.header("📈 Dashboard & Laporan")
    st.markdown(
        """
        <div style="background-color:#0A2342; padding:16px; border-radius:10px;">
            <h2 style="color:white; margin:0;">📈 Dashboard</h2>
        </div>
        """,
        unsafe_allow_html=True
    )
    if not supabase: return

    try:
        # --- PERBAIKAN 1: Mengambil semua kolom dari kedua tabel ---
        warga_response = supabase.table("warga").select("*").execute()
        pemeriksaan_response = supabase.table("pemeriksaan").select("*").execute()

        if not warga_response.data:
            st.info("Belum ada data warga untuk ditampilkan di laporan.")
            return

        df_warga = pd.DataFrame(warga_response.data)
        df_pemeriksaan = pd.DataFrame(pemeriksaan_response.data)
        
        # Usia warga berdasarkan per hari ini!
        df_warga['tanggal_lahir'] = pd.to_datetime(df_warga['tanggal_lahir'])
        #df_warga['usia'] = (datetime.now() - df_warga['tanggal_lahir']).dt.days / 365.25
        
        # Ini cobain
        df_warga['tanggal_pemeriksaan'] = pd.to_datetime(df_warga['tanggal_pemeriksaan'])
        # Hitung usia saat pemeriksaan
        df_warga['usia'] = (df_warga['tanggal_pemeriksaan'] - df_warga['tanggal_lahir']).dt.days / 365.25
        
        
        # --- Filter di Halaman Utama ---
        st.subheader("Laporan")
        
        df_pemeriksaan['tanggal_pemeriksaan'] = pd.to_datetime(df_pemeriksaan['tanggal_pemeriksaan']).dt.date
        available_dates = sorted(df_pemeriksaan['tanggal_pemeriksaan'].unique(), reverse=True)
        selected_date = st.selectbox(
            "Pilih Tanggal Pelaksanaan Posyandu",
            options=available_dates,
            format_func=lambda d: d.strftime('%d %B %Y'),
            index=None,
            placeholder="Pilih tanggal..."
        )

        if selected_date:
            wilayah_options = ["Lingkungan (Semua RT)"] + sorted(df_warga['rt'].dropna().unique().tolist())
            selected_wilayah = st.selectbox("Tampilkan data untuk wilayah", wilayah_options)

            df_warga_wilayah = df_warga.copy()
            if selected_wilayah != "Lingkungan (Semua RT)":
                df_warga_wilayah = df_warga[df_warga['rt'] == selected_wilayah]
            
            total_warga_wilayah = len(df_warga_wilayah)
            laki_wilayah = df_warga_wilayah[df_warga_wilayah['jenis_kelamin'] == 'L'].shape[0]
            perempuan_wilayah = total_warga_wilayah - laki_wilayah

            # Menghitung jumlah warga bayi usia < 0.5 tahun
            bayi_wilayah = df_warga_wilayah[df_warga_wilayah['usia'] <= 0.5]
            jumlah_bayi_wilayah = bayi_wilayah.shape[0]
            # Memisahkan berdasarkan jenis kelamin
            jumlah_bayi_laki_wilayah = bayi_wilayah[bayi_wilayah['jenis_kelamin'] == 'L'].shape[0]
            jumlah_bayi_perempuan_wilayah = bayi_wilayah[bayi_wilayah['jenis_kelamin'] == 'P'].shape[0]

            # Menghitung jumlah warga baduta usia ? 0.5 tahun dan < 2 tahun
            baduta_wilayah = df_warga_wilayah[(df_warga_wilayah['usia'] > 0.5) & (df_warga_wilayah['usia'] < 2)]
            jumlah_baduta_wilayah = baduta_wilayah.shape[0]
            # Memisahkan berdasarkan jenis kelamin
            jumlah_baduta_laki_wilayah = baduta_wilayah[baduta_wilayah['jenis_kelamin'] == 'L'].shape[0]
            jumlah_baduta_perempuan_wilayah = baduta_wilayah[baduta_wilayah['jenis_kelamin'] == 'P'].shape[0]

            # Menghitung jumlah warga balita usia ?= 2 tahun dan < 5 tahun
            balita_wilayah = df_warga_wilayah[(df_warga_wilayah['usia'] >= 2) & (df_warga_wilayah['usia'] < 5)]
            jumlah_balita_wilayah = balita_wilayah.shape[0]
            # Memisahkan berdasarkan jenis kelamin
            jumlah_balita_laki_wilayah = balita_wilayah[balita_wilayah['jenis_kelamin'] == 'L'].shape[0]
            jumlah_balita_perempuan_wilayah = balita_wilayah[balita_wilayah['jenis_kelamin'] == 'P'].shape[0]

            # Menghitung jumlah warga anak-anak usia ?= 5 tahun dan < 10 tahun
            anak_wilayah = df_warga_wilayah[(df_warga_wilayah['usia'] >= 5) & (df_warga_wilayah['usia'] < 10)]
            jumlah_anak_wilayah = anak_wilayah.shape[0]
            # Memisahkan berdasarkan jenis kelamin
            jumlah_anak_laki_wilayah = anak_wilayah[anak_wilayah['jenis_kelamin'] == 'L'].shape[0]
            jumlah_anak_perempuan_wilayah = anak_wilayah[anak_wilayah['jenis_kelamin'] == 'P'].shape[0]

            # Menghitung jumlah warga remaja usia ?= 10 tahun dan < 20 tahun
            remaja_wilayah = df_warga_wilayah[(df_warga_wilayah['usia'] >= 10) & (df_warga_wilayah['usia'] < 20)]
            jumlah_remaja_wilayah = remaja_wilayah.shape[0]
            # Memisahkan berdasarkan jenis kelamin
            jumlah_remaja_laki_wilayah = remaja_wilayah[remaja_wilayah['jenis_kelamin'] == 'L'].shape[0]
            jumlah_remaja_perempuan_wilayah = remaja_wilayah[remaja_wilayah['jenis_kelamin'] == 'P'].shape[0]

            # Menghitung jumlah warga dewasa usia ?= 20 tahun dan < 60 tahun
            dewasa_wilayah = df_warga_wilayah[(df_warga_wilayah['usia'] >= 20) & (df_warga_wilayah['usia'] < 60)]
            jumlah_dewasa_wilayah = dewasa_wilayah.shape[0]
            # Memisahkan berdasarkan jenis kelamin
            jumlah_dewasa_laki_wilayah = dewasa_wilayah[dewasa_wilayah['jenis_kelamin'] == 'L'].shape[0]
            jumlah_dewasa_perempuan_wilayah = dewasa_wilayah[dewasa_wilayah['jenis_kelamin'] == 'P'].shape[0]

            # Menghitung jumlah warga lansia usia ?= 60 tahun
            lansia_wilayah = df_warga_wilayah[df_warga_wilayah['usia'] >= 60]
            jumlah_lansia_wilayah = lansia_wilayah.shape[0]
            # Memisahkan berdasarkan jenis kelamin
            jumlah_lansia_laki_wilayah = lansia_wilayah[lansia_wilayah['jenis_kelamin'] == 'L'].shape[0]
            jumlah_lansia_perempuan_wilayah = lansia_wilayah[lansia_wilayah['jenis_kelamin'] == 'P'].shape[0]
            
            st.write("#### Demografi Wilayah")
            # col1, col2, col3 = st.columns(3)
            # col1.metric("Total Warga", total_warga_wilayah)
            # col2.metric("👦 Laki-laki", laki_wilayah)
            # col3.metric("👧 Perempuan", perempuan_wilayah)

            
            warna_baris = "#4682B4"  # Steel Blue (lebih terang) #0A2342 Dark Metallic Blue
            if selected_wilayah == "Lingkungan (Semua RT)":
                st.markdown(f"""
                <div style="background-color:{warna_baris}; padding:10px; border-radius:8px; margin-bottom:5px; font-size: 32px;">
                    <strong>Lingkungan Karang Baru Utara</strong><br>
                    Jumlah Warga: {total_warga_wilayah} &nbsp;&nbsp;&nbsp;
                    👦 Laki-laki: {laki_wilayah} &nbsp;&nbsp;&nbsp;
                    👧 Perempuan: {perempuan_wilayah}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background-color:{warna_baris}; padding:10px; border-radius:8px; margin-bottom:5px; font-size: 32px;">
                    <strong>Lingkungan Karang Baru Utara - RT003</strong><br>
                    Jumlah Warga: {total_warga_wilayah} &nbsp;&nbsp;&nbsp;
                    👦 Laki-laki: {laki_wilayah} &nbsp;&nbsp;&nbsp;
                    👧 Perempuan: {perempuan_wilayah}
                </div>
                """, unsafe_allow_html=True)
            
            # r_1col1, r_1col2, r_1col3 = st.columns(3)
            # r_1col1.metric("Bayi (0-6 bln)", jumlah_bayi_wilayah)
            # r_1col2.metric("Laki-laki", jumlah_bayi_laki_wilayah)
            # r_1col3.metric("Perempuan", jumlah_bayi_perempuan_wilayah)

            # r_2col1, r_2col2, r_2col3 = st.columns(3)
            # r_2col1.metric("Baduta (6 bln - <2 thn)", jumlah_baduta_wilayah)
            # r_2col2.metric("Laki-laki", jumlah_baduta_laki_wilayah)
            # r_2col3.metric("Perempuan", jumlah_baduta_perempuan_wilayah)

            # r_3col1, r_3col2, r_3col3 = st.columns(3)
            # r_3col1.metric("Balita (2 - <5 thn)", jumlah_balita_wilayah)
            # r_3col2.metric("Laki-laki", jumlah_balita_laki_wilayah)
            # r_3col3.metric("Perempuan", jumlah_balita_perempuan_wilayah)

            # r_4col1, r_4col2, r_4col3 = st.columns(3)
            # r_4col1.metric("Anak-anak (5 - <10 thn)", jumlah_anak_wilayah)
            # r_4col2.metric("Laki-laki", jumlah_anak_laki_wilayah)
            # r_4col3.metric("Perempuan", jumlah_anak_perempuan_wilayah)

            # r_5col1, r_5col2, r_5col3 = st.columns(3)
            # r_5col1.metric("Remaja (10 - <20 thn)", jumlah_remaja_wilayah)
            # r_5col2.metric("Laki-laki", jumlah_remaja_laki_wilayah)
            # r_5col3.metric("Perempuan", jumlah_remaja_perempuan_wilayah)

            # r_6col1, r_6col2, r_6col3 = st.columns(3)
            # r_6col1.metric("Dewasa (20 - <60 thn)", jumlah_dewasa_wilayah)
            # r_6col2.metric("Laki-laki", jumlah_dewasa_laki_wilayah)
            # r_6col3.metric("Perempuan", jumlah_dewasa_perempuan_wilayah)

            # r_7col1, r_7col2, r_7col3 = st.columns(3)
            # r_7col1.metric("Lansia (20 - <60 thn)", jumlah_lansia_wilayah)
            # r_7col2.metric("Laki-laki", jumlah_lansia_laki_wilayah)
            # r_7col3.metric("Perempuan", jumlah_lansia_perempuan_wilayah)

            #-------------------------------------------------------------------------------------------------------
            # tampilan berwarna di web
            # Data demografi yang sudah dihitung sebelumnya
            baris_demografi = [
                ("Bayi (0-6 bln)", jumlah_bayi_wilayah, jumlah_bayi_laki_wilayah, jumlah_bayi_perempuan_wilayah),
                ("Baduta (6 bln - <2 thn)", jumlah_baduta_wilayah, jumlah_baduta_laki_wilayah, jumlah_baduta_perempuan_wilayah),
                ("Balita (2 - <5 thn)", jumlah_balita_wilayah, jumlah_balita_laki_wilayah, jumlah_balita_perempuan_wilayah),
                ("Anak-anak (5 - <10 thn)", jumlah_anak_wilayah, jumlah_anak_laki_wilayah, jumlah_anak_perempuan_wilayah),
                ("Remaja (10 - <20 thn)", jumlah_remaja_wilayah, jumlah_remaja_laki_wilayah, jumlah_remaja_perempuan_wilayah),
                ("Dewasa (20 - <60 thn)", jumlah_dewasa_wilayah, jumlah_dewasa_laki_wilayah, jumlah_dewasa_perempuan_wilayah),
                ("Lansia (≥60 thn)", jumlah_lansia_wilayah, jumlah_lansia_laki_wilayah, jumlah_lansia_perempuan_wilayah),
            ]

            # Warna berbeda untuk tiap baris
            warna_baris_list = [
                "#e6f7ff",  # biru muda
                "#fff0f5",  # pink muda
                "#e6f7ff",  # biru muda
                "#fff0f5",  # pink muda
                "#e6f7ff",  # biru muda
                "#fff0f5",  # pink muda
                "#e6f7ff",  # biru muda
            ]

            # # Warna berbeda untuk tiap baris
            # warna_baris_list = [
            #     "#e6f7ff",  # biru muda
            #     "#fff0f5",  # pink muda
            #     "#f0fff0",  # hijau pucat
            #     "#ffffe0",  # kuning pucat
            #     "#ffe4e1",  # salmon muda
            #     "#f5f5dc",  # beige
            #     "#e0ffff",  # cyan muda
            # ]

            # Tampilkan setiap baris demografi
            for i, (label, total, laki, perempuan) in enumerate(baris_demografi):
                warna = warna_baris_list[i % len(warna_baris_list)]
                #with st.expander(f"**{label} (Total: {total})**", expanded=False):
                st.markdown(f"""
                <div style="background-color:{warna}; padding:12px 16px; border-radius:10px; margin-bottom:8px; font-size: 16px; font-family: sans-serif;">
                    <strong>{label}</strong><br>
                    👥 Total: <strong>{total}</strong> &nbsp;&nbsp;&nbsp;
                    👦 Laki-laki: <strong>{laki}</strong> &nbsp;&nbsp;&nbsp;
                    👧 Perempuan: <strong>{perempuan}</strong>
                </div>
                """, unsafe_allow_html=True)
            #-------------------------------------------------------------------------------------------------------

            st.write("#### Pilih Kategori")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                kategori_usia_list = ["Semua", "Bayi (0-6 bln)", "Baduta (6 bln - <2 thn)", "Balita (2 - <5 thn)", "Anak-anak (5 - <10 thn)", "Remaja (10 - <20 thn)", "Dewasa (20 - <60 thn)", "Lansia (60+ thn)"]
                selected_kategori = st.selectbox("Kategori Usia", kategori_usia_list)
            with col_f2:
                selected_gender = st.selectbox("Jenis Kelamin", ["Semua", "Laki-laki", "Perempuan"])

            df_warga_final_filter = df_warga_wilayah.copy()
            if selected_gender != "Semua":
                gender_code = "L" if selected_gender == "Laki-laki" else "P"
                df_warga_final_filter = df_warga_final_filter[df_warga_final_filter['jenis_kelamin'] == gender_code]
            if selected_kategori != "Semua":
                if selected_kategori == "Bayi (0-6 bln)": df_warga_final_filter = df_warga_final_filter[df_warga_final_filter['usia'] <= 0.5]
                elif selected_kategori == "Baduta (6 bln - <2 thn)": df_warga_final_filter = df_warga_final_filter[(df_warga_final_filter['usia'] > 0.5) & (df_warga_final_filter['usia'] < 2)]
                elif selected_kategori == "Balita (2 - <5 thn)": df_warga_final_filter = df_warga_final_filter[(df_warga_final_filter['usia'] >= 2) & (df_warga_final_filter['usia'] < 5)]
                elif selected_kategori == "Anak-anak (5 - <10 thn)": df_warga_final_filter = df_warga_final_filter[(df_warga_final_filter['usia'] >= 5) & (df_warga_final_filter['usia'] < 10)]
                elif selected_kategori == "Remaja (10 - <20 thn)": df_warga_final_filter = df_warga_final_filter[(df_warga_final_filter['usia'] >= 10) & (df_warga_final_filter['usia'] < 20)]
                elif selected_kategori == "Dewasa (20 - <60 thn)": df_warga_final_filter = df_warga_final_filter[(df_warga_final_filter['usia'] >= 20) & (df_warga_final_filter['usia'] < 60)]
                elif selected_kategori == "Lansia (60+ thn)": df_warga_final_filter = df_warga_final_filter[df_warga_final_filter['usia'] >= 60]

            st.divider()
            st.subheader(f"Laporan untuk {selected_date.strftime('%d %B %Y')}")
            
            df_pemeriksaan_harian = df_pemeriksaan[
                (df_pemeriksaan['tanggal_pemeriksaan'] == selected_date) &
                (df_pemeriksaan['warga_id'].isin(df_warga_final_filter['id']))
            ]

            total_warga_terfilter = len(df_warga_final_filter)
            hadir_hari_itu = len(df_pemeriksaan_harian)
            partisipasi_hari_itu = (hadir_hari_itu / total_warga_terfilter * 100) if total_warga_terfilter > 0 else 0
            
            col_m1, col_m2 = st.columns(2)
            col_m1.metric("Jumlah Kunjungan", f"{hadir_hari_itu} dari {total_warga_terfilter} warga")
            col_m2.metric("Tingkat Partisipasi", f"{partisipasi_hari_itu:.1f}%")

            if hadir_hari_itu > 0:
                col_pie, col_empty = st.columns([1, 1])
                with col_pie:
                    tidak_hadir_hari_itu = total_warga_terfilter - hadir_hari_itu
                    labels = 'Hadir', 'Tidak Hadir'
                    sizes = [hadir_hari_itu, tidak_hadir_hari_itu]
                    colors = ['#4CAF50', '#FFC107']
                    
                    fig_pie, ax_pie = plt.subplots(figsize=(4, 4))
                    ax_pie.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors, wedgeprops={'edgecolor': 'white'})
                    ax_pie.axis('equal'); st.pyplot(fig_pie)

                st.write("#### Data Rinci Kunjungan")
                # --- PERBAIKAN 2: Menggabungkan dengan df_warga yang memiliki semua kolom ---
                df_laporan_harian = pd.merge(df_pemeriksaan_harian, df_warga, left_on='warga_id', right_on='id', how='left')
                st.dataframe(df_laporan_harian[['nama_lengkap', 'rt', 'blok', 'tensi_sistolik', 'tensi_diastolik', 'berat_badan_kg', 'gula_darah', 'kolesterol']])
            else:
                st.info("Tidak ada data kehadiran yang cocok dengan filter yang dipilih pada tanggal ini.")

            st.divider()
            st.subheader("Tren Kunjungan")
            df_pemeriksaan_tren = df_pemeriksaan[df_pemeriksaan['warga_id'].isin(df_warga_final_filter['id'])]
            if not df_pemeriksaan_tren.empty:
                kehadiran_per_hari = df_pemeriksaan_tren.groupby('tanggal_pemeriksaan').size().reset_index(name='jumlah_hadir')
                fig_tren, ax_tren = plt.subplots(figsize=(10, 4))
                ax_tren.plot(kehadiran_per_hari['tanggal_pemeriksaan'], kehadiran_per_hari['jumlah_hadir'], marker='o', linestyle='-')
                ax_tren.set_ylabel("Jumlah Kunjungan"); ax_tren.grid(True, linestyle='--', alpha=0.6)
                plt.xticks(rotation=45); fig_tren.tight_layout(); st.pyplot(fig_tren)
            else:
                st.info("Tidak ada data pemeriksaan untuk ditampilkan di grafik tren sesuai filter populasi.")

            st.divider()
            if hadir_hari_itu > 0:
                # --- PERBAIKAN: Menggunakan filter yang benar untuk PDF ---
                pdf_buffer = generate_pdf_report(
                    filters={"selected_date_str": selected_date.strftime('%d %B %Y'), "rt": selected_wilayah, "kategori": selected_kategori, "gender": selected_gender, "tgl_mulai": selected_date, "tgl_akhir": selected_date},
                    metrics={"total_warga": total_warga_terfilter, "hadir_hari_ini": hadir_hari_itu, "partisipasi_hari_ini": partisipasi_hari_itu},
                    df_rinci=df_laporan_harian[['nama_lengkap', 'rt', 'blok', 'tensi_sistolik', 'tensi_diastolik', 'berat_badan_kg']],
                    fig_tren=fig_tren,
                    fig_pie=fig_pie
                )
                st.download_button(
                    label="📥 Unduh Laporan PDF",
                    data=pdf_buffer,
                    file_name=f"Laporan Posyandu {selected_date.strftime('%Y-%m-%d')}.pdf",
                    mime="application/pdf"
                )


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
        fig, ax = plt.subplots(figsize=(6, 4)); ax.plot(df_pemeriksaan['tanggal_pemeriksaan'], df_pemeriksaan['tensi_sistolik'], marker='o', label='Sistolik'); ax.plot(df_pemeriksaan['tanggal_pemeriksaan'], df_pemeriksaan['tensi_diastolik'], marker='o', label='Diastolik'); ax.set_title("Tren Tensi Darah"); ax.set_ylabel("mmHg"); ax.legend(); ax.grid(True, linestyle=':'); plt.xticks(rotation=45); fig.tight_layout(); st.pyplot(fig)
        fig, ax = plt.subplots(figsize=(6, 4)); ax.plot(df_pemeriksaan['tanggal_pemeriksaan'], df_pemeriksaan['gula_darah'], marker='o', color='g'); ax.set_title("Tren Gula Darah"); ax.set_ylabel("mg/dL"); ax.grid(True, linestyle=':'); plt.xticks(rotation=45); fig.tight_layout(); st.pyplot(fig)
    with col2:
        fig, ax = plt.subplots(figsize=(6, 4)); ax.plot(df_pemeriksaan['tanggal_pemeriksaan'], df_pemeriksaan['berat_badan_kg'], marker='o', color='r'); ax.set_title("Tren Berat Badan"); ax.set_ylabel("kg"); ax.grid(True, linestyle=':'); plt.xticks(rotation=45); fig.tight_layout(); st.pyplot(fig)
        fig, ax = plt.subplots(figsize=(6, 4)); ax.plot(df_pemeriksaan['tanggal_pemeriksaan'], df_pemeriksaan['kolesterol'], marker='o', color='purple'); ax.set_title("Tren Kolesterol"); ax.set_ylabel("mg/dL"); ax.grid(True, linestyle=':'); plt.xticks(rotation=45); fig.tight_layout(); st.pyplot(fig)

# ==============================================================================
# BAGIAN UTAMA APLIKASI (MAIN)
# ==============================================================================

st.set_page_config(page_title="Posyandu Mawar", layout="wide")
st.sidebar.title("🏥 Aplikasi Posyandu Mawar - KBU")

page_options = {
    "👨‍👩‍👧‍👦 Manajemen Data Warga": page_manajemen_warga,
    "🗓️ Input Kunjungan & Pemeriksaan": page_input_pemeriksaan,
    "📈 Dashboard & Laporan": page_dashboard
}

selected_page = st.sidebar.radio("Pilih Halaman:", page_options.keys())
page_options[selected_page]()