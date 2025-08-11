# data_utils.py

# ... (kode load_raw_data tetap ada di atas) ...

def calculate_age(dataframe, reference_date):
    """
    Menghitung dan menambahkan kolom 'usia' ke DataFrame warga.

    Args:
        dataframe (pd.DataFrame): DataFrame warga yang berisi 'tanggal_lahir'.
        reference_date (datetime): Tanggal acuan untuk menghitung usia.

    Returns:
        pd.DataFrame: DataFrame yang sama dengan tambahan kolom 'usia'.
    """
    if 'tanggal_lahir' not in dataframe.columns or dataframe.empty:
        return dataframe
    
    # Buat salinan agar tidak mengubah DataFrame asli secara langsung (best practice)
    df_copy = dataframe.copy()
    
    # Logika perhitungan usia sekarang ada di satu tempat
    df_copy['usia'] = (pd.to_datetime(reference_date) - df_copy['tanggal_lahir']).dt.days / 365.25
    return df_copy