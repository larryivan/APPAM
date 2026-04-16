import pandas as pd


def load_samples(samples_file):
    df = pd.read_csv(samples_file, sep="\t", dtype=str)
    if "sample_id" not in df.columns:
        raise ValueError("samples_file must include a 'sample_id' column")
    samples = df["sample_id"].dropna().astype(str).str.strip()
    return [sample for sample in samples if sample]
