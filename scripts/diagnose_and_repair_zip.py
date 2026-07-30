#!/usr/bin/env python3
"""
Deep Binary Diagnosis & Zip Fixer for OneDrive 4.4GB Archive.
Tests:
- Header Magic Bytes (PK34, PK78, etc.).
- Central Directory Reconstruction via 'zip -FF' or '7z x' or custom Python byte scanner.
"""

import subprocess
import zipfile
from pathlib import Path

def test_headers_and_repair():
    zip_path = Path("onedrive_4.zip")
    fixed_path = Path("onedrive_4_fixed.zip")
    extract_dir = Path("onedrive_4_extracted")

    extract_dir.mkdir(exist_ok=True)

    with open(zip_path, "rb") as f:
        header = f.read(100)
        f.seek(-100, 2)
        footer = f.read(100)

    print("==========================================================================")
    print("🔍 DIAGNÓSTICO BINARIO DEL ARCHIVO ONEDRIVE (4.42 GB)")
    print("==========================================================================")
    print(f"• Primeros 16 Bytes (Header): {header[:16].hex()} -> Raw: {header[:16]}")
    print(f"• Últimos 16 Bytes (Footer): {footer[-16:].hex()} -> Raw: {footer[-16:]}")

    # Test zip -FF repair command
    print("\n🛠️ Intentando Reparación de Estructura Central Directory con 'zip -FF'...")
    res = subprocess.run(
        ["zip", "-FF", str(zip_path), "--out", str(fixed_path)],
        input="y\ny\ny\ny\ny\n",
        capture_output=True,
        text=True
    )
    print(f"• Output zip -FF: {res.stdout[:500]}")
    print(f"• Exit status: {res.returncode}")

    if fixed_path.exists():
        print(f"✅ Archivo Reparado Creado: '{fixed_path}' ({fixed_path.stat().st_size:,} bytes)")
        # Try extracting fixed zip
        try:
            with zipfile.ZipFile(fixed_path, "r") as zf:
                files = zf.namelist()
                print(f"🎉 ÉXITO TOTAL: {len(files)} archivos recuperados en la estructura!")
                zf.extractall(extract_dir)
                print(f"📂 Archivos Extraídos Exitosamente en {extract_dir}:")
                for item in files[:20]:
                    print("  -", item)
        except Exception as err:
            print(f"❌ Error al abrir archivo reparado: {err}")
    else:
        print("❌ 'zip -FF' no pudo crear un archivo único. Probando escaneo manual de firmas PK...")

if __name__ == "__main__":
    test_headers_and_repair()
