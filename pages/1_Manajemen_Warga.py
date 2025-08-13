# pages/1_Manajemen_Warga.py

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from supabase import create_client
from datetime import date, datetime
from matplotlib.ticker import MultipleLocator
from typing import Dict, Any, Tuple

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

def hitung_usia_saat_periksa(tanggal_lahir_warga, tanggal_pemeriksaan):
    """
    Menghitung usia pada tanggal pemeriksaan berdasarkan tanggal lahir warga.
    Mengembalikan usia dalam format string "X thn, Y bln".
    """
    try:
        # Konversi string tanggal lahir ke objek date
        tgl_lahir = datetime.strptime(tanggal_lahir_warga, '%Y-%m-%d').date()

        # Konversi string tanggal pemeriksaan ke objek date
        # Mengatasi format ISO 8601 dengan informasi zona waktu
        tgl_periksa = datetime.fromisoformat(tanggal_pemeriksaan.replace('Z', '+00:00')).date()

        # Menghitung selisih hari total
        selisih_hari = (tgl_periksa - tgl_lahir).days
        
        # Menghitung tahun dan sisa hari
        tahun = selisih_hari // 365
        sisa_hari = selisih_hari % 365
        
        # Menghitung bulan dari sisa hari (aproksimasi)
        bulan = sisa_hari // 30
        
        return f"{tahun} thn, {bulan} bln"
    except (ValueError, TypeError, AttributeError):
        # Mengembalikan N/A jika ada masalah dengan format tanggal
        return "N/A"


# ==============================================================================
# BAGIAN KODE UNTUK GRAFIK KMS (0-5 TAHUN)
# ==============================================================================

# --- KONFIGURASI KURVA PERTUMBUHAN WHO ---
CONFIG: Dict[str, Dict[str, Any]] = {
    "wfa": {
        "title": "Berat Badan menurut Umur", "y_col": "berat_kg", "y_label": "Berat Badan (kg)",
        "interpretation_func": lambda berat, z: get_interpretation_wfa(berat, z),
        "ranges": [
            {"max_age": 24, "xlim": (0, 24), "ylim": (0, 18), "x_major": 1, "y_major": 1, "age_range_label": "0-24 Bulan"},
            {"max_age": 61, "xlim": (24, 60), "ylim": (7, 30), "x_major": 1, "y_major": 1, "age_range_label": "24-60 Bulan"},
        ],
        "file_pattern": "wfa_{gender}_0-to-5-years_zscores.xlsx", "x_axis_label": "Umur (Bulan)",
    },
    "wfh": {
        "title": "Berat Badan menurut Tinggi/Panjang Badan", "x_col": "tinggi_cm", "y_col": "berat_kg", "y_label": "Berat Badan (kg)",
        "interpretation_func": lambda berat, z: get_interpretation_wfh(berat, z),
        "ranges": [
            {"max_age": 24, "file_key": "wfl", "x_col_std": "Length", "x_label": "Panjang Badan (cm)", "xlim": (45, 110), "ylim": (1, 25), "x_major": 5, "y_major": 2},
            {"max_age": 61, "file_key": "wfh", "x_col_std": "Height", "x_label": "Tinggi Badan (cm)", "xlim": (65, 120), "ylim": (5, 31), "x_major": 5, "y_major": 2},
        ],
        "file_pattern": "{file_key}_{gender}_{age_group}_zscores.xlsx",
    },
    "bmi": {
        "title": "Indeks Massa Tubuh (IMT) menurut Umur", "y_col": "bmi", "y_label": "IMT (kg/m²)",
        "interpretation_func": lambda bmi, z: get_interpretation_bmi(bmi, z),
        "ranges": [
            {"max_age": 24, "xlim": (0, 24), "ylim": (9, 23), "x_major": 1, "y_major": 1, "age_range_label": "0-24 Bulan"},
            {"max_age": 61, "xlim": (24, 60), "ylim": (11.6, 21), "x_major": 2, "y_major": 1, "age_range_label": "24-60 Bulan"},
        ],
        "file_pattern": "bmi_{gender}_{age_group}_zscores.xlsx", "x_axis_label": "Umur (Bulan)",
    },
    "lhfa": {
        "title": "Panjang/Tinggi Badan menurut Umur", "y_col": "tinggi_cm", "y_label": "Panjang/Tinggi Badan (cm)",
        "interpretation_func": lambda tinggi, z: get_interpretation_lhfa(tinggi, z),
        "ranges": [
            {"max_age": 24, "xlim": (0, 24), "ylim": (43, 100), "x_major": 1, "y_major": 5, "age_range_label": "0-24 Bulan"},
            {"max_age": 61, "xlim": (24, 60), "ylim": (76, 125), "x_major": 2, "y_major": 5, "age_range_label": "2-5 Tahun"},
        ],
        "file_pattern": "lhfa_{gender}_{age_group}_zscores.xlsx", "x_axis_label": "Umur (Bulan)",
    },
    "hcfa": {
        "title": "Lingkar Kepala menurut Umur", "y_col": "lingkar_kepala_cm", "y_label": "Lingkar Kepala (cm)",
        "interpretation_func": lambda hc, z: get_interpretation_hcfa(hc, z),
        "ranges": [
            {"max_age": 24, "xlim": (0, 24), "ylim": (32, 52), "x_major": 1, "y_major": 1, "age_range_label": "0-24 Bulan"},
            {"max_age": 61, "xlim": (24, 60), "ylim": (42, 56), "x_major": 2, "y_major": 1, "age_range_label": "2-5 Tahun"},
        ],
        "file_pattern": "hcfa_{gender}_0-to-5-years-zscores.xlsx", "x_axis_label": "Umur (Bulan)",
    },
}

# --- FUNGSI-FUNGSI PEMBANTU UNTUK KMS ---

@st.cache_data(ttl=3600)
def load_who_data(file_path: str) -> pd.DataFrame:
    """Memuat dan menyimpan cache data dari file Excel standar WHO."""
    try:
        return pd.read_excel(file_path)
    except FileNotFoundError:
        st.error(f"File standar WHO tidak ditemukan: {file_path}. Pastikan file ada di direktori aplikasi.")
        return None

def calculate_age_in_months(birth_date: date, measurement_date: date) -> int:
    """Menghitung usia dalam bulan penuh."""
    if isinstance(birth_date, str):
        birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
    if isinstance(measurement_date, str):
        measurement_date = datetime.fromisoformat(measurement_date.replace('Z', '+00:00')).date()
    
    return (measurement_date.year - birth_date.year) * 12 + (measurement_date.month - birth_date.month)

def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """Menghitung Indeks Massa Tubuh (IMT)."""
    if height_cm == 0 or weight_kg == 0:
        return 0.0
    return weight_kg / ((height_cm / 100) ** 2)

# --- FUNGSI INTERPRETASI STATUS GIZI ---
def get_interpretation_wfa(berat_anak: float, z: Dict) -> Tuple[str, str]:
    if berat_anak > z['SD3']: return "Berat badan sangat lebih", 'red'
    elif berat_anak > z['SD2']: return "Berat badan lebih", 'yellow'
    elif berat_anak >= z['SD2neg']: return "Berat badan normal", 'forestgreen'
    elif berat_anak > z['SD3neg']: return "Berat badan kurang", 'yellow'
    else: return "Berat badan sangat kurang (Underweight)", 'red'

def get_interpretation_wfh(berat_anak: float, z: Dict) -> Tuple[str, str]:
    if berat_anak > z['SD3']: return "Gizi lebih (Obesitas)", 'red'
    elif berat_anak > z['SD2']: return "Berisiko gizi lebih (Overweight)", 'yellow'
    elif berat_anak >= z['SD2neg']: return "Gizi baik (Normal)", 'forestgreen'
    elif berat_anak >= z['SD3neg']: return "Gizi kurang (Wasting)", 'yellow'
    else: return "Gizi buruk (Severe Wasting)", 'red'

def get_interpretation_bmi(bmi_anak: float, z: Dict) -> Tuple[str, str]:
    if bmi_anak > z['SD3']: return "Gizi lebih (Obesitas)", 'red'
    elif bmi_anak > z['SD2']: return "Berisiko gizi lebih (Overweight)", 'yellow'
    elif bmi_anak >= z['SD2neg']: return "Gizi baik (Normal)", 'forestgreen'
    elif bmi_anak >= z['SD3neg']: return "Gizi kurang (Wasting)", 'yellow'
    else: return "Gizi buruk (Severe Wasting)", 'red'

def get_interpretation_lhfa(panjang_anak: float, z: Dict) -> Tuple[str, str]:
    if panjang_anak > z['SD2']: return "Tinggi", 'forestgreen'
    elif panjang_anak >= z['SD2neg']: return "Normal", 'forestgreen'
    elif panjang_anak >= z['SD3neg']: return "Pendek (Stunting)", 'yellow'
    else: return "Sangat Pendek (Severe Stunting)", 'red'

def get_interpretation_hcfa(hc_anak: float, z: Dict) -> Tuple[str, str]:
    if hc_anak > z['SD2']: return "Makrosefali", 'yellow'
    elif hc_anak >= z['SD2neg']: return "Normal", 'forestgreen'
    else: return "Mikrosefali", 'yellow'

# --- FUNGSI PLOTTING UTAMA UNTUK KMS ---
def create_growth_chart(ax: plt.Axes, chart_type: str, history_df: pd.DataFrame, gender: str, latest_data: pd.Series):
    cfg = CONFIG[chart_type]
    is_age_based = cfg.get("x_axis_label", "").endswith("(Bulan)")
    x_col = cfg.get("x_col", "usia_bulan")
    y_col = cfg["y_col"]
    
    x_latest = latest_data[x_col]
    y_latest = latest_data[y_col]
    
    if y_latest is None or y_latest <= 0:
        ax.text(0.5, 0.5, 'Data tidak tersedia', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
        ax.set_title(f"Grafik {cfg['title']}", pad=20, fontsize=16)
        return

    if is_age_based:
        range_cfg = next((r for r in cfg["ranges"] if x_latest < r["max_age"]), cfg["ranges"][-1])
        age_group_map = {24: "0-to-2-years", 61: "2-to-5-years"}
        age_group = next((v for k, v in age_group_map.items() if x_latest < k), "2-to-5-years")
        file_name = cfg["file_pattern"].format(gender="girls" if gender == 'P' else "boys", age_group=age_group)
        x_col_std = "Month"
    else: 
        range_cfg = next((r for r in cfg["ranges"] if latest_data['usia_bulan'] < r["max_age"]), cfg["ranges"][-1])
        age_group_map = {24: "0-to-2-years", 61: "2-to-5-years"}
        age_group = next((v for k, v in age_group_map.items() if latest_data['usia_bulan'] < k), "2-to-5-years")
        file_name = cfg["file_pattern"].format(file_key=range_cfg["file_key"], gender="girls" if gender == 'P' else "boys", age_group=age_group)
        x_col_std = range_cfg["x_col_std"]
        
    df_std = load_who_data(f"data/{file_name}")
    if df_std is None: return
    
    df_std = df_std.rename(columns={x_col_std: 'x_std'}).sort_values('x_std').drop_duplicates('x_std')
    z_cols = ['SD3neg', 'SD2neg', 'SD1neg', 'SD0', 'SD1', 'SD2', 'SD3']
    poly_funcs = {col: np.poly1d(np.polyfit(df_std['x_std'], df_std[col], 5)) for col in z_cols}
    z_scores_at_point = {col: func(x_latest) for col, func in poly_funcs.items()}
    
    interpretation, color = cfg["interpretation_func"](y_latest, z_scores_at_point)
    st.info(f"**{cfg['title']}:** {interpretation}")

    fig = ax.figure
    fig.set_facecolor('hotpink' if gender == 'P' else 'steelblue')
    x_smooth = np.linspace(df_std['x_std'].min(), df_std['x_std'].max(), 300)
    smooth_data = {col: func(x_smooth) for col, func in poly_funcs.items()}

    ax.fill_between(x_smooth, smooth_data['SD3neg'], smooth_data['SD2neg'], color='yellow', alpha=0.5)
    ax.fill_between(x_smooth, smooth_data['SD2neg'], smooth_data['SD2'], color='green', alpha=0.4)
    ax.fill_between(x_smooth, smooth_data['SD2'], smooth_data['SD3'], color='yellow', alpha=0.5)
    
    for col, data in smooth_data.items():
        ax.plot(x_smooth, data, color='red' if col in ['SD3', 'SD3neg'] else 'black', lw=1, alpha=0.8)

    ax.plot(history_df[x_col].astype(float), history_df[y_col].astype(float), marker='o', linestyle='-', color='darkviolet', label='Riwayat Pertumbuhan')
    ax.scatter(x_latest, y_latest, marker='*', c='cyan', s=300, ec='black', zorder=10, label='Pengukuran Terakhir')

    # Anotasi dan Label
    props = dict(boxstyle='round', facecolor=color, alpha=0.8)
    ax.text(0.03, 0.97, f"Interpretasi: {interpretation}", transform=ax.transAxes, fontsize=12, va='top', bbox=props)

    title_text = f"Grafik {cfg['title']} - {'Perempuan' if gender == 'P' else 'Laki-laki'}"
    if 'age_range_label' in range_cfg:
        title_text += f" ({range_cfg['age_range_label']})"
        
    ax.set_title(title_text, pad=20, fontsize=16, color='white', fontweight='bold')
    ax.set_xlabel(cfg.get('x_axis_label') or range_cfg.get('x_label'), fontsize=12, color='white')
    ax.set_ylabel(cfg['y_label'], fontsize=12, color='white')
    
    ax.set_xlim(range_cfg["xlim"])
    ax.set_ylim(range_cfg["ylim"])

    ax2 = ax.twinx(); ax2.set_ylim(ax.get_ylim())
    ax2.yaxis.set_major_locator(MultipleLocator(range_cfg["y_major"]))
    ax2.yaxis.set_minor_locator(MultipleLocator(range_cfg["y_minor"]))

    ax.xaxis.set_major_locator(MultipleLocator(range_cfg["x_major"]))
    ax.yaxis.set_major_locator(MultipleLocator(range_cfg["y_major"]))

    for spine_position in ['top', 'bottom', 'left', 'right']:
        ax.spines[spine_position].set_visible(False)
        ax2.spines[spine_position].set_visible(False)

    ax.grid(which='major', linestyle='-', linewidth='0.8', color='gray')
    ax.grid(which='minor', axis='y', linestyle=':', linewidth='0.5', color='lightgray')
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')
    ax.legend(loc='lower right')
    fig.tight_layout()

def plot_all_kms_curves(history_df: pd.DataFrame):
    """Fungsi utama untuk menampilkan semua kurva pertumbuhan KMS."""
    st.subheader("📈 Grafik Pertumbuhan Anak (KMS)")
    if history_df.empty:
        st.warning("Data riwayat tidak tersedia untuk membuat grafik.")
        return

    # Siapkan data
    history_df['bmi'] = history_df.apply(lambda row: calculate_bmi(row['berat_kg'], row['tinggi_cm']), axis=1)
    latest_data = history_df.sort_values(by='usia_bulan').iloc[-1]
    gender = latest_data['jenis_kelamin']

    charts_to_plot = ["wfa", "lhfa", "wfh", "bmi", "hcfa"]
    for chart_type in charts_to_plot:
        st.markdown("---")
        fig, ax = plt.subplots(figsize=(12, 7))
        try:
            create_growth_chart(ax, chart_type, history_df, gender, latest_data)
            st.pyplot(fig)
        except Exception as e:
            st.error(f"Gagal membuat grafik {chart_type.upper()}: {e}")
        plt.close(fig)

# ==============================================================================
# BAGIAN KODE UNTUK GRAFIK TREN UMUM (DI ATAS 5 TAHUN)
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
# FUNGSI HALAMAN UTAMA (MANAJEMEN WARGA)
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
                df_pemeriksaan = pd.DataFrame(pemeriksaan_response.data).fillna(0)

                # # df_pemeriksaan['usia_thn_bln'] = df_pemeriksaan['tanggal_lahir'].apply(
                # #     lambda tgl: format_usia_teks(tgl, df_pemeriksaan['tanggal_pemeriksaan'])
                # # ) #13082025 tambahkolom usia dalam tahun bulan

                # st.dataframe(df_pemeriksaan[['tanggal_pemeriksaan', 'berat_badan_kg', 'tinggi_badan_cm', 'lingkar_lengan_cm', 'lingkar_kepala_cm', 'tensi_sistolik', 'tensi_diastolik', 'gula_darah', 'kolesterol']])

                # === PERUBAHAN DIMULAI DI SINI ===
                # 1. Ambil tanggal lahir warga yang sedang dipilih.
                tgl_lahir_warga = selected_warga_data['tanggal_lahir']

                # 2. Buat kolom baru 'Usia' dengan menerapkan fungsi hitung_usia_saat_periksa.
                #    Kita gunakan lambda untuk memberikan tanggal lahir (konstan) dan tanggal pemeriksaan (berubah per baris) ke fungsi.
                df_pemeriksaan['Usia'] = df_pemeriksaan['tanggal_pemeriksaan'].apply(
                    lambda tgl_periksa: hitung_usia_saat_periksa(tgl_lahir_warga, tgl_periksa)
                )

                # 3. Definisikan urutan kolom untuk ditampilkan, letakkan 'Usia' di depan.
                kolom_tampil = [
                    'tanggal_pemeriksaan', 
                    'Usia',  # Kolom baru ditambahkan di sini
                    'berat_badan_kg', 
                    'tinggi_badan_cm', 
                    'lingkar_lengan_cm', 
                    'lingkar_kepala_cm', 
                    'tensi_sistolik', 
                    'tensi_diastolik', 
                    'gula_darah', 
                    'kolesterol'
                ]
                
                # 4. Tampilkan DataFrame dengan kolom baru dan urutan yang sudah diatur.
                st.dataframe(df_pemeriksaan[kolom_tampil], use_container_width=True)
                # === AKHIR PERUBAHAN ===

                # --- MODIFIKASI DIMULAI DI SINI: LOGIKA KONDISIONAL UNTUK GRAFIK ---
                # 1. Hitung usia pada pemeriksaan terakhir dalam bulan
                latest_exam_date = pd.to_datetime(df_pemeriksaan['tanggal_pemeriksaan'].iloc[0]).date()
                birth_date_obj = pd.to_datetime(selected_warga_data['tanggal_lahir']).date()
                latest_age_months = calculate_age_in_months(birth_date_obj, latest_exam_date)

                # 2. Tentukan grafik yang akan ditampilkan berdasarkan usia
                if latest_age_months <= 60:
                    # --- JIKA USIA <= 5 TAHUN, TAMPILKAN GRAFIK KMS ---
                    df_kms = df_pemeriksaan.copy()
                    df_kms = df_kms.rename(columns={
                        'berat_badan_kg': 'berat_kg',
                        'tinggi_badan_cm': 'tinggi_cm',
                    })
                    
                    df_kms['jenis_kelamin'] = selected_warga_data['jenis_kelamin']
                    df_kms['usia_bulan'] = df_kms.apply(
                        lambda row: calculate_age_in_months(birth_date_obj, row['tanggal_pemeriksaan']), axis=1
                    )
                    
                    plot_all_kms_curves(df_kms)
                else:
                    # --- JIKA USIA > 5 TAHUN, TAMPILKAN GRAFIK TREN BIASA ---
                    plot_individual_trends(df_pemeriksaan.copy())
                # --- AKHIR MODIFIKASI ---

                # plot_individual_trends(df_pemeriksaan)


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
                            edit_berat_badan = st.number_input("Berat Badan (kg)", value=float(selected_pemeriksaan['berat_badan_kg']))
                            edit_tinggi_badan = st.number_input("Tinggi Badan (cm)", value=float(selected_pemeriksaan['tinggi_badan_cm']))
                            edit_lingkar_lengan = st.number_input("Lingkar Lengan (cm)", value=float(selected_pemeriksaan['lingkar_lengan_cm']))
                            edit_lingkar_perut = st.number_input("Lingkar Perut (cm)", value=float(selected_pemeriksaan['lingkar_perut_cm']))
                            edit_lingkar_kepala = st.number_input("Lingkar Kepala (cm)", value=float(selected_pemeriksaan['lingkar_kepala_cm']))
                            
                        with col2:
                            edit_tensi_sistolik = st.number_input("Tensi Sistolik (mmHg)", value=int(selected_pemeriksaan['tensi_sistolik']))
                            edit_tensi_diastolik = st.number_input("Tensi Diastolik (mmHg)", value=int(selected_pemeriksaan['tensi_diastolik']))
                            edit_gula_darah = st.number_input("Gula Darah (mg/dL)", value=int(selected_pemeriksaan['gula_darah']))
                            edit_kolesterol = st.number_input("Kolesterol (mg/dL)", value=int(selected_pemeriksaan['kolesterol']))
                        
                        edit_catatan = st.text_area("Catatan", value=selected_pemeriksaan['catatan'])

                        if st.form_submit_button("Simpan Perubahan Pemeriksaan"):
                            try:
                                update_data = {
                                    "tensi_sistolik": edit_tensi_sistolik, "tensi_diastolik": edit_tensi_diastolik,
                                    "tinggi_badan_cm": edit_tinggi_badan, "berat_badan_kg": edit_berat_badan, "lingkar_perut_cm": edit_lingkar_perut,
                                    "lingkar_lengan_cm": edit_lingkar_lengan, "lingkar_kepala_cm": edit_lingkar_kepala, "gula_darah": edit_gula_darah,
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