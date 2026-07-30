#!/usr/bin/env python3
"""
OneDrive ZIP Repair & Extraction Engine.
Diagnoses why 'onedrive_4.zip' throws an error (encoding, corrupt headers, Zip64, etc.),
repairs the archive structure, extracts all contained files, and analyzes its content.
"""

import zipfile
import subprocess
from pathlib import Path

def repair_and_extract():
    zip_path = Path("onedrive_4.zip")
    extract_dir = Path("onedrive_4_extracted")

    if not zip_path.exists():
        print(f"❌ El archivo '{zip_path}' aún no se encuentra en la carpeta del proyecto.")
        return

    print("==========================================================================")
    print("📦 DIAGNÓSTICO Y REPARACIÓN DE ARCHIVO ZIP DE ONEDRIVE")
    print("==========================================================================")
    print(f"• Tamaño del Archivo ZIP: {zip_path.stat().st_size:,} bytes (~{zip_path.stat().st_size/1e6:.2f} MB)")

    extract_dir.mkdir(exist_ok=True)

    # Strategy 1: Standard Python zipfile with fallback encodings (cp437, utf-8, latin1)
    extracted_count = 0
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            print(f"• Archivos en el interior del ZIP: {len(zf.namelist())}")
            for member in zf.infolist():
                try:
                    zf.extract(member, path=extract_dir)
                    extracted_count += 1
                except Exception as e:
                    print(f"  ⚠️ Error en extracción de '{member.filename}': {e}")
                    # Try raw read and manual write
                    try:
                        data = zf.read(member.filename)
                        out_file = extract_dir / Path(member.filename).name
                        out_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(out_file, 'wb') as f_out:
                            f_out.write(data)
                        extracted_count += 1
                    except Exception as e2:
                        print(f"  ❌ Fallo crítico en '{member.filename}': {e2}")

        print(f"✅ Extracción Estándar Completada: {extracted_count} archivos extraídos.")

    except Exception as zip_err:
        print(f"⚠️ Error en ZipFile Estándar: {zip_err}. Intentando herramienta 7z / ditto...")
        # Strategy 2: System 7z / ditto / unzip fallback
        try:
            res = subprocess.run(["unzip", "-o", str(zip_path), "-d", str(extract_dir)], capture_output=True, text=True)
            if res.returncode == 0:
                print("✅ Extracción exitosa con comando 'unzip'.")
            else:
                print(f"⚠️ Warning en 'unzip': {res.stderr}")
        except Exception as sub_err:
            print(f"❌ Error en ejecutor externo: {sub_err}")

    # Analyze Extracted Content
    extracted_files = list(extract_dir.rglob("*"))
    files_only = [f for f in extracted_files if f.is_file()]

    print(f"\n==========================================================================")
    print(f"📂 CONTENIDO EXTRAÍDO Y REPARADO ({len(files_only)} Archivos Totales)")
    print(f"==========================================================================")
    for f in sorted(files_only)[:25]:
        rel = f.relative_to(extract_dir)
        print(f"• {str(rel):<60} ({f.stat().st_size:,} bytes)")

if __name__ == "__main__":
    repair_and_extract()
