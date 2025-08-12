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
from dateutil.relativedelta import relativedelta #12082025 untuk akomodasi format ..Tahun...Bulan

# --- KONEKSI & KEAMANAN ---
st.set_page_config(page_title="Dashboard & Laporan", page_icon="📈", layout="wide")

if not st.session_state.get("authenticated", False):
    st.error("🔒 Anda harus login untuk mengakses halaman ini.")
    st.stop()

supabase = st.session_state.get('supabase_client')
if not supabase:
    st.error("Koneksi Supabase tidak ditemukan. Silakan login kembali.")
    st.stop()

def format_usia_string(tgl_lahir, tgl_referensi): #12082025 tambahan fungsi untuk ..Tahun..Bulan
    """
    Mengubah tanggal lahir menjadi format string 'X Tahun Y Bulan'.
    Bekerja dengan objek datetime dari Pandas.
    """
    if pd.isna(tgl_lahir):
        return "N/A"
    delta = relativedelta(tgl_referensi, tgl_lahir)
    return f"{delta.years} Tahun {delta.months} Bulan"

def tampilkan_data_per_kategori(dataframe, kategori_filter, semua_kategori_defs, kolom_tampil, judul_prefix=""):
    """
    Fungsi bantuan untuk menampilkan DataFrame dalam Streamlit, 
    dikelompokkan berdasarkan kategori usia yang dipilih.

    Args:
        dataframe (pd.DataFrame): DataFrame sumber (bisa data hadir atau tidak hadir).
        kategori_filter (str): Kategori yang dipilih dari filter Streamlit.
        semua_kategori_defs (dict): Definisi semua kategori usia.
        kolom_tampil (list): Daftar nama kolom yang ingin ditampilkan.
        judul_prefix (str): Teks awalan untuk judul setiap kategori (misal: "Hadir: ").

    Returns:
        bool: True jika ada data yang ditampilkan, False jika tidak.
    """
    ada_data_yang_ditampilkan = False

    # Jika pengguna memilih untuk menampilkan semua kategori
    if kategori_filter == "Tampilkan Semua":
        for nama_kategori, _ in semua_kategori_defs.items():
            df_kategori = dataframe[dataframe['kategori_usia'] == nama_kategori]
            if not df_kategori.empty:
                ada_data_yang_ditampilkan = True
                st.markdown(f"#### {judul_prefix}{nama_kategori}")
                df_display = df_kategori.reset_index(drop=True)
                df_display.index += 1  # Indeks mulai dari 1
                st.dataframe(df_display[kolom_tampil], use_container_width=True)
    
    # Jika pengguna memilih satu kategori spesifik
    else:
        df_kategori = dataframe[dataframe['kategori_usia'] == kategori_filter]
        if not df_kategori.empty:
            ada_data_yang_ditampilkan = True
            st.markdown(f"#### {judul_prefix}{kategori_filter}")
            df_display = df_kategori.reset_index(drop=True)
            df_display.index += 1  # Indeks mulai dari 1
            st.dataframe(df_display[kolom_tampil], use_container_width=True)
            
    return ada_data_yang_ditampilkan

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

# --- FUNGSI PEMBANTU PDF (VERSI FINAL DENGAN TOTAL ROW & URUTAN BARU) ---
def generate_pdf_report(filters, metrics, df_rinci, fig_komposisi, fig_partisipasi, df_tidak_hadir, semua_kategori_defs, data_komposisi, column_maps):
    """
    Membuat laporan PDF dari data yang sudah difilter.
    Fungsi ini menyertakan total row pada tabel komposisi dan urutan elemen yang disesuaikan.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='H3_Bold', parent=styles['h3'], fontName='Helvetica-Bold'))
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
    elements.append(Spacer(1, 0.2 * inch))

    # --- [PERUBAHAN 2] Urutan diubah: Diagram dulu, baru tabel ---
    # Pindah ke halaman baru jika ada grafik
    if fig_komposisi or fig_partisipasi:
         elements.append(PageBreak())

    # Tampilkan Diagram Komposisi Warga
    if fig_komposisi:
        elements.append(Paragraph("Diagram Komposisi Warga", styles['h2']))
        img_buffer_komposisi = BytesIO()
        fig_komposisi.write_image(img_buffer_komposisi, format='png', scale=2)
        img_buffer_komposisi.seek(0)
        elements.append(Image(img_buffer_komposisi, width=6*inch, height=4.3*inch))
        elements.append(Spacer(1, 0.1 * inch))

    # Tampilkan Tabel Rincian Komposisi Warga (setelah diagramnya)
    elements.append(Paragraph("Rincian Komposisi Warga", styles['h2']))
    elements.append(Spacer(1, 0.2 * inch))
    
    # --- [PERUBAHAN 1] Hitung total untuk baris terakhir ---
    total_keseluruhan = sum(row[1] for row in data_komposisi)
    total_laki = sum(row[2] for row in data_komposisi)
    total_perempuan = sum(row[3] for row in data_komposisi)
    total_row = ['Total Keseluruhan', total_keseluruhan, total_laki, total_perempuan]
    
    # Siapkan header dan gabungkan dengan data
    table_data_komposisi = [['Kategori Usia', 'Total', 'Laki-laki', 'Perempuan']]
    table_data_komposisi.extend(data_komposisi)
    table_data_komposisi.append(total_row) # Tambahkan baris total ke data tabel

    komposisi_table = Table(table_data_komposisi, colWidths=[2.5*inch, 0.8*inch, 1*inch, 1*inch], hAlign='LEFT')
    komposisi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightblue), ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-2), colors.beige), # Latar belakang untuk baris data
        ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey), # Latar belakang untuk baris total
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTSIZE', (0,1), (-1,-1), 9),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold') # Membuat baris terakhir (total) menjadi tebal
    ]))
    elements.append(komposisi_table)
    elements.append(Spacer(1, 0.2 * inch))
    
    # Tampilkan Diagram Partisipasi Warga
    if fig_partisipasi:
        elements.append(Paragraph("Diagram Partisipasi Warga Hadir", styles['h2']))
        img_buffer_partisipasi = BytesIO()
        fig_partisipasi.write_image(img_buffer_partisipasi, format='png', scale=2)
        img_buffer_partisipasi.seek(0)
        elements.append(Image(img_buffer_partisipasi, width=6*inch, height=4.3*inch))

    elements.append(PageBreak())
    
    # --- Tabel Data Rinci Kunjungan (Warga Hadir) per Kategori ---
    elements.append(Paragraph("Data Rinci Kunjungan (Warga Hadir)", styles['h2']))
    elements.append(Spacer(1, 0.2 * inch))
    
    kategori_filter = filters.get('kategori', 'Tampilkan Semua')
    ada_data_hadir = False

    kategori_iterator = semua_kategori_defs.keys() if kategori_filter == "Tampilkan Semua" else [kategori_filter]

    for nama_kategori in kategori_iterator:
        df_kategori = df_rinci[df_rinci['kategori_usia'] == nama_kategori]
        if not df_kategori.empty:
            ada_data_hadir = True
            elements.append(Paragraph(f"Kategori: {nama_kategori}", styles['H3_Bold']))
            elements.append(Spacer(1, 0.1 * inch))

            # --- [PERUBAHAN UTAMA] LOGIKA PEMILIHAN KOLOM DINAMIS ADA DI SINI ---
            if nama_kategori in ["Dewasa (>18 - <60 thn)", "Lansia (≥60 thn)"]:
                kolom_hadir_pdf = [
                    'nama_lengkap', 'usia_teks', 'rt', 'blok', 'tensi_sistolik', 
                    'tensi_diastolik', 'berat_badan_kg', 'gula_darah', 'kolesterol'
                ]
            else: # Untuk kategori lainnya
                kolom_hadir_pdf = [
                    'nama_lengkap', 'usia_teks', 'rt', 'blok', 'berat_badan_kg', 
                    'tinggi_badan_cm', 'lingkar_lengan_cm', 'lingkar_kepala_cm'
                ]
            kolom_valid = [kol for kol in kolom_hadir_pdf if kol in df_kategori.columns]
            # df_display = df_kategori.copy()
            # df_display = df_display.drop(columns=['kategori_usia'])
            df_display = df_kategori[kolom_valid].copy().rename(columns=column_maps)
            df_display.insert(0, "No", range(1, len(df_display) + 1))
            
            table_data = [df_display.columns.to_list()] + df_display.values.tolist()
            data_rinci_table = Table(table_data, repeatRows=1, hAlign='LEFT')
            data_rinci_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.darkslategray), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,0), 10),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('BACKGROUND', (0,1), (-1,-1), colors.beige),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('FONTSIZE', (0,1), (-1,-1), 9)
            ]))
            elements.append(data_rinci_table)
            elements.append(Spacer(1, 0.2 * inch))

    if not ada_data_hadir:
        elements.append(Paragraph("Tidak ada data kunjungan rinci untuk ditampilkan.", styles['Normal']))

    # --- Tabel Data Warga Tidak Hadir per Kategori ---
    elements.append(PageBreak())
    elements.append(Paragraph("Data Warga Tidak Hadir", styles['h2']))
    elements.append(Spacer(1, 0.2 * inch))
    
    ada_data_tidak_hadir = False
    if df_tidak_hadir is not None and not df_tidak_hadir.empty:
        for nama_kategori in kategori_iterator:
            df_kategori_tidak_hadir = df_tidak_hadir[df_tidak_hadir['kategori_usia'] == nama_kategori]
            if not df_kategori_tidak_hadir.empty:
                ada_data_tidak_hadir = True
                elements.append(Paragraph(f"Kategori: {nama_kategori}", styles['H3_Bold']))
                elements.append(Spacer(1, 0.1 * inch))
                
                df_display_tidak_hadir = df_kategori_tidak_hadir.copy()
                df_display_tidak_hadir = df_display_tidak_hadir.drop(columns=['kategori_usia'])
                df_display_tidak_hadir.insert(0, "No", range(1, len(df_display_tidak_hadir) + 1))
                
                table_data_tidak_hadir = [df_display_tidak_hadir.columns.to_list()] + df_display_tidak_hadir.values.tolist()
                data_tidak_hadir_table = Table(table_data_tidak_hadir, repeatRows=1, hAlign='LEFT')
                data_tidak_hadir_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.darkred), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,0), 10),
                    ('BOTTOMPADDING', (0,0), (-1,0), 12),
                    ('BACKGROUND', (0,1), (-1,-1), colors.beige),
                    ('GRID', (0,0), (-1,-1), 1, colors.black),
                    ('FONTSIZE', (0,1), (-1,-1), 9)
                ]))
                elements.append(data_tidak_hadir_table)
                elements.append(Spacer(1, 0.2 * inch))

    if not ada_data_tidak_hadir:
        elements.append(Paragraph("Semua warga yang relevan hadir atau tidak ada data tidak hadir untuk ditampilkan.", styles['Normal']))

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

    # [BARU] Dictionary untuk memetakan nama kolom teknis ke nama yang ramah pengguna
    COLUMN_MAPS = {
        'nama_lengkap': 'Nama Lengkap',
        'usia_teks': 'Usia',
        'rt': 'RT',
        'blok': 'Blok',
        'berat_badan_kg': 'Berat Badan\n(kg)',
        'tinggi_badan_cm': 'Tinggi Badan\n(cm)',
        'lingkar_lengan_cm': 'Lingkar Lengan\n(cm)',
        'lingkar_kepala_cm': 'Lingkar Kepala\n(cm)',
        'tensi_sistolik': 'Tensi\nSistolik',
        'tensi_diastolik': 'Tensi\nDiastolik',
        'gula_darah': 'Gula\nDarah',
        'kolesterol': 'Kolesterol'
    }

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
            # 1. TETAP hitung 'usia' numerik untuk logika filter & kategori
            df_warga['usia'] = (pd.to_datetime(selected_date) - df_warga['tanggal_lahir']).dt.days / 365.25

            # 2. [BARU] Buat kolom 'usia_teks' dengan format "Tahun Bulan" yang akurat
            df_warga['usia_teks'] = df_warga['tanggal_lahir'].apply(
                lambda tgl: format_usia_string(tgl, selected_date)
            )

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

            #------------------- [ BLOK UNTUK BARIS TAMPILAN DEMOGRAFI DAN GRAFIKNYA ] -------------------
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
            #------------------- [ AKHIR BARIS TAMPILAN DEMOGRAFI DAN GRAFIKNYA ] -------------------


            st.divider()

            # --- [ BLOK KODE SUNBURST PARTISIPASI ] ---
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
            # --- [ AKHIR BLOK KODE SUNBURST PARTISIPASI ] ---

            st.divider()


            # --- [ AWAL BLOK UNTUK DIAGRAM DONUT TINGKAT PARTISIPASI ] ---
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
            # --- [ AKHIR BLOK UNTUK DIAGRAM DONUT TINGKAT PARTISIPASI ] ---

            # Tambahkan kolom kategori usia ke dataframe gabungan untuk filtering di bawah
            if not df_merged.empty:
                df_merged['kategori_usia'] = df_merged['usia'].apply(get_kategori)
                # BUAT JUGA KOLOM USIA DALAM BENTUK TEKS AGAR LEBIH INFORMATIF DI TABEL
                #df_merged['usia_teks'] = df_merged['usia'].apply(lambda u: f"{int(u)} thn" if u >= 1 else f"{int(u * 12)} bln")

            # --- [ AKHIR PERUBAHAN UTAMA ] ---
            
            st.divider()

            # --- BLOK DATA WARGA HADIR (Sudah Rapi) ---
            with st.expander("Lihat Data Rinci Warga yang Hadir Posyandu"):
                st.subheader(f"Data Rinci Warga yang Hadir pada {selected_date.strftime('%d %B %Y')}")
                
                # Tentukan kategori mana yang akan di-loop berdasarkan filter
                if selected_kategori == "Tampilkan Semua":
                    kategori_iterator = kategori_usia_defs.keys()
                else:
                    kategori_iterator = [selected_kategori]
                    
                ada_data_kunjungan_total = False

                # Loop melalui setiap kategori yang relevan
                for nama_kategori in kategori_iterator:
                    df_kategori = df_merged[df_merged['kategori_usia'] == nama_kategori]
                    
                    if not df_kategori.empty:
                        ada_data_kunjungan_total = True
                        
                        # --- INTI PERBAIKAN: Tentukan kolom yang benar UNTUK KATEGORI INI ---
                        if nama_kategori in ["Dewasa (>18 - <60 thn)", "Lansia (≥60 thn)"]:
                            kolom_tampil = [
                                'nama_lengkap', 'usia_teks', 'rt', 'blok', 'tensi_sistolik', 
                                'tensi_diastolik', 'berat_badan_kg', 'gula_darah', 'kolesterol'
                            ]
                        else: # Untuk kategori lainnya (Bayi, Balita, dll.)
                            kolom_tampil = [
                                'nama_lengkap', 'usia_teks', 'rt', 'blok', 'berat_badan_kg', 
                                'tinggi_badan_cm', 'lingkar_lengan_cm', 'lingkar_kepala_cm'
                            ]
                        
                        # Pastikan hanya kolom yang ada di DataFrame yang dipanggil
                        kolom_valid = [kol for kol in kolom_tampil if kol in df_kategori.columns]

                        # Tampilkan judul dan tabel
                        st.markdown(f"#### {nama_kategori}")
                        df_display = df_kategori.reset_index(drop=True)
                        df_display.index += 1

                        # [UBAH] Ganti nama kolom sebelum ditampilkan
                        df_renamed = df_display[kolom_valid].rename(columns=COLUMN_MAPS)
                        st.dataframe(df_renamed, use_container_width=True)

                # Tampilkan pesan jika tidak ada data sama sekali setelah loop selesai
                if not ada_data_kunjungan_total:
                    st.info("Tidak ada data kunjungan (hadir) yang cocok dengan filter.")

            # --- BLOK DATA WARGA TIDAK HADIR (Sudah Rapi) ---
            with st.expander("Lihat Data Warga yang Tidak Hadir Posyandu"):
                # Persiapan data warga tidak hadir
                id_hadir = df_merged['warga_id'].unique()
                df_tidak_hadir = df_warga_wilayah[~df_warga_wilayah['id'].isin(id_hadir)]

                if selected_gender != "Semua":
                    gender_code = "L" if selected_gender == "Laki-laki" else "P"
                    df_tidak_hadir = df_tidak_hadir[df_tidak_hadir['jenis_kelamin'] == gender_code]

                if not df_tidak_hadir.empty:
                    df_tidak_hadir['kategori_usia'] = df_tidak_hadir['usia'].apply(get_kategori)
                
                st.subheader(f"Data Warga yang Tidak Hadir pada {selected_date.strftime('%d %B %Y')}")

                if selected_kategori == "Tampilkan Semua":
                    kategori_iterator_th = kategori_usia_defs.keys()
                else:
                    kategori_iterator_th = [selected_kategori]
                
                ada_data_tidak_hadir_total = False
                kolom_tidak_hadir = ['nama_lengkap', 'usia_teks', 'rt', 'blok'] # Kolom yang relevan

                for nama_kategori in kategori_iterator_th:
                    df_kategori_th = df_tidak_hadir[df_tidak_hadir['kategori_usia'] == nama_kategori]

                    if not df_kategori_th.empty:
                        ada_data_tidak_hadir_total = True
                        st.markdown(f"#### Tidak Hadir: {nama_kategori}")
                        
                        df_display_th = df_kategori_th.reset_index(drop=True)
                        df_display_th.index += 1
                        
                        # [UBAH] Ganti nama kolom sebelum ditampilkan
                        df_renamed_th = df_display_th[kolom_tidak_hadir].rename(columns=COLUMN_MAPS)
                        st.dataframe(df_renamed_th, use_container_width=True)
                
                if not ada_data_tidak_hadir_total:
                    st.success("Semua warga yang cocok dengan filter telah hadir, atau tidak ada data warga untuk ditampilkan.")            

            # --- [TAMBAHKAN BLOK INI] Tombol untuk Mengunduh Laporan PDF ---
            st.divider()
            st.subheader("📥⬇️ Unduh Laporan")

            # Persiapan data final untuk PDF
            # Pastikan kolom yang relevan dipilih


            # for kategori in kategori_usia_defs:
            #     # Memeriksa apakah kunci saat ini sama dengan string target
            #     if kategori == "Dewasa (>18 - <60 thn)":
            #         # Jika sama, eksekusi perintah di sini
            #         kolom_hadir_pdf = [
            #             'kategori_usia', 'nama_lengkap', 'usia_teks', 'rt', 'blok', 'tensi_sistolik', 
            #             'tensi_diastolik', 'berat_badan_kg', 'gula_darah', 'kolesterol'
            #         ]
            #     else:
            #         kolom_hadir_pdf = [
            #             'kategori_usia', 'nama_lengkap', 'usia_teks', 'rt', 'blok',  
            #             'berat_badan_kg', 'lingkar_kepala_cm'
            #         ]                    

            # kolom_hadir_pdf = [
            #     'kategori_usia', 'nama_lengkap', 'usia_teks', 'rt', 'blok', 'tensi_sistolik', 
            #     'tensi_diastolik', 'berat_badan_kg', 'gula_darah', 'kolesterol'
            # ]
            kolom_tidak_hadir_pdf = ['kategori_usia', 'nama_lengkap', 'usia_teks', 'rt', 'blok']

            # Filter data sesuai pilihan di UI
            df_data_rinci_pdf = df_merged.copy()
            if selected_kategori != "Tampilkan Semua":
                df_data_rinci_pdf = df_data_rinci_pdf[df_data_rinci_pdf['kategori_usia'] == selected_kategori]
            
            df_tidak_hadir_pdf = df_tidak_hadir.copy()
            if selected_kategori != "Tampilkan Semua":
                df_tidak_hadir_pdf = df_tidak_hadir_pdf[df_tidak_hadir_pdf['kategori_usia'] == selected_kategori]

            # Kumpulkan filter dan metrik untuk PDF
            pdf_filters = {
                "selected_date_str": selected_date.strftime('%d %B %Y'),
                "rt": selected_wilayah,
                "kategori": selected_kategori,
                "gender": selected_gender
            }
            # Hitung metrik berdasarkan data yang sudah difilter di UI
            total_warga_terfilter = len(df_warga_wilayah_gender)
            if selected_kategori != "Tampilkan Semua":
                 total_warga_terfilter = len(df_warga_wilayah_gender[df_warga_wilayah_gender['kategori_usia'] == selected_kategori])

            hadir_hari_ini = len(df_data_rinci_pdf)
            partisipasi = (hadir_hari_ini / total_warga_terfilter * 100) if total_warga_terfilter > 0 else 0

            pdf_metrics = {
                "total_warga": total_warga_terfilter,
                "hadir_hari_ini": hadir_hari_ini,
                "partisipasi_hari_ini": partisipasi
            }

            # Tombol download
            if st.button("Buat dan Unduh Laporan PDF", type="primary"):
                with st.spinner("Membuat laporan PDF... Mohon tunggu sebentar."):

                    # [UBAH] Ganti nama kolom untuk DataFrame yang akan dikirim ke PDF
                    #df_rinci_pdf_renamed = df_data_rinci_pdf[kolom_hadir_pdf].rename(columns=COLUMN_MAPS)
                    df_tidak_hadir_pdf_renamed = df_tidak_hadir_pdf[kolom_tidak_hadir_pdf].rename(columns=COLUMN_MAPS)

                    pdf_buffer = generate_pdf_report(
                        filters=pdf_filters,
                        metrics=pdf_metrics,
                        df_rinci=df_data_rinci_pdf, # Gunakan DataFrame yang sudah di-rename
                        fig_komposisi=fig_sunburst_komposisi if not df_komposisi.empty else None,
                        fig_partisipasi=fig_sunburst_partisipasi if not df_partisipasi.empty else None,
                        df_tidak_hadir=df_tidak_hadir_pdf_renamed, # Gunakan DataFrame yang sudah di-rename
                        semua_kategori_defs=kategori_usia_defs,
                        data_komposisi=baris_demografi,
                        column_maps=COLUMN_MAPS
                    )
                    st.download_button(
                        label="✅ Laporan Siap! Klik untuk mengunduh",
                        data=pdf_buffer,
                        file_name=f"Laporan_Posyandu_{selected_date.strftime('%Y-%m-%d')}_{selected_wilayah}.pdf",
                        mime="application/pdf"
                    )


    except Exception as e:
        st.error(f"Gagal membuat laporan: {e}")
        st.exception(e)
# ---AKHIR FUNGSI HALAMAN UTAMA ---

# --- JALANKAN HALAMAN ---
page_dashboard()