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

# --- KONEKSI & KEAMANAN ---
st.set_page_config(page_title="Dashboard & Laporan", page_icon="📈", layout="wide")

# Blokir akses jika pengguna belum login
if not st.session_state.get("authenticated", False):
    st.error("🔒 Anda harus login untuk mengakses halaman ini.")
    st.stop()

@st.cache_resource
def init_connection():
    """Membuat dan mengembalikan koneksi ke database Supabase."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Gagal terhubung ke Supabase: {e}")
        return None

supabase = init_connection()

# --- FUNGSI PEMBANTU PDF ---
def generate_pdf_report(filters, metrics, df_rinci, fig_tren, fig_pie):
    """Membuat laporan PDF dari data yang sudah difilter."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))

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
        
        # Hitung Usia warga berdasarkan hari ini
        df_warga['tanggal_lahir'] = pd.to_datetime(df_warga['tanggal_lahir'])
        df_warga['usia'] = (datetime.now() - df_warga['tanggal_lahir']).dt.days / 365.25

        # --- Filter di Halaman Utama ---
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
            wilayah_options = ["Lingkungan (Semua RT)"] + sorted(df_warga['rt'].dropna().unique().tolist())
            selected_wilayah = st.selectbox("Tampilkan data untuk wilayah", wilayah_options)

            df_warga_wilayah = df_warga.copy()
            if selected_wilayah != "Lingkungan (Semua RT)":
                df_warga_wilayah = df_warga[df_warga['rt'] == selected_wilayah]
            
            # --- Perhitungan Demografi ---
            # (Seluruh blok perhitungan demografi dari kode asli Anda)
            total_warga_wilayah = len(df_warga_wilayah)
            # ... dan seterusnya ...

            st.divider()
            st.subheader(f"Laporan untuk {selected_date.strftime('%d %B %Y')}")
            
            # --- Filter Lanjutan ---
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                kategori_usia_list = ["Semua", "Bayi (0-6 bln)", "Baduta (6 bln - <2 thn)", "Balita (2 - <5 thn)", "Anak-anak (5 - <10 thn)", "Remaja (10 - <20 thn)", "Dewasa (20 - <60 thn)", "Lansia (60+ thn)"]
                selected_kategori = st.selectbox("Kategori Usia", kategori_usia_list)
            with col_f2:
                selected_gender = st.selectbox("Jenis Kelamin", ["Semua", "Laki-laki", "Perempuan"])

            # Terapkan filter ke dataframe warga
            df_warga_final_filter = df_warga_wilayah.copy()
            if selected_gender != "Semua":
                gender_code = "L" if selected_gender == "Laki-laki" else "P"
                df_warga_final_filter = df_warga_final_filter[df_warga_final_filter['jenis_kelamin'] == gender_code]
            if selected_kategori != "Semua":
                if selected_kategori == "Bayi (0-6 bln)": df_warga_final_filter = df_warga_final_filter[df_warga_final_filter['usia'] <= 0.5]
                elif selected_kategori == "Baduta (6 bln - <2 thn)": df_warga_final_filter = df_warga_final_filter[(df_warga_final_filter['usia'] > 0.5) & (df_warga_final_filter['usia'] < 2)]
                # ... (lanjutkan untuk semua kategori usia) ...
                elif selected_kategori == "Lansia (60+ thn)": df_warga_final_filter = df_warga_final_filter[df_warga_final_filter['usia'] >= 60]

            # --- Perhitungan Metrik ---
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

            # Inisialisasi fig_pie dan fig_tren
            fig_pie, fig_tren = None, None

            # --- Visualisasi ---
            if hadir_hari_itu > 0:
                col_pie, _ = st.columns([1, 1])
                with col_pie:
                    tidak_hadir_hari_itu = total_warga_terfilter - hadir_hari_itu
                    labels = 'Hadir', 'Tidak Hadir'
                    sizes = [hadir_hari_itu, tidak_hadir_hari_itu]
                    fig_pie, ax_pie = plt.subplots(figsize=(4, 4))
                    ax_pie.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=['#4CAF50', '#FFC107'])
                    ax_pie.axis('equal'); st.pyplot(fig_pie)

                st.write("#### Data Rinci Kunjungan")
                df_laporan_harian = pd.merge(df_pemeriksaan_harian, df_warga, left_on='warga_id', right_on='id', how='left')
                st.dataframe(df_laporan_harian[['nama_lengkap', 'rt', 'blok', 'tensi_sistolik', 'tensi_diastolik', 'berat_badan_kg', 'gula_darah', 'kolesterol']])
            else:
                st.info("Tidak ada data kehadiran yang cocok dengan filter yang dipilih.")
                df_laporan_harian = pd.DataFrame() # Buat dataframe kosong jika tidak ada data

            st.divider()
            st.subheader("Tren Kunjungan")
            df_pemeriksaan_tren = df_pemeriksaan[df_pemeriksaan['warga_id'].isin(df_warga_final_filter['id'])]
            if not df_pemeriksaan_tren.empty:
                kehadiran_per_hari = df_pemeriksaan_tren.groupby('tanggal_pemeriksaan').size().reset_index(name='jumlah_hadir')
                fig_tren, ax_tren = plt.subplots(figsize=(10, 4))
                ax_tren.plot(kehadiran_per_hari['tanggal_pemeriksaan'], kehadiran_per_hari['jumlah_hadir'], marker='o', linestyle='-')
                ax_tren.set_ylabel("Jumlah Kunjungan"); ax_tren.grid(True, linestyle='--', alpha=0.6)
                plt.xticks(rotation=45); fig_tren.tight_layout(); st.pyplot(fig_tren)

            # --- Tombol Unduh PDF ---
            st.divider()
            if not df_laporan_harian.empty:
                pdf_buffer = generate_pdf_report(
                    filters={"selected_date_str": selected_date.strftime('%d %B %Y'), "rt": selected_wilayah, "kategori": selected_kategori, "gender": selected_gender},
                    metrics={"total_warga": total_warga_terfilter, "hadir_hari_ini": hadir_hari_itu, "partisipasi_hari_ini": partisipasi_hari_itu},
                    df_rinci=df_laporan_harian[['nama_lengkap', 'rt', 'blok', 'tensi_sistolik', 'tensi_diastolik', 'berat_badan_kg']],
                    fig_tren=fig_tren, fig_pie=fig_pie
                )
                st.download_button(
                    label="📥 Unduh Laporan PDF",
                    data=pdf_buffer,
                    file_name=f"Laporan Posyandu {selected_date.strftime('%Y-%m-%d')}.pdf",
                    mime="application/pdf"
                )

    except Exception as e:
        st.error(f"Gagal membuat laporan: {e}")

# --- JALANKAN HALAMAN ---
page_dashboard()