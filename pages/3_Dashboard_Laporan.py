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

# --- KONEKSI & KEAMANAN ---
st.set_page_config(page_title="Dashboard & Laporan", page_icon="📈", layout="wide")

if not st.session_state.get("authenticated", False):
    st.error("🔒 Anda harus login untuk mengakses halaman ini.")
    st.stop()

supabase = st.session_state.get('supabase_client')
if not supabase:
    st.error("Koneksi Supabase tidak ditemukan. Silakan login kembali.")
    st.stop()

# --- FUNGSI PEMBANTU PDF (VERSI MODIFIKASI) ---
def generate_pdf_report(filters, metrics, df_rinci, df_rinci_tidak, fig_komposisi, fig_partisipasi):
    """
    Membuat laporan PDF dari data yang sudah difilter.
    Fungsi ini dimodifikasi untuk menerima gambar dari Plotly.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    elements = []

    # --- Header ---
    elements.append(Paragraph("Laporan Posyandu Mawar - KBU", styles['h1']))
    elements.append(Spacer(1, 0.2 * inch))
    
    filter_text = f"<b>Filter Laporan:</b><br/>- Tanggal: {filters['selected_date_str']}<br/>- Wilayah: {filters['rt']}<br/>- Kategori Usia: {filters['kategori']}<br/>- Jenis Kelamin: {filters['gender']}"
    elements.append(Paragraph(filter_text, styles['Normal']))
    elements.append(Spacer(1, 0.3 * inch))

    # --- Ringkasan Metrik ---
    elements.append(Paragraph("Ringkasan Laporan", styles['h2']))
    metric_data = [
        ['Total Warga (sesuai filter)', f": {metrics['total_warga']}"],
        ['Jumlah Kunjungan (Hadir)', f": {metrics['hadir_hari_ini']}"],
        ['Tingkat Partisipasi', f": {metrics['partisipasi_hari_ini']:.1f}%"]
    ]
    metric_table = Table(metric_data, colWidths=[2.5*inch, 2.5*inch])
    metric_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    elements.append(metric_table)
    elements.append(Spacer(1, 0.3 * inch))

    # --- Grafik Komposisi Warga ---
    if fig_komposisi:
        elements.append(Paragraph("Diagram Komposisi Warga", styles['h2']))
        img_buffer_komposisi = BytesIO()
        # Menggunakan write_image untuk Plotly (membutuhkan 'kaleido')
        fig_komposisi.write_image(img_buffer_komposisi, format='png', scale=2)
        img_buffer_komposisi.seek(0)
        elements.append(Image(img_buffer_komposisi, width=6*inch, height=4*inch))
        elements.append(Spacer(1, 0.1 * inch))

    # --- Grafik Partisipasi Warga ---
    if fig_partisipasi:
        elements.append(Paragraph("Diagram Partisipasi Warga Hadir", styles['h2']))
        img_buffer_partisipasi = BytesIO()
        fig_partisipasi.write_image(img_buffer_partisipasi, format='png', scale=2)
        img_buffer_partisipasi.seek(0)
        elements.append(Image(img_buffer_partisipasi, width=6*inch, height=4*inch))

    elements.append(PageBreak())
    
    # --- Tabel Data Rinci ---
    elements.append(Paragraph("Data Rinci Kunjungan (Warga Hadir)", styles['h2']))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Pastikan ada data sebelum membuat tabel
    if not df_rinci.empty:
        table_data = [df_rinci.columns.to_list()] + df_rinci.values.tolist()
        data_rinci_table = Table(table_data, repeatRows=1, hAlign='LEFT')
        data_rinci_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.darkslategray), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.beige),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('FONTSIZE', (0,1), (-1,-1), 9)
        ]))
        elements.append(data_rinci_table)
    else:
        elements.append(Paragraph("Tidak ada data kunjungan rinci untuk ditampilkan.", styles['Normal']))

    # Pastikan ada data sebelum membuat tabel
    if not df_rinci_tidak.empty:
        table_data_tidak = [df_rinci_tidak.columns.to_list()] + df_rinci_tidak.values.tolist()
        data_rinci_table_tidak = Table(table_data_tidak, repeatRows=1, hAlign='LEFT')
        data_rinci_table_tidak.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.darkslategray), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.beige),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('FONTSIZE', (0,1), (-1,-1), 9)
        ]))
        elements.append(data_rinci_table_tidak)
    else:
        elements.append(Paragraph("Tidak ada data kunjungan rinci untuk ditampilkan.", styles['Normal']))

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
                    path=['total_label', 'kategori_usia', 'jenis_kelamin'],
                    values='count',
                    title='Diagram Komposisi Warga (Total > Kategori Usia > Jenis Kelamin)',
                    # Mewarnai berdasarkan kategori usia untuk membedakan segmen utama
                    color='kategori_usia',
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
                    
                    col_idx = (col_idx + 1) % 4
            
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
            st.divider()
            st.subheader("📥 Unduh Laporan")
            
            # 1. Siapkan semua data yang diperlukan untuk PDF
            
            # a. Filter
            filters_for_pdf = {
                'selected_date_str': selected_date.strftime('%d %B %Y'),
                'rt': "Lingkungan (Semua RT)" if selected_wilayah == "Lingkungan (Semua RT)" else f"RT {selected_wilayah}",
                'kategori': selected_kategori,
                'gender': selected_gender
            }

            # b. Metrik
            hadir_hari_ini = len(id_hadir_keseluruhan)
            partisipasi_hari_ini = (hadir_hari_ini / total_warga_wilayah * 100) if total_warga_wilayah > 0 else 0
            metrics_for_pdf = {
                'total_warga': total_warga_wilayah,
                'hadir_hari_ini': hadir_hari_ini,
                'partisipasi_hari_ini': partisipasi_hari_ini
            }

            # c. Data Rinci (format ulang untuk laporan)
            df_laporan_rinci = pd.DataFrame()
            if not df_merged.empty:
                df_laporan_rinci = df_merged[[
                    'nama_lengkap', 'rt', 'usia', 'tensi_sistolik', 'tensi_diastolik', 
                    'berat_badan_kg', 'gula_darah', 'kolesterol'
                ]].copy()
                df_laporan_rinci.rename(columns={
                    'nama_lengkap': 'Nama Lengkap', 'rt': 'RT', 'usia': 'Usia (thn)',
                    'tensi_sistolik': 'Sistolik', 'tensi_diastolik': 'Diastolik',
                    'berat_badan_kg': 'Berat (kg)', 'gula_darah': 'Gula Darah',
                    'kolesterol': 'Kolesterol'
                }, inplace=True)
                df_laporan_rinci['Usia (thn)'] = df_laporan_rinci['Usia (thn)'].round(1)

            # d. Data Rinci tidak hadir (format ulang untuk laporan)
            df_laporan_rinci_tidak_hadir = pd.DataFrame()
            if not df_tidak_hadir.empty:
                df_laporan_rinci_tidak_hadir = df_tidak_hadir[[
                    'nama_lengkap', 'rt', 'usia', 'tensi_sistolik', 'tensi_diastolik', 
                    'berat_badan_kg', 'gula_darah', 'kolesterol'
                ]].copy()
                df_laporan_rinci_tidak_hadir.rename(columns={
                    'nama_lengkap': 'Nama Lengkap', 'rt': 'RT', 'usia': 'Usia (thn)',
                    'tensi_sistolik': 'Sistolik', 'tensi_diastolik': 'Diastolik',
                    'berat_badan_kg': 'Berat (kg)', 'gula_darah': 'Gula Darah',
                    'kolesterol': 'Kolesterol'
                }, inplace=True)
                df_laporan_rinci_tidak_hadir['Usia (thn)'] = df_laporan_rinci_tidak_hadir['Usia (thn)'].round(1)

            # 2. Hasilkan file PDF di memori
            pdf_buffer = generate_pdf_report(
                filters=filters_for_pdf,
                metrics=metrics_for_pdf,
                df_rinci=df_laporan_rinci,
                df_rinci_tidak=df_laporan_rinci_tidak_hadir
                fig_komposisi=fig_sunburst_komposisi,
                fig_partisipasi=fig_sunburst_partisipasi
            )

            # 3. Buat tombol download
            st.download_button(
                label="Unduh Laporan dalam Format .PDF",
                data=pdf_buffer,
                file_name=f"Laporan_Posyandu_{selected_date.strftime('%Y-%m-%d')}.pdf",
                mime="application/pdf"
            )
            # --- [AKHIR BLOK KODE BARU] ---


    except Exception as e:
        st.error(f"Gagal membuat laporan: {e}")
        st.exception(e)

# --- JALANKAN HALAMAN ---
page_dashboard()