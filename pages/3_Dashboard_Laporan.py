# pages/3_Dashboard_Laporan.py

import streamlit as st
import pandas as pd
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

# --- FUNGSI PEMBANTU PDF ---
def generate_pdf_report(filters, metrics, df_rinci, fig_tren, fig_pie):
    """Membuat laporan PDF dari data yang sudah difilter."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    elements = []

    elements.append(Paragraph("Laporan Posyandu Mawar - KBU", styles['h1']))
    elements.append(Spacer(1, 0.2 * inch))
    
    filter_text = f"<b>Laporan:</b><br/>- Tanggal: {filters['selected_date_str']}<br/>- Wilayah: {filters['rt']}<br/>- Kategori Usia: {filters['kategori']}<br/>- Jenis Kelamin: {filters['gender']}"
    elements.append(Paragraph(filter_text, styles['Normal']))
    elements.append(Spacer(1, 0.3 * inch))

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

    if fig_pie:
        img_buffer_pie = BytesIO()
        fig_pie.savefig(img_buffer_pie, format='png', dpi=300, bbox_inches='tight')
        img_buffer_pie.seek(0)
        elements.append(Image(img_buffer_pie, width=4*inch, height=4*inch))
    
    elements.append(PageBreak())
    elements.append(Paragraph("Tren Kunjungan Warga", styles['h2']))
    if fig_tren:
        img_buffer_tren = BytesIO()
        fig_tren.savefig(img_buffer_tren, format='png', dpi=300, bbox_inches='tight')
        img_buffer_tren.seek(0)
        elements.append(Image(img_buffer_tren, width=6*inch, height=3*inch))
    
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

# --- FUNGSI HALAMAN UTAMA ---
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
            # ... (Kode demografi wilayah tidak diubah)
            
            st.divider()

            # --- Persiapan Data & Pie Chart ---
            df_pemeriksaan_harian = df_pemeriksaan[df_pemeriksaan['tanggal_pemeriksaan'] == selected_date]
            df_merged = pd.merge(df_pemeriksaan_harian, df_warga_wilayah, left_on='warga_id', right_on='id', how='inner')
            
            if selected_gender != "Semua":
                gender_code = "L" if selected_gender == "Laki-laki" else "P"
                df_merged = df_merged[df_merged['jenis_kelamin'] == gender_code]

            st.subheader("Ringkasan Kehadiran per Kategori Usia")

            if not df_merged.empty:
                kategori_usia_defs = {
                    "Bayi (0-6 bln)": (0, 0.5), "Baduta (>6 bln - 2 thn)": (0.5, 2), "Balita (>2 - 5 thn)": (2, 5),
                    "Anak Pra-Sekolah (>5 - <6 thn)": (5, 6), "Anak Usia Sekolah dan Remaja (6 - 18 thn)": (6, 18),
                    "Dewasa (>18 - <60 thn)": (18, 60), "Lansia (≥60 thn)": (60, 200)
                }
                
                def get_kategori(usia):
                    if usia <= 0.5: return "Bayi (0-6 bln)"
                    if usia <= 2: return "Baduta (>6 bln - 2 thn)"
                    if usia <= 5: return "Balita (>2 - 5 thn)"
                    if usia < 6: return "Anak Pra-Sekolah (>5 - <6 thn)"
                    if usia <= 18: return "Anak Usia Sekolah dan Remaja (6 - 18 thn)"
                    if usia < 60: return "Dewasa (>18 - <60 thn)"
                    return "Lansia (≥60 thn)"

                df_merged['kategori_usia'] = df_merged['usia'].apply(get_kategori)
                kehadiran_counts = df_merged['kategori_usia'].value_counts()

                fig_pie, ax_pie = plt.subplots(figsize=(6, 4))
                ax_pie.pie(kehadiran_counts, labels=kehadiran_counts.index, autopct='%1.1f%%', startangle=90)
                ax_pie.axis('equal')
                st.pyplot(fig_pie)
            else:
                st.info("Tidak ada data kehadiran untuk ditampilkan dalam ringkasan.")
            
            st.divider()

            st.subheader(f"Data Rinci Warga yang Hadir pada {selected_date.strftime('%d %B %Y')}")
            
            ada_data_kunjungan = False
            if selected_kategori == "Tampilkan Semua":
                for nama_kategori, _ in kategori_usia_defs.items():
                    df_kategori = df_merged[df_merged['kategori_usia'] == nama_kategori]
                    if not df_kategori.empty:
                        ada_data_kunjungan = True
                        st.markdown(f"#### {nama_kategori}")
                        st.dataframe(df_kategori[['nama_lengkap', 'rt', 'blok', 'tensi_sistolik', 'tensi_diastolik', 'berat_badan_kg', 'gula_darah', 'kolesterol']], use_container_width=True)
            else:
                df_kategori = df_merged[df_merged['kategori_usia'] == selected_kategori]
                if not df_kategori.empty:
                    ada_data_kunjungan = True
                    st.markdown(f"#### Menampilkan Kategori: {selected_kategori}")
                    st.dataframe(df_kategori[['nama_lengkap', 'rt', 'blok', 'tensi_sistolik', 'tensi_diastolik', 'berat_badan_kg', 'gula_darah', 'kolesterol']], use_container_width=True)

            if not ada_data_kunjungan:
                st.info("Tidak ada data kunjungan (hadir) yang cocok dengan filter.")

            st.divider()
            
            with st.expander("Lihat Data Warga yang Tidak Hadir Pemeriksaan"):
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
                                st.dataframe(df_kategori_absen[['nama_lengkap', 'rt', 'blok']], use_container_width=True)
                    else:
                        df_kategori_absen = df_tidak_hadir[df_tidak_hadir['kategori_usia'] == selected_kategori]
                        if not df_kategori_absen.empty:
                            ada_data_tidak_hadir = True
                            st.markdown(f"#### Tidak Hadir: {selected_kategori}")
                            st.dataframe(df_kategori_absen[['nama_lengkap', 'rt', 'blok']], use_container_width=True)
                
                if not ada_data_tidak_hadir:
                    st.success("Semua warga yang cocok dengan filter telah hadir, atau tidak ada data warga untuk ditampilkan.")
            
            st.divider()
            # (Sisa kode untuk tren dan PDF tidak perlu diubah)
            # ...

    except Exception as e:
        st.error(f"Gagal membuat laporan: {e}")
        st.exception(e)

# --- JALANKAN HALAMAN ---
page_dashboard()