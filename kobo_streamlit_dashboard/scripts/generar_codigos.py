"""
Genera códigos de acceso por empresa/encuesta a partir de un Excel o CSV exportado desde KOBO.
Uso local:
    python scripts/generar_codigos.py --input data.xlsx --output data_con_codigos.xlsx --company-column nombre_empresa --id-column _id
"""
import argparse
import hashlib
import secrets
import string
from pathlib import Path

import pandas as pd


def make_code(seed: str, prefix: str = "EMP") -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest().upper()
    # Se mezcla hash estable + fragmento aleatorio para evitar códigos demasiado predecibles.
    alphabet = string.ascii_uppercase + string.digits
    random_part = "".join(secrets.choice(alphabet) for _ in range(4))
    return f"{prefix}-{digest[:4]}-{digest[4:8]}-{random_part}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--company-column", default="nombre_empresa")
    parser.add_argument("--id-column", default="_id")
    parser.add_argument("--code-column", default="codigo_acceso")
    parser.add_argument("--prefix", default="EMP")
    args = parser.parse_args()

    path = Path(args.input)
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path, dtype=object)
    else:
        df = pd.read_excel(path, dtype=object)

    if args.code_column not in df.columns:
        df[args.code_column] = ""

    for idx, row in df.iterrows():
        if pd.notna(row.get(args.code_column)) and str(row.get(args.code_column)).strip():
            continue
        company = str(row.get(args.company_column, "")).strip()
        internal_id = str(row.get(args.id_column, idx)).strip()
        df.at[idx, args.code_column] = make_code(f"{company}|{internal_id}", args.prefix)

    out = Path(args.output)
    if out.suffix.lower() == ".csv":
        df.to_csv(out, index=False)
    else:
        df.to_excel(out, index=False)
    print(f"Archivo generado: {out}")


if __name__ == "__main__":
    main()
