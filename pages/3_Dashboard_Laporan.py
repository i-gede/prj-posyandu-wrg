# pages/3_Dashboard_Laporan.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go # <-- Pustaka tambahan untuk kustomisasi
from supabase import create_client
from datetime import date, datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

# --- KONEKSI & KEAMANAN ---
st.set_page_config(page_title="Dashboard & Laporan", page_icon="📈", layout="wide")

if not st.session_state.get("authenticated", False):
    st.error("🔒 Anda harus login untuk mengakses halaman ini.")
    st.stop()

supabase = st.session_state.get('supabase_client')
if not supabase:
    st.error("Koneksi Supabase tidak ditemukan. Silakan login kembali.")
    st.stop()

# --- FUNGSI PEMBUAT GRAFIK (PLOTLY VERSION) ---
def buat_grafik_gender_plotly(laki, perempuan, height=100, warna_laki='#6495ED', warna_perempuan='#FFB6C1'):
    """Membuat dan mengembalikan objek figure Plotly untuk grafik gender."""
    if laki == 0 and perempuan == 0:
        return None  # Tidak perlu membuat grafik jika tidak ada data

    data = {'Jumlah': [laki, perempuan], 'Gender': ['Laki-laki', 'Perempuan']}
    df_chart = pd.DataFrame(data)

    fig = px.bar(df_chart, x='Jumlah', y='Gender', orientation='h', text='Jumlah', color='Gender',
                 color_discrete_map={'Laki-laki': warna_laki, 'Perempuan': warna_perempuan})

    fig.update_layout(
        showlegend=False,
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color="white")
    )
    fig.update_traces(textposition='inside', textfont_size=14, textfont_color='white',
                      marker_line_width=0)
    return fig

def buat_grafik_partisipasi_plotly(hadir, tidak_hadir, title):
    """Membuat dan mengembalikan objek figure Plotly untuk donut chart partisipasi."""
    if hadir == 0 and tidak_hadir == 0:
        return None

    labels = ['Hadir', 'Tidak Hadir']
    values = [hadir, tidak_hadir]
    colors_pie = ['#4CAF50', '#FFC107']
    
    partisipasi_percent = (hadir / (hadir + tidak_hadir)) * 100 if (hadir + tidak_hadir) > 0 else 0

    fig = go.Figure(data=[go.Pie(
        labels=labels, 
        values=values, 
        hole=.5,
        textinfo='label+value',
        marker_colors=colors_pie,
        hoverinfo='label+percent'
    )])
    
    fig.update_layout(
        title={
            'text': title,
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 14}
        },
        annotations=[dict(text=f'{partisipasi_percent:.1f}%', x=0.5, y=0.5, font_size=20, showarrow=False)],
        showlegend=False,
        margin=dict(l=20, r=20, t=40, b=20),
        height=250
    )
    return fig

# --- FUNGSI PEMBANTU PDF (VERSI BARU) ---
def convert_fig_to_image(fig, width, height):
    """Mengubah figure Plotly menjadi objek Image ReportLab."""
    if fig is None:
        return Spacer(0, 0)
    img_buffer = BytesIO()
    fig.write_image(img_buffer, format='png', scale=3) # Scale ditingkatkan untuk resolusi lebih baik
    img_buffer.seek(0)
    return Image(img_buffer, width=width, height=height)
    
def generate_pdf_report(report_data):
    """Membuat laporan PDF dari data yang sudah disiapkan."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=inch*0.8, leftMargin=inch*0.8, topMargin=inch*0.8, bottomMargin=inch*0.8)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))
    styles.add(ParagraphStyle(name='H2_Dark', parent=styles['h2'], textColor=colors.darkslategray))

    elements = []

    # --- Header ---
    elements.append(Paragraph("Laporan Posyandu Mawar - KBU", styles['h1']))
    elements.append(Spacer(1, 0.2 * inch))
    
    filters = report_data['filters']
    filter_text = f"<b>Filter Laporan:</b><br/>- Tanggal: {filters['selected_date_str']}<br/>- Wilayah: {filters['rt']}<br/>- Kategori Usia: {filters['kategori']}<br/>- Jenis Kelamin: {filters['gender']}"
    elements.append(Paragraph(filter_text, styles['Normal']))
    elements.append(Spacer(1, 0.3 * inch))

    # --- Ringkasan Metrik ---
    elements.append(Paragraph("Ringkasan Laporan", styles['H2_Dark']))
    metrics = report_data['metrics']
    metric_data = [
        ['Total Warga (sesuai filter)', f": {metrics['total_warga']}"],
        ['Jumlah Kunjungan (Hadir)', f": {metrics['hadir_hari_ini']}"],
        ['Tingkat Partisipasi', f": {metrics['partisipasi_hari_ini']:.1f}%"]
    ]
    metric_table = Table(metric_data, colWidths=[2.5*inch, 3.5*inch])
    metric_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'LEFT'), ('FONTNAME', (0,0), (-1,-1), 'Helvetica'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    elements.append(metric_table)
    elements.append(Spacer(1, 0.3 * inch))

    # --- Grafik Komposisi & Partisipasi ---
    elements.append(Paragraph("Diagram Komposisi Warga", styles['H2_Dark']))
    elements.append(convert_fig_to_image(report_data['figures']['komposisi_warga'], width=6.5*inch, height=4.5*inch))
    elements.append(Spacer(1, 0.1 * inch))

    elements.append(Paragraph("Diagram Partisipasi Warga Hadir", styles['H2_Dark']))
    elements.append(convert_fig_to_image(report_data['figures']['partisipasi_warga'], width=6.5*inch, height=4.5*inch))

    # --- Halaman Baru ---
    elements.append(PageBreak())

    # --- Demografi Rinci per Kategori ---
    elements.append(Paragraph("Rincian Demografi Wilayah", styles['H2_Dark']))
    for item in report_data['demografi_rinci']:
        if item['total'] > 0:
            text_content = f"""
            <b>{item['label']}</b><br/>
            👥 Total: <b>{item['total']}</b><br/>
            👦 Laki-laki: <b>{item['laki']}</b><br/>
            👧 Perempuan: <b>{item['perempuan']}</b>
            """
            p = Paragraph(text_content, styles['Normal'])
            img = convert_fig_to_image(item['fig'], width=3*inch, height=0.8*inch)
            
            # Tabel untuk layout 2 kolom (teks | grafik)
            table_layout = Table([[p, img]], colWidths=[3*inch, 3.2*inch])
            table_layout.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
            elements.append(table_layout)
            elements.append(Spacer(1, 0.15*inch))

    # --- Grafik Partisipasi per Kategori ---
    elements.append(Paragraph("Tingkat Partisipasi Berdasarkan Usia", styles['H2_Dark']))
    donut_charts = report_data['figures']['partisipasi_kategori']
    # Tabel untuk layout 2x2
    table_data = [
        [convert_fig_to_image(donut_charts.get(0), width=3*inch, height=2.5*inch), convert_fig_to_image(donut_charts.get(1), width=3*inch, height=2.5*inch)],
        [convert_fig_to_image(donut_charts.get(2), width=3*inch, height=2.5*inch), convert_fig_to_image(donut_charts.get(3), width=3*inch, height=2.5*inch)],
        [convert_fig_to_image(donut_charts.get(4), width=3*inch, height=2.5*inch), convert_fig_to_image(donut_charts.get(5), width=3*inch, height=2.5*inch)],
        [convert_fig_to_image(donut_charts.get(6), width=3*inch, height=2.5*inch), Spacer(0,0)],
    ]
    partisipasi_table = Table(table_data, colWidths=[3.25*inch, 3.25*inch])
    elements.append(partisipasi_table)


    # --- Tabel Data Rinci (Hadir & Tidak Hadir) ---
    def create_data_table(df, title, bg_color):
        elements.append(PageBreak())
        elements.append(Paragraph(title, styles['H2_Dark']))
        elements.append(Spacer(1, 0.2*inch))
        if not df.empty:
            df = df.copy()
            df.insert(0, "No", range(1, len(df) + 1))
            table_data = [df.columns.to_list()] + df.values.tolist()
            data_table = Table(table_data, repeatRows=1, hAlign='LEFT')
            data_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), bg_color), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,0), 10),
                ('BOTTOMPADDING', (0,0), (-1,0), 12), ('BACKGROUND', (0,1), (-1,-1), colors.beige),
                ('GRID', (0,0), (-1,-1), 1, colors.black), ('FONTSIZE', (0,1), (-1,-1), 9)
            ]))
            elements.append(data_table)
        else:
            elements.append(Paragraph("Tidak ada data untuk ditampilkan.", styles['Normal']))

    create_data_table(report_data['dataframes']['rinci_hadir'], "Data Rinci Kunjungan (Warga Hadir)", colors.darkslategray)
    create_data_table(report_data['dataframes']['tidak_hadir'], "Data Warga Tidak Hadir", colors.darkred)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- FUNGSI HALAMAN UTAMA ---
def get_kategori(usia):
    if usia <= 0.5: return "Bayi (0-6 bln)"
    if usia <= 2: return "Baduta (>6 bln - 2 thn)"
    if usia <= 5: return "Balita (>2 - 5 thn)"
    if usia < 6: return "Anak Pra-Sekolah (>5 - <6 thn)"
    if usia <= 18: return "Anak Usia Sekolah dan Remaja (6 - 18 thn)"
    if usia < 60: return "Dewasa (>18 - <60 thn)"
    return "Lansia (≥60 thn)"

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

            # Siapkan data filter untuk PDF
            filters_for_pdf = {
                'selected_date_str': selected_date.strftime('%d %B %Y'),
                'rt': selected_wilayah,
                'kategori': selected_kategori,
                'gender': selected_gender
            }

            df_warga_wilayah = df_warga.copy()
            if selected_wilayah != "Lingkungan (Semua RT)":
                df_warga_wilayah = df_warga[df_warga['rt'] == selected_wilayah]
            
            # --- Perhitungan Demografi Global ---
            total_warga_wilayah = len(df_warga_wilayah)
            laki_wilayah = df_warga_wilayah[df_warga_wilayah['jenis_kelamin'] == 'L'].shape[0]
            perempuan_wilayah = total_warga_wilayah - laki_wilayah

            # --- Tampilan Demografi Header ---
            st.write("#### Demografi Wilayah")
            rt_label = f"RT{selected_wilayah.zfill(3)}" if selected_wilayah.isdigit() else "Lingkungan Karang Baru Utara"
            if selected_wilayah == "Lingkungan (Semua RT)":
                rt_label = "Lingkungan Karang Baru Utara"

            with st.container(border=True):
                col_kiri, col_kanan = st.columns([3, 2])
                with col_kiri:
                    st.markdown(f"### {rt_label}")
                    st.markdown(f"#### Jumlah Warga: **{total_warga_wilayah}**")
                    st.markdown(f"##### 👦 Laki-laki: **{laki_wilayah}** | 👧 Perempuan: **{perempuan_wilayah}**")
                with col_kanan:
                    fig_gender_total = buat_grafik_gender_plotly(laki_wilayah, perempuan_wilayah)
                    if fig_gender_total:
                        st.plotly_chart(fig_gender_total, use_container_width=True)

            # --- [ SUNBURST KOMPOSISI WARGA ] ---
            st.subheader("Komposisi Warga")
            df_komposisi = df_warga_wilayah.copy()
            df_komposisi['kategori_usia'] = df_komposisi['usia'].apply(get_kategori)
            df_komposisi['jenis_kelamin_label'] = df_komposisi['jenis_kelamin'].map({'L': 'Laki-laki', 'P': 'Perempuan'}).fillna('N/A')
            df_komposisi['count'] = 1 
            if selected_gender != "Semua":
                df_komposisi = df_komposisi[df_komposisi['jenis_kelamin_label'] == selected_gender]

            fig_sunburst_komposisi = None
            if not df_komposisi.empty:
                total_warga = len(df_komposisi)
                df_komposisi['total_label'] = f'Total Warga: {total_warga}'
                fig_sunburst_komposisi = px.sunburst(
                    df_komposisi, path=['total_label', 'kategori_usia', 'jenis_kelamin_label'],
                    values='count', title='Diagram Komposisi Warga (Total > Kategori Usia > Jenis Kelamin)',
                    color='kategori_usia', color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_sunburst_komposisi.update_layout(margin=dict(t=50, l=25, r=25, b=25))
                fig_sunburst_komposisi.update_traces(textinfo='label+percent parent', insidetextorientation='radial')
                st.plotly_chart(fig_sunburst_komposisi, use_container_width=True)
            else:
                st.info("Tidak ada data komposisi warga yang cocok dengan filter.")

            # --- [ RINCIAN DEMOGRAFI PER KATEGORI ] ---
            kategori_defs = {
                "Bayi (0-6 bln)": (lambda u: u <= 0.5),
                "Baduta (>6 bln - 2 thn)": (lambda u: 0.5 < u <= 2),
                "Balita (>2 - 5 thn)": (lambda u: 2 < u <= 5),
                "Anak Pra-Sekolah (>5 - <6 thn)": (lambda u: 5 < u < 6),
                "Anak Usia Sekolah dan Remaja (6 - 18 thn)": (lambda u: 6 <= u <= 18),
                "Dewasa (>18 - <60 thn)": (lambda u: 18 < u < 60),
                "Lansia (≥60 thn)": (lambda u: u >= 60)
            }
            demografi_rinci_pdf = []

            with st.expander("Lihat Rinci Data Komposisi Warga"):
                for label, kriteria in kategori_defs.items():
                    df_kategori = df_warga_wilayah[df_warga_wilayah['usia'].apply(kriteria)]
                    total = len(df_kategori)
                    laki = len(df_kategori[df_kategori['jenis_kelamin'] == 'L'])
                    perempuan = total - laki
                    
                    if total > 0:
                        with st.container(border=True):
                            col_teks, col_grafik = st.columns([2, 1.5])
                            with col_teks:
                                st.markdown(f"**{label}**")
                                st.markdown(f"👥 Total: **{total}**")
                                st.markdown(f"👦 Laki-laki: **{laki}** | 👧 Perempuan: **{perempuan}**")
                            
                            with col_grafik:
                                fig_gender_kategori = buat_grafik_gender_plotly(laki, perempuan, height=80)
                                if fig_gender_kategori:
                                    st.plotly_chart(fig_gender_kategori, use_container_width=True)
                                
                                # Simpan data untuk PDF
                                demografi_rinci_pdf.append({
                                    'label': label, 'total': total, 'laki': laki, 'perempuan': perempuan, 'fig': fig_gender_kategori
                                })

            st.divider()

            # --- [ SUNBURST PARTISIPASI WARGA ] ---
            st.subheader("Ringkasan Partisipasi Warga yang Hadir")
            df_pemeriksaan_harian = df_pemeriksaan[df_pemeriksaan['tanggal_pemeriksaan'] == selected_date]
            id_hadir_keseluruhan = df_pemeriksaan_harian['warga_id'].unique()
            df_partisipasi = df_warga_wilayah[df_warga_wilayah['id'].isin(id_hadir_keseluruhan)].copy()
            
            df_partisipasi['kategori_usia'] = df_partisipasi['usia'].apply(get_kategori)
            df_partisipasi['jenis_kelamin_label'] = df_partisipasi['jenis_kelamin'].map({'L': 'Laki-laki', 'P': 'Perempuan'}).fillna('N/A')
            df_partisipasi['rt_label'] = 'RT ' + df_partisipasi['rt'].astype(str)
            df_partisipasi['count'] = 1

            if selected_gender != "Semua":
                df_partisipasi = df_partisipasi[df_partisipasi['jenis_kelamin_label'] == selected_gender]
            
            fig_sunburst_partisipasi = None
            if not df_partisipasi.empty:
                total_hadir = len(df_partisipasi)
                df_partisipasi['total_label'] = f'Total Hadir: {total_hadir}'
                fig_sunburst_partisipasi = px.sunburst(
                    df_partisipasi, path=['total_label', 'rt_label', 'kategori_usia', 'jenis_kelamin_label'],
                    values='count', title='Diagram Partisipasi Warga Hadir (Total > RT > Kategori Usia > Jenis Kelamin)',
                    color='rt_label', color_discrete_sequence=px.colors.qualitative.Antique
                )
                fig_sunburst_partisipasi.update_layout(margin=dict(t=50, l=25, r=25, b=25))
                fig_sunburst_partisipasi.update_traces(textinfo='label+percent parent', insidetextorientation='radial')
                st.plotly_chart(fig_sunburst_partisipasi, use_container_width=True)
            else:
                st.info("Tidak ada data partisipasi (hadir) yang cocok dengan filter.")

            st.divider()

            # --- [ TINGKAT PARTISIPASI BERDASARKAN USIA (DONUT CHARTS) ] ---
            st.subheader("Tingkat Partisipasi Berdasarkan Usia")
            df_merged = pd.merge(df_pemeriksaan_harian, df_warga_wilayah, left_on='warga_id', right_on='id', how='inner')
            
            df_warga_target = df_warga_wilayah.copy()
            df_hadir_target = df_merged.copy()
            if selected_gender != "Semua":
                gender_code = "L" if selected_gender == "Laki-laki" else "P"
                df_warga_target = df_warga_target[df_warga_target['jenis_kelamin'] == gender_code]
                df_hadir_target = df_hadir_target[df_hadir_target['jenis_kelamin'] == gender_code]

            cols = st.columns(4)
            col_idx = 0
            partisipasi_kategori_figs = {}

            for label, kriteria in kategori_defs.items():
                warga_kategori = df_warga_target[df_warga_target['usia'].apply(kriteria)]
                total_warga_kategori = len(warga_kategori)
                
                if total_warga_kategori > 0:
                    hadir_kategori = df_hadir_target[df_hadir_target['usia'].apply(kriteria)]
                    jumlah_hadir = len(hadir_kategori)
                    jumlah_tidak_hadir = total_warga_kategori - jumlah_hadir
                    
                    fig_donut = buat_grafik_partisipasi_plotly(jumlah_hadir, jumlah_tidak_hadir, label)
                    if fig_donut:
                        with cols[col_idx % 4]:
                            st.plotly_chart(fig_donut, use_container_width=True)
                        partisipasi_kategori_figs[col_idx] = fig_donut
                        col_idx += 1

            st.divider()

            # --- Data Rinci (Hadir & Tidak Hadir) ---
            df_merged['kategori_usia'] = df_merged['usia'].apply(get_kategori)
            df_rinci_hadir = df_merged.copy()
            if selected_kategori != "Tampilkan Semua":
                df_rinci_hadir = df_rinci_hadir[df_rinci_hadir['kategori_usia'] == selected_kategori]
            
            with st.expander("Lihat Data Rinci Warga yang Hadir Posyandu"):
                st.dataframe(df_rinci_hadir[['nama_lengkap', 'rt', 'blok', 'tensi_sistolik', 'tensi_diastolik', 'berat_badan_kg', 'gula_darah', 'kolesterol']], use_container_width=True)

            id_hadir = df_merged['warga_id'].unique()
            df_tidak_hadir = df_warga_wilayah[~df_warga_wilayah['id'].isin(id_hadir)].copy()
            df_tidak_hadir['kategori_usia'] = df_tidak_hadir['usia'].apply(get_kategori)
            if selected_gender != "Semua":
                gender_code = "L" if selected_gender == "Laki-laki" else "P"
                df_tidak_hadir = df_tidak_hadir[df_tidak_hadir['jenis_kelamin'] == gender_code]
            if selected_kategori != "Tampilkan Semua":
                df_tidak_hadir = df_tidak_hadir[df_tidak_hadir['kategori_usia'] == selected_kategori]

            with st.expander("Lihat Data Warga yang Tidak Hadir Posyandu"):
                st.dataframe(df_tidak_hadir[['nama_lengkap', 'rt', 'blok', 'jenis_kelamin']], use_container_width=True)

            # --- Tombol Download PDF ---
            st.divider()
            st.subheader("Cetak Laporan")
            
            if st.button("Buat & Download Laporan PDF"):
                with st.spinner("Membuat laporan PDF, mohon tunggu..."):
                    # Siapkan semua data yang dibutuhkan oleh fungsi PDF
                    report_data_for_pdf = {
                        "filters": filters_for_pdf,
                        "metrics": {
                            'total_warga': total_warga_wilayah,
                            'hadir_hari_ini': len(id_hadir_keseluruhan),
                            'partisipasi_hari_ini': (len(id_hadir_keseluruhan) / total_warga_wilayah * 100) if total_warga_wilayah > 0 else 0
                        },
                        "figures": {
                            'komposisi_warga': fig_sunburst_komposisi,
                            'partisipasi_warga': fig_sunburst_partisipasi,
                            'partisipasi_kategori': partisipasi_kategori_figs
                        },
                        "demografi_rinci": demografi_rinci_pdf,
                        "dataframes": {
                            'rinci_hadir': df_rinci_hadir[['nama_lengkap', 'rt', 'blok', 'tensi_sistolik', 'tensi_diastolik', 'berat_badan_kg']],
                            'tidak_hadir': df_tidak_hadir[['nama_lengkap', 'rt', 'blok', 'jenis_kelamin']]
                        }
                    }
                    
                    pdf_buffer = generate_pdf_report(report_data_for_pdf)
                    
                    st.download_button(
                        label="✅ Download PDF Selesai",
                        data=pdf_buffer,
                        file_name=f"Laporan_Posyandu_{selected_date.strftime('%Y-%m-%d')}.pdf",
                        mime="application/pdf"
                    )

    except Exception as e:
        st.error(f"Terjadi kesalahan saat memuat data atau membuat laporan: {e}")

# Panggil fungsi utama untuk menjalankan halaman
page_dashboard()