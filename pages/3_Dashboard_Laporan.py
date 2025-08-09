# pages/3_Dashboard_Laporan.py

import streamlit as st
import pandas as pd
import plotly.express as px # <--- IMPORT PUSTAKA BARU
import matplotlib.pyplot as plt
from supabase import create_client
from datetime import date, datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT


# --- KONEKSI & KEAMANAN ---
st.set_page_config(page_title="Dashboard & Laporan", page_icon="📈", layout="wide")

if not st.session_state.get("authenticated", False):
    st.error("🔒 Anda harus login untuk mengakses halaman ini.")
    st.stop()

supabase = st.session_state.get('supabase_client')
if not supabase:
    st.error("Koneksi Supabase tidak ditemukan. Silakan login kembali.")
    st.stop()

# --- FUNGSI PEMBUAT GRAFIK ---
def buat_grafik_gender(laki, perempuan, warna_laki='#6495ED', warna_perempuan='#FFB6C1'):
    """Membuat dan mengembalikan objek figure Matplotlib untuk grafik gender."""
    if laki == 0 and perempuan == 0:
        return None # Tidak perlu membuat grafik jika tidak ada data

    fig, ax = plt.subplots(figsize=(4, 0.8)) # Ukuran grafik kecil dan horizontal
    data = {'Laki-laki': laki, 'Perempuan': perempuan}
    kategori = list(data.keys())
    jumlah = list(data.values())

    # --- PERUBAHAN UTAMA: Gunakan ax.bar() untuk grafik vertikal ---
    ax.bar(kategori, jumlah, color=[warna_laki, warna_perempuan], width=0.6)
    
    # Menghilangkan frame dan sumbu Y
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.yaxis.set_ticks([]) # Sembunyikan angka di sumbu y

    # Menyesuaikan posisi teks agar berada di dalam bar vertikal
    for i, value in enumerate(jumlah):
        if value > 0:
            ax.text(i, value / 2, str(value), ha='center', va='center', color='white', fontweight='bold')
    
    # Atur agar tidak ada margin ekstra
    fig.tight_layout(pad=0)
    return fig
    # --- 

# --- FUNGSI PEMBANTU PDF (VERSI MODIFIKASI) ---
# --- FUNGSI PEMBANTU PDF (VERSI MODIFIKASI) ---
# <-- MODIFIKASI BESAR DI SINI -->
# Fungsi ini perlu dirombak total agar lebih fleksibel.
# 1. Ubah inputnya agar tidak menerima banyak variabel, tetapi satu objek 'report_data' yang berisi semua yang dibutuhkan.
# 2. Tambahkan fungsi 'helper' untuk mengubah SEMUA jenis gambar (Matplotlib & Plotly) menjadi format yang bisa dibaca PDF.
# 3. Ubah logika pembuatan tabel agar bisa membuat tabel secara berulang untuk SETIAP kategori usia, bukan hanya satu tabel besar.

# CONTOH FUNGSI PDF YANG SEHARUSNYA (Ganti seluruh fungsi di bawah dengan ini):
def generate_pdf_report_baru(report_data):
    """
    Membuat laporan PDF dari data yang sudah disiapkan dalam satu objek.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=inch*0.8, leftMargin=inch*0.8, topMargin=inch*0.8, bottomMargin=inch*0.8)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='H2_Dark', parent=styles['h2'], textColor=colors.darkslategray))
    styles.add(ParagraphStyle(name='H3_Dark', parent=styles['h3'], textColor=colors.darkslategray))
    elements = []

    # Fungsi helper untuk mengubah semua jenis grafik menjadi gambar PDF
    def convert_fig_to_image(fig, width, height):
        if fig is None: return Spacer(0, 0)
        img_buffer = BytesIO()
        if 'plotly' in str(type(fig)):
            fig.write_image(img_buffer, format='png', scale=3)
        elif 'matplotlib' in str(type(fig)):
            fig.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
            plt.close(fig) # Penting agar tidak menumpuk di memori
        img_buffer.seek(0)
        return Image(img_buffer, width=width, height=height)

    # --- Header (tetap sama) ---
    elements.append(Paragraph("Laporan Posyandu Mawar - KBU", styles['h1']))
    # ... (kode header dan filter lainnya bisa disalin dari kode lama)

    # --- Menambahkan Semua Grafik (Plotly & Matplotlib) ---
    # Sunburst
    elements.append(Paragraph("Diagram Komposisi Warga", styles['H2_Dark']))
    elements.append(convert_fig_to_image(report_data['figures']['komposisi_warga'], width=6*inch, height=4*inch))
    # Donat (Matplotlib) - dibuat dalam bentuk tabel agar rapi
    elements.append(Paragraph("Tingkat Partisipasi Berdasarkan Usia", styles['H2_Dark']))
    donut_charts = report_data['figures']['partisipasi_kategori']
    table_data = []
    row = []
    for fig in donut_charts:
        row.append(convert_fig_to_image(fig, width=3*inch, height=3*inch))
        if len(row) == 2:
            table_data.append(row)
            row = []
    if row: table_data.append(row)
    if table_data: elements.append(Table(table_data, colWidths=[3.25*inch, 3.25*inch]))
    
    # --- FUNGSI UNTUK MEMBUAT TABEL DATA PER KATEGORI SECARA DINAMIS ---
    def build_category_tables(data_dict, title_prefix, header_color):
        elements.append(PageBreak())
        elements.append(Paragraph(title_prefix, styles['h2']))
        elements.append(Spacer(1, 0.2*inch))
        
        has_data = False
        for category_name, df_category in data_dict.items():
            if not df_category.empty:
                has_data = True
                elements.append(Paragraph(f"Kategori: <b>{category_name}</b>", styles['H3_Dark']))
                df_display = df_category.copy()
                df_display.insert(0, "No", range(1, len(df_display) + 1))
                table_data = [df_display.columns.to_list()] + df_display.values.tolist()
                data_table = Table(table_data, repeatRows=1) # Tambahkan style di sini
                elements.append(data_table)
                elements.append(Spacer(1, 0.3*inch))
        
        if not has_data:
            elements.append(Paragraph("Tidak ada data untuk ditampilkan.", styles['Normal']))

    # Panggil fungsi di atas untuk data hadir dan tidak hadir
    build_category_tables(report_data['dataframes']['hadir_per_kategori'], "Data Rinci Warga Hadir", colors.darkslategray)
    build_category_tables(report_data['dataframes']['tidak_hadir_per_kategori'], "Data Warga Tidak Hadir", colors.darkred)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# Fungsi untuk menentukan kategori usia, digunakan di banyak tempat
def get_kategori(usia):
    if usia <= 0.5: return "Bayi (0-6 bln)"
    if usia <= 2: return "Baduta (>6 bln - 2 thn)"
    if usia <= 5: return "Balita (>2 - 5 thn)"
    if usia < 6: return "Anak Pra-Sekolah (>5 - <6 thn)"
    if usia <= 18: return "Anak Usia Sekolah dan Remaja (6 - 18 thn)"
    if usia < 60: return "Dewasa (>18 - <60 thn)"
    return "Lansia (≥60 thn)"
# --- FUNGSI HALAMAN UTAMA ---
# GANTI SELURUH FUNGSI page_dashboard ANDA DENGAN INI

# GANTI SELURUH FUNGSI page_dashboard ANDA DENGAN INI

# GANTI SELURUH FUNGSI page_dashboard ANDA DENGAN INI

def page_dashboard():
    st.markdown(
        """
        <div style="background-color:#0A2342; padding:16px; border-radius:10px;">
            <h2 style="color:white; margin:0;">📈 Dashboard & Laporan</h2>
        </div>
        """,
        unsafe_allow_html=True
    )
    if not supabase: return

    try:
        warga_response = supabase.table("warga").select("*").execute()
        pemeriksaan_response = supabase.table("pemeriksaan").select("*").execute()

        if not warga_response.data:
            st.info("Belum ada data warga untuk ditampilkan di laporan.")
            return

        df_warga = pd.DataFrame(warga_response.data)
        df_pemeriksaan = pd.DataFrame(pemeriksaan_response.data) if pemeriksaan_response.data else pd.DataFrame()
        
        st.subheader("Filter Laporan")
        
        if df_pemeriksaan.empty:
            st.warning("Belum ada data pemeriksaan yang bisa ditampilkan.")
            return

        df_pemeriksaan['tanggal_pemeriksaan'] = pd.to_datetime(df_pemeriksaan['tanggal_pemeriksaan']).dt.date
        available_dates = sorted(df_pemeriksaan['tanggal_pemeriksaan'].unique(), reverse=True)
        selected_date = st.selectbox(
            "Pilih Tanggal Pelaksanaan Posyandu",
            options=available_dates,
            format_func=lambda d: d.strftime('%d %B %Y'),
            index=0 if available_dates else None,
            placeholder="Pilih tanggal..."
        )
        
        if selected_date:
            df_warga['tanggal_lahir'] = pd.to_datetime(df_warga['tanggal_lahir'])
            df_warga['usia'] = (pd.to_datetime(selected_date) - df_warga['tanggal_lahir']).dt.days / 365.25

            kategori_usia_list = [
                "Tampilkan Semua", "Bayi (0-6 bln)", "Baduta (>6 bln - 2 thn)", "Balita (>2 - 5 thn)", 
                "Anak Pra-Sekolah (>5 - <6 thn)", "Anak Usia Sekolah dan Remaja (6 - 18 thn)", 
                "Dewasa (>18 - <60 thn)", "Lansia (≥60 thn)"
            ]

            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                wilayah_options = ["Lingkungan (Semua RT)"] + sorted(df_warga['rt'].dropna().unique().tolist())
                selected_wilayah = st.selectbox("Wilayah", wilayah_options)
            with col_f2:
                selected_gender = st.selectbox("Jenis Kelamin", ["Semua", "Laki-laki", "Perempuan"])
            with col_f3:
                selected_kategori = st.selectbox("Kategori Usia", kategori_usia_list)

            df_warga_wilayah = df_warga.copy()
            if selected_wilayah != "Lingkungan (Semua RT)":
                df_warga_wilayah = df_warga[df_warga['rt'] == selected_wilayah]
            
            # --- Bagian Demografi Wilayah (TETAP SAMA) ---
            # ... (Kode demografi tidak perlu diubah) ...

            # --- Perhitungan Demografi ---
            total_warga_wilayah = len(df_warga_wilayah)
            laki_wilayah = df_warga_wilayah[df_warga_wilayah['jenis_kelamin'] == 'L'].shape[0]
            perempuan_wilayah = total_warga_wilayah - laki_wilayah

            bayi_wilayah = df_warga_wilayah[df_warga_wilayah['usia'] <= 0.5]
            jumlah_bayi_wilayah = bayi_wilayah.shape[0]
            jumlah_bayi_laki_wilayah = bayi_wilayah[bayi_wilayah['jenis_kelamin'] == 'L'].shape[0]
            jumlah_bayi_perempuan_wilayah = bayi_wilayah[bayi_wilayah['jenis_kelamin'] == 'P'].shape[0]

            baduta_wilayah = df_warga_wilayah[(df_warga_wilayah['usia'] > 0.5) & (df_warga_wilayah['usia'] <= 2)]
            jumlah_baduta_wilayah = baduta_wilayah.shape[0]
            jumlah_baduta_laki_wilayah = baduta_wilayah[baduta_wilayah['jenis_kelamin'] == 'L'].shape[0]
            jumlah_baduta_perempuan_wilayah = baduta_wilayah[baduta_wilayah['jenis_kelamin'] == 'P'].shape[0]

            balita_wilayah = df_warga_wilayah[(df_warga_wilayah['usia'] > 2) & (df_warga_wilayah['usia'] <= 5)]
            jumlah_balita_wilayah = balita_wilayah.shape[0]
            jumlah_balita_laki_wilayah = balita_wilayah[balita_wilayah['jenis_kelamin'] == 'L'].shape[0]
            jumlah_balita_perempuan_wilayah = balita_wilayah[balita_wilayah['jenis_kelamin'] == 'P'].shape[0]

            anak_wilayah = df_warga_wilayah[(df_warga_wilayah['usia'] > 5) & (df_warga_wilayah['usia'] < 6)]
            jumlah_anak_wilayah = anak_wilayah.shape[0]
            jumlah_anak_laki_wilayah = anak_wilayah[anak_wilayah['jenis_kelamin'] == 'L'].shape[0]
            jumlah_anak_perempuan_wilayah = anak_wilayah[anak_wilayah['jenis_kelamin'] == 'P'].shape[0]

            remaja_wilayah = df_warga_wilayah[(df_warga_wilayah['usia'] >= 6) & (df_warga_wilayah['usia'] <= 18)]
            jumlah_remaja_wilayah = remaja_wilayah.shape[0]
            jumlah_remaja_laki_wilayah = remaja_wilayah[remaja_wilayah['jenis_kelamin'] == 'L'].shape[0]
            jumlah_remaja_perempuan_wilayah = remaja_wilayah[remaja_wilayah['jenis_kelamin'] == 'P'].shape[0]

            dewasa_wilayah = df_warga_wilayah[(df_warga_wilayah['usia'] > 18) & (df_warga_wilayah['usia'] < 60)]
            jumlah_dewasa_wilayah = dewasa_wilayah.shape[0]
            jumlah_dewasa_laki_wilayah = dewasa_wilayah[dewasa_wilayah['jenis_kelamin'] == 'L'].shape[0]
            jumlah_dewasa_perempuan_wilayah = dewasa_wilayah[dewasa_wilayah['jenis_kelamin'] == 'P'].shape[0]

            lansia_wilayah = df_warga_wilayah[df_warga_wilayah['usia'] >= 60]
            jumlah_lansia_wilayah = lansia_wilayah.shape[0]
            jumlah_lansia_laki_wilayah = lansia_wilayah[lansia_wilayah['jenis_kelamin'] == 'L'].shape[0]
            jumlah_lansia_perempuan_wilayah = lansia_wilayah[lansia_wilayah['jenis_kelamin'] == 'P'].shape[0]
            
            st.write("#### Demografi Wilayah")
            
            warna_baris = "#4682B4"
            rt_label = f"RT{selected_wilayah.zfill(3)}" if selected_wilayah.isdigit() else "Lingkungan Karang Baru Utara"
            if selected_wilayah == "Lingkungan (Semua RT)":
                 rt_label = "Lingkungan Karang Baru Utara"

            # --- LAYOUT DUA KOLOM ---
            kolom_kiri, kolom_kanan = st.columns([4, 3])  # 2:1 rasio lebar

            # --- TEKS DI KOLOM KIRI ---
            with kolom_kiri:
                st.markdown(f"""
                    <div style="background-color:{warna_baris}; color:white; padding:10px; border-radius:8px; margin-bottom:10px; font-size: 32px;">
                        <strong>{rt_label}</strong><br>
                        <span style="font-size: 18px;">
                            Jumlah Warga: {total_warga_wilayah} &nbsp;&nbsp;&nbsp;
                            👦 Laki-laki: {laki_wilayah} &nbsp;&nbsp;&nbsp;
                            👧 Perempuan: {perempuan_wilayah}
                        </span>
                    </div>
                """, unsafe_allow_html=True)

            # --- GRAFIK DI KOLOM KANAN ---
            with kolom_kanan:
                with st.container(border=True):
                    fig = buat_grafik_gender(laki_wilayah, perempuan_wilayah)
                    if fig is not None:
                        st.pyplot(fig)


            # --- [ AWAL BLOK KODE BARU UNTUK SUNBURST KOMPOSISI WARGA ] ---
            # --- [ BLOK KODE SUNBURST KOMPOSISI WARGA YANG DIPERBAIKI ] ---
            st.subheader("Komposisi Warga")

            # 1. Siapkan data untuk visualisasi
            df_komposisi = df_warga_wilayah.copy()
            df_komposisi['kategori_usia'] = df_komposisi['usia'].apply(get_kategori)
            df_komposisi['jenis_kelamin'] = df_komposisi['jenis_kelamin'].map({'L': 'Laki-laki', 'P': 'Perempuan'}).fillna('N/A')
            df_komposisi['count'] = 1 

            # Filter berdasarkan gender jika dipilih
            if selected_gender != "Semua":
                df_komposisi = df_komposisi[df_komposisi['jenis_kelamin'] == selected_gender]

            # 2. Buat dan tampilkan diagram Sunburst untuk Komposisi Warga
            if not df_komposisi.empty:
                # Tambahkan kolom untuk label total sebagai pusat diagram
                total_warga = len(df_komposisi)
                df_komposisi['total_label'] = f'Total Warga: {total_warga}'
                
                fig_sunburst_komposisi = px.sunburst(
                    df_komposisi,
                    # Urutan path diubah sesuai permintaan: Total -> Kategori Usia -> Jenis Kelamin
                    path=['total_label', 'kategori_usia', 'jenis_kelamin'], # Menentukan jalur hierarki dari pusat ke luar
                    values='count', # Menentukan nilai yang merepresentasikan ukuran irisan
                    title='Diagram Komposisi Warga (Total > Kategori Usia > Jenis Kelamin)',
                    # Mewarnai berdasarkan kategori usia untuk membedakan segmen utama
                    color='kategori_usia', # (Opsional) Memberi warna berdasarkan nilai lain
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_sunburst_komposisi.update_layout(margin=dict(t=50, l=25, r=25, b=25))
                fig_sunburst_komposisi.update_traces(textinfo='label+percent parent', insidetextorientation='radial')
                st.plotly_chart(fig_sunburst_komposisi, use_container_width=True)
            else:
                st.info("Tidak ada data komposisi warga yang cocok dengan filter.")
            # --- [ AKHIR BLOK KODE BARU ] ---

            #------------------- [ AWAL PERUBAHAN UTAMA ] -------------------
            baris_demografi = [
                ("Bayi (0-6 bln)", jumlah_bayi_wilayah, jumlah_bayi_laki_wilayah, jumlah_bayi_perempuan_wilayah),
                ("Baduta (>6 bln - 2 thn)", jumlah_baduta_wilayah, jumlah_baduta_laki_wilayah, jumlah_baduta_perempuan_wilayah),
                ("Balita (>2 - 5 thn)", jumlah_balita_wilayah, jumlah_balita_laki_wilayah, jumlah_balita_perempuan_wilayah),
                ("Anak pra-Sekolah (>5 - <6 thn)", jumlah_anak_wilayah, jumlah_anak_laki_wilayah, jumlah_anak_perempuan_wilayah),
                ("Anak Usia Sekolah dan Remaja (6 - 18 thn)", jumlah_remaja_wilayah, jumlah_remaja_laki_wilayah, jumlah_remaja_perempuan_wilayah),
                ("Dewasa (>18 - <60 thn)", jumlah_dewasa_wilayah, jumlah_dewasa_laki_wilayah, jumlah_dewasa_perempuan_wilayah),
                ("Lansia (≥60 thn)", jumlah_lansia_wilayah, jumlah_lansia_laki_wilayah, jumlah_lansia_perempuan_wilayah),
            ]

            # Tampilkan setiap baris demografi dengan grafik
            # GANTI SELURUH BLOK 'for' ANDA DENGAN YANG INI

            with st.expander("Lihat Rinci Data Komposisi Warga"):
                # Tampilkan setiap baris demografi dengan layout kolom dan container
                for label, total, laki, perempuan in baris_demografi:
                    
                    # Buat dua kolom: satu untuk teks, satu untuk grafik
                    col_teks, col_grafik = st.columns([2, 1.5])

                    # Gunakan kolom kiri untuk menampilkan semua teks
                    with col_teks:
                        # Gunakan container bawaan Streamlit untuk membuat kotak
                        with st.container(border=True):
                            st.markdown(f"**{label}**") # Judul kategori
                            st.markdown(f"👥 Total: **{total}**")
                            st.markdown(f"👦 Laki-laki: **{laki}**")
                            st.markdown(f"👧 Perempuan: **{perempuan}**")

                    # Gunakan kolom kanan untuk menampilkan grafik
                    with col_grafik:
                        with st.container(border=True):

                            st.markdown(
                                """
                                <div style="display: flex; align-items: center; justify-content: center; height: 58px;">
                                """,
                                unsafe_allow_html=True
                            )
                            # Panggil fungsi grafik Anda
                            fig_gender = buat_grafik_gender(laki, perempuan) # Pastikan nama fungsi ini benar
                            if fig_gender:
                                st.pyplot(fig_gender, use_container_width=True)
                                plt.close(fig_gender)

                    # Beri sedikit spasi antar kategori
                    st.write("")
                #------------------- [ AKHIR PERUBAHAN UTAMA ] -------------------


            st.divider()

            # --- [ BLOK KODE SUNBURST PARTISIPASI YANG DIPERBAIKI ] ---
            st.subheader("Ringkasan Partisipasi Warga yang Hadir")

            # 1. Ambil data warga yang hadir saja
            df_pemeriksaan_harian = df_pemeriksaan[df_pemeriksaan['tanggal_pemeriksaan'] == selected_date]
            id_hadir_keseluruhan = df_pemeriksaan_harian['warga_id'].unique()
            df_partisipasi = df_warga_wilayah[df_warga_wilayah['id'].isin(id_hadir_keseluruhan)].copy()

            # 2. Siapkan kolom yang diperlukan untuk diagram
            # Pastikan fungsi get_kategori sudah didefinisikan sebelumnya di dalam page_dashboard()
            df_partisipasi['kategori_usia'] = df_partisipasi['usia'].apply(get_kategori)
            df_partisipasi['jenis_kelamin'] = df_partisipasi['jenis_kelamin'].map({'L': 'Laki-laki', 'P': 'Perempuan'}).fillna('N/A')
            df_partisipasi['rt'] = 'RT ' + df_partisipasi['rt'].astype(str)
            df_partisipasi['count'] = 1 

            # 3. Filter berdasarkan gender jika dipilih di filter utama
            if selected_gender != "Semua":
                df_partisipasi = df_partisipasi[df_partisipasi['jenis_kelamin'] == selected_gender]

            # 4. Buat dan tampilkan diagram Sunburst
            if not df_partisipasi.empty:
                # Tambahkan kolom untuk label total sebagai pusat diagram
                total_hadir = len(df_partisipasi)
                df_partisipasi['total_label'] = f'Total Hadir: {total_hadir}'

                fig_sunburst_partisipasi = px.sunburst(
                    df_partisipasi,
                    # Urutan path diubah untuk menempatkan total di tengah
                    path=['total_label', 'rt', 'kategori_usia', 'jenis_kelamin'],
                    values='count',
                    title='Diagram Partisipasi Warga Hadir (Total > RT > Kategori Usia > Jenis Kelamin)',
                    # Mewarnai berdasarkan RT untuk membedakan wilayah
                    color='rt',
                    color_discrete_sequence=px.colors.qualitative.Antique
                )
                fig_sunburst_partisipasi.update_layout(margin=dict(t=50, l=25, r=25, b=25))
                fig_sunburst_partisipasi.update_traces(
                    textinfo='label+percent parent', 
                    insidetextorientation='radial'
                )
                st.plotly_chart(fig_sunburst_partisipasi, use_container_width=True)
            else:
                st.info("Tidak ada data partisipasi (hadir) yang cocok dengan filter untuk ditampilkan.")



            st.divider()
            # --- [ AKHIR DARI BLOK KODE BARU ] ---


            # --- [ AWAL PERUBAHAN UTAMA: DIAGRAM TINGKAT PARTISIPASI ] ---
            
            st.subheader("Tingkat Partisipasi Berdasarkan Usia")

            df_pemeriksaan_harian = df_pemeriksaan[df_pemeriksaan['tanggal_pemeriksaan'] == selected_date]
            df_merged = pd.merge(df_pemeriksaan_harian, df_warga_wilayah, left_on='warga_id', right_on='id', how='inner')
            
            if selected_gender != "Semua":
                gender_code = "L" if selected_gender == "Laki-laki" else "P"
                df_warga_wilayah_gender = df_warga_wilayah[df_warga_wilayah['jenis_kelamin'] == gender_code]
                df_merged_gender = df_merged[df_merged['jenis_kelamin'] == gender_code]
            else:
                df_warga_wilayah_gender = df_warga_wilayah
                df_merged_gender = df_merged

            kategori_usia_defs = {
                "Bayi (0-6 bln)": (0, 0.5), "Baduta (>6 bln - 2 thn)": (0.5, 2), "Balita (>2 - 5 thn)": (2, 5),
                "Anak Pra-Sekolah (>5 - <6 thn)": (5, 6), "Anak Usia Sekolah dan Remaja (6 - 18 thn)": (6, 18),
                "Dewasa (>18 - <60 thn)": (18, 60), "Lansia (≥60 thn)": (60, 200)
            }
            
            # # Fungsi untuk menentukan kategori usia, digunakan di banyak tempat
            # def get_kategori(usia):
            #     if usia <= 0.5: return "Bayi (0-6 bln)"
            #     if usia <= 2: return "Baduta (>6 bln - 2 thn)"
            #     if usia <= 5: return "Balita (>2 - 5 thn)"
            #     if usia < 6: return "Anak Pra-Sekolah (>5 - <6 thn)"
            #     if usia <= 18: return "Anak Usia Sekolah dan Remaja (6 - 18 thn)"
            #     if usia < 60: return "Dewasa (>18 - <60 thn)"
            #     return "Lansia (≥60 thn)"
            
            # Buat kolom untuk menata diagram
            donut_figs_for_pdf = [] # Buat list kosong ini sebelum loop
            cols = st.columns(4)
            col_idx = 0

            for nama_kategori, (usia_min, usia_max) in kategori_usia_defs.items():
                
                # 1. Hitung TOTAL warga di kategori ini
                warga_kategori = df_warga_wilayah_gender[df_warga_wilayah_gender['usia'].apply(lambda x: usia_min < x <= usia_max if nama_kategori not in ["Bayi (0-6 bln)"] else x <= usia_max)]
                total_warga_kategori = len(warga_kategori)
                
                if total_warga_kategori > 0:
                    # 2. Hitung yang HADIR di kategori ini
                    hadir_kategori = df_merged_gender[df_merged_gender['usia'].apply(lambda x: usia_min < x <= usia_max if nama_kategori not in ["Bayi (0-6 bln)"] else x <= usia_max)]
                    jumlah_hadir = len(hadir_kategori)
                    jumlah_tidak_hadir = total_warga_kategori - jumlah_hadir
                    
                    # 3. Hitung persentase partisipasi
                    partisipasi = (jumlah_hadir / total_warga_kategori * 100) if total_warga_kategori > 0 else 0
                    
                    # 4. Buat Donut Chart
                    with cols[col_idx]:
                        fig, ax = plt.subplots(figsize=(3, 3))
                        ax.pie(
                            [jumlah_hadir, jumlah_tidak_hadir], 
                            labels=['Hadir', 'Tidak Hadir'], 
                            autopct=lambda p: '{:.0f}'.format(p * (jumlah_hadir+jumlah_tidak_hadir) / 100), # Menampilkan jumlah absolut
                            startangle=90, 
                            colors=['#4CAF50', '#FFC107'],
                            wedgeprops=dict(width=0.4)
                        )
                        # Tambahkan teks persentase di tengah
                        ax.text(0, 0, f"{partisipasi:.1f}%", ha='center', va='center', fontsize=20, fontweight='bold')
                        ax.set_title(nama_kategori, fontsize=10)
                        st.pyplot(fig)
                        # TAMBAHKAN BARIS INI untuk menyimpan figurnya
                        donut_figs_for_pdf.append(fig)
                    
                    #col_idx = (col_idx + 1) % 4
                    col_idx += 1
            
            # Tambahkan kolom kategori usia ke dataframe gabungan untuk filtering di bawah
            if not df_merged.empty:
                df_merged['kategori_usia'] = df_merged['usia'].apply(get_kategori)

            # --- [ AKHIR PERUBAHAN UTAMA ] ---
            
            st.divider()

            with st.expander("Lihat Data Rinci Warga yang Hadir Posyandu"):

                st.subheader(f"Data Rinci Warga yang Hadir pada {selected_date.strftime('%d %B %Y')}")
                
                ada_data_kunjungan = False
                if selected_kategori == "Tampilkan Semua":
                    for nama_kategori, _ in kategori_usia_defs.items():
                        df_kategori = df_merged[df_merged['kategori_usia'] == nama_kategori]
                        if not df_kategori.empty:
                            ada_data_kunjungan = True
                            st.markdown(f"#### {nama_kategori}")
                            df_display = df_kategori.reset_index(drop=True)
                            df_display.index += 1 # Membuat indeks mulai dari 1
                            st.dataframe(df_display[['nama_lengkap', 'rt', 'blok', 'tensi_sistolik', 'tensi_diastolik', 'berat_badan_kg', 'gula_darah', 'kolesterol']], use_container_width=True)
                else:
                    df_kategori = df_merged[df_merged['kategori_usia'] == selected_kategori]
                    if not df_kategori.empty:
                        ada_data_kunjungan = True
                        st.markdown(f"#### Menampilkan Kategori: {selected_kategori}")
                        df_display = df_kategori.reset_index(drop=True)
                        df_display.index += 1 # Membuat indeks mulai dari 1
                        st.dataframe(df_display[['nama_lengkap', 'rt', 'blok', 'tensi_sistolik', 'tensi_diastolik', 'berat_badan_kg', 'gula_darah', 'kolesterol']], use_container_width=True)

                if not ada_data_kunjungan:
                    st.info("Tidak ada data kunjungan (hadir) yang cocok dengan filter.")

            # st.divider()
            
            with st.expander("Lihat Data Warga yang Tidak Hadir Posyandu"):
                # --- PERBAIKAN DI SINI ---
                # Menggunakan 'warga_id' karena kolom 'id' di-rename oleh pandas merge
                id_hadir = df_merged['warga_id'].unique()

                df_tidak_hadir = df_warga_wilayah[~df_warga_wilayah['id'].isin(id_hadir)]

                if selected_gender != "Semua":
                    gender_code = "L" if selected_gender == "Laki-laki" else "P"
                    df_tidak_hadir = df_tidak_hadir[df_tidak_hadir['jenis_kelamin'] == gender_code]

                if not df_tidak_hadir.empty:
                    df_tidak_hadir['kategori_usia'] = df_tidak_hadir['usia'].apply(get_kategori)
                
                st.subheader(f"Data Warga yang Tidak Hadir pada {selected_date.strftime('%d %B %Y')}")

                ada_data_tidak_hadir = False
                if not df_tidak_hadir.empty:
                    if selected_kategori == "Tampilkan Semua":
                        for nama_kategori, _ in kategori_usia_defs.items():
                            df_kategori_absen = df_tidak_hadir[df_tidak_hadir['kategori_usia'] == nama_kategori]
                            if not df_kategori_absen.empty:
                                ada_data_tidak_hadir = True
                                st.markdown(f"#### Tidak Hadir: {nama_kategori}")
                                df_display_absen = df_kategori_absen.reset_index(drop=True)
                                df_display_absen.index += 1 # Membuat indeks mulai dari 1
                                st.dataframe(df_display_absen[['nama_lengkap', 'rt', 'blok']], use_container_width=True)
                    else:
                        df_kategori_absen = df_tidak_hadir[df_tidak_hadir['kategori_usia'] == selected_kategori]
                        if not df_kategori_absen.empty:
                            ada_data_tidak_hadir = True
                            st.markdown(f"#### Tidak Hadir: {selected_kategori}")
                            df_display_absen = df_kategori_absen.reset_index(drop=True)
                            df_display_absen.index += 1 # Membuat indeks mulai dari 1
                            st.dataframe(df_display_absen[['nama_lengkap', 'rt', 'blok']], use_container_width=True)
                
                if not ada_data_tidak_hadir:
                    st.success("Semua warga yang cocok dengan filter telah hadir, atau tidak ada data warga untuk ditampilkan.")
            
            # st.divider()
            # (Sisa kode untuk tren dan PDF tidak perlu diubah)
            # ...

            # --- [BLOK KODE BARU] UNTUK FITUR DOWNLOAD PDF ---
            # <-- MODIFIKASI 3: Tambahkan tombol "Buat PDF" dan logika persiapan datanya -->
            st.divider()
            st.subheader("Cetak Laporan")
            
            if st.button("Buat & Download Laporan PDF"):
                with st.spinner("Membuat laporan PDF, mohon tunggu..."):
                    
                    # --- Langkah A: Siapkan data hadir & tidak hadir yang final ---
                    id_hadir = df_merged['id'].unique() # Pastikan 'id' adalah kolom yang benar
                    df_hadir_final = df_warga_wilayah[df_warga_wilayah['id'].isin(id_hadir)].copy()
                    df_tidak_hadir_final = df_warga_wilayah[~df_warga_wilayah['id'].isin(id_hadir)].copy()
                    
                    # Gabungkan data pemeriksaan ke data hadir
                    df_hadir_final = pd.merge(df_hadir_final, df_pemeriksaan_harian, left_on='id', right_on='warga_id')
                    
                    # Tambah kolom kategori usia
                    df_hadir_final['kategori_usia'] = df_hadir_final['usia'].apply(get_kategori)
                    df_tidak_hadir_final['kategori_usia'] = df_tidak_hadir_final['usia'].apply(get_kategori)

                    # --- Langkah B: Kelompokkan data ke dalam dictionary ---
                    hadir_per_kategori = {}
                    tidak_hadir_per_kategori = {}
                    kolom_hadir = ['nama_lengkap', 'rt', 'blok', 'tensi_sistolik', 'tensi_diastolik', 'berat_badan_kg']
                    kolom_tidak_hadir = ['nama_lengkap', 'rt', 'blok', 'jenis_kelamin']

                    for kategori in kategori_usia_list[1:]: # Loop semua nama kategori
                        hadir_per_kategori[kategori] = df_hadir_final[df_hadir_final['kategori_usia'] == kategori][kolom_hadir]
                        tidak_hadir_per_kategori[kategori] = df_tidak_hadir_final[df_tidak_hadir_final['kategori_usia'] == kategori][kolom_tidak_hadir]

                    # --- Langkah C: Kumpulkan semua data ke dalam satu objek ---
                    report_data_final = {
                        "filters": {
                            'selected_date_str': selected_date.strftime('%d %B %Y'),
                            'rt': selected_wilayah, 'kategori': selected_kategori, 'gender': selected_gender
                        },
                        "figures": {
                            'komposisi_warga': fig_sunburst_komposisi,
                            'partisipasi_warga': fig_sunburst_partisipasi,
                            'partisipasi_kategori': donut_figs_for_pdf # List berisi gambar donat
                        },
                        "dataframes": {
                            'hadir_per_kategori': hadir_per_kategori, # Kamus berisi tabel hadir
                            'tidak_hadir_per_kategori': tidak_hadir_per_kategori # Kamus berisi tabel tidak hadir
                        }
                    }
                    
                    # --- Langkah D: Panggil fungsi PDF yang baru dengan data yang sudah siap ---
                    pdf_buffer = generate_pdf_report_baru(report_data_final)
                    
                    st.download_button(
                        label="✅ Download PDF Selesai",
                        data=pdf_buffer,
                        file_name=f"Laporan_Posyandu_{selected_date.strftime('%Y-%m-%d')}.pdf",
                        mime="application/pdf"
                    )
    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
        st.exception(e)

# --- JALANKAN HALAMAN ---
page_dashboard()