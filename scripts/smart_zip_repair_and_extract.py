#!/usr/bin/env python3
"""
Universal Binary Signature Extractor for 4.42 GB OneDrive Package.
Extracts all valid documents (Word, Excel, PDF, Visio, CAD, Zip) directly into cataloged OT folders.
"""

import struct
import zlib
import re
import sys
from pathlib import Path

def universal_extract():
    zip_path = Path("onedrive_4.zip")
    extract_dir = Path("ot_8000_smart_extracted")
    extract_dir.mkdir(exist_ok=True)

    print("==========================================================================")
    print("🛠️ EXTRACCIÓN Y CATALÓGICA UNIVERSAL DE DOCUMENTOS (4.42 GB)")
    print("==========================================================================")

    file_size = zip_path.stat().st_size
    extracted_count = 0
    doc_counter = 0

    with open(zip_path, "rb") as f:
        pos = 0
        while pos < file_size - 30:
            f.seek(pos)
            sig = f.read(4)
            if sig == b"PK\x03\x04":
                header_offset = pos
                header_data = f.read(26)
                if len(header_data) < 26:
                    break

                ver, flag, comp_method, mod_time, mod_date, crc32, comp_size, uncomp_size, fname_len, extra_len = struct.unpack(
                    "<HHHHHIIIHH", header_data
                )

                filename_bytes = f.read(fname_len)
                extra_bytes = f.read(extra_len)

                try:
                    filename = filename_bytes.decode("utf-8", errors="ignore")
                except Exception:
                    filename = filename_bytes.decode("latin1", errors="ignore")

                filename = filename.replace("\x00", "").strip()

                if filename and comp_size > 0 and comp_size < 500_000_000:
                    clean_filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
                    
                    # If this is an inner DOCX/XLSX component, group into parent document container
                    if any(clean_filename.startswith(prefix) for prefix in ["word/", "xl/", "customXml/", "docProps/", "ppt/", "visio/"]):
                        if clean_filename in ["word/document.xml", "xl/workbook.xml", "docProps/core.xml"]:
                            doc_counter += 1
                        out_path = extract_dir / f"document_package_{doc_counter:04d}" / clean_filename
                    else:
                        out_path = extract_dir / clean_filename

                    try:
                        out_path.parent.mkdir(parents=True, exist_ok=True)
                        comp_data = f.read(comp_size)

                        if comp_method == 0:  # Stored
                            with open(out_path, "wb") as out_f:
                                out_f.write(comp_data)
                            extracted_count += 1
                        elif comp_method == 8:  # Deflate
                            try:
                                decomp = zlib.decompress(comp_data, -15)
                                with open(out_path, "wb") as out_f:
                                    out_f.write(decomp)
                                extracted_count += 1
                            except Exception:
                                try:
                                    decomp = zlib.decompress(comp_data)
                                    with open(out_path, "wb") as out_f:
                                        out_f.write(decomp)
                                    extracted_count += 1
                                except Exception:
                                    pass

                        if extracted_count > 0 and extracted_count % 200 == 0:
                            print(f"  • Extraídos {extracted_count:,} archivos/componentes: '{clean_filename[:60]}'")

                        pos = header_offset + 30 + fname_len + extra_len + comp_size
                        continue

                    except Exception:
                        pos += 1
                        continue

                pos += 1
            else:
                pos += 1

    print(f"\n==========================================================================")
    print(f"🎉 EXTRACCIÓN Y REPARACIÓN COMPLETADA:")
    print(f"• Total Paquetes de Documentos Extraídos: {doc_counter:,}")
    print(f"• Total Archivos/Componentes Recuperados: {extracted_count:,}")
    print(f"• Ubicación: '{extract_dir.resolve()}'")
    print(f"==========================================================================")

if __name__ == "__main__":
    universal_extract()
