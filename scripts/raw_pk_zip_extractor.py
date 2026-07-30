#!/usr/bin/env python3
"""
Low-Level Binary Signature Stream Extractor (PK\x03\x04 Scanner).
Extracts all files and folders from damaged/truncated OneDrive ZIP archives
by directly parsing Local File Headers (PK\x03\x04) without requiring EOCDR footer.
"""

import struct
import zlib
from pathlib import Path

def extract_raw_pk_stream():
    zip_path = Path("onedrive_4.zip")
    extract_dir = Path("ot_8000_extracted")
    extract_dir.mkdir(exist_ok=True)

    print("==========================================================================")
    print("🛠️ EXTRACTOR BINARIO DE BAJO NIVEL PK\\x03\\x04 (SERIE OT 8000)")
    print("==========================================================================")

    extracted_count = 0
    skipped_count = 0

    with open(zip_path, "rb") as f:
        file_size = zip_path.stat().st_size
        print(f"• Analizando flujo binario de {file_size:,} bytes...")
        
        pos = 0
        while pos < file_size - 30:
            f.seek(pos)
            sig = f.read(4)
            if sig == b"PK\x03\x04":
                # Local File Header structure:
                # 0..4: signature (4)
                # 4..6: version needed (2)
                # 6..8: general flag (2)
                # 8..10: compression method (2) -> 0=stored, 8=deflate
                # 10..14: last mod time/date (4)
                # 14..18: crc32 (4)
                # 18..22: compressed size (4)
                # 22..26: uncompressed size (4)
                # 26..28: filename length (2)
                # 28..30: extra field length (2)
                header_data = f.read(26)
                if len(header_data) < 26:
                    break

                ver, flag, comp_method, mod_time, mod_date, crc32, comp_size, uncomp_size, fname_len, extra_len = struct.unpack(
                    "<HHHHHIIIHH", header_data
                )

                filename_bytes = f.read(fname_len)
                extra_bytes = f.read(extra_len)

                try:
                    filename = filename_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    try:
                        filename = filename_bytes.decode("cp437")
                    except UnicodeDecodeError:
                        filename = filename_bytes.decode("latin1", errors="ignore")

                filename = filename.strip("\x00")

                if comp_size > 0 and comp_size < 500_000_000 and not filename.endswith("/"):
                    data_offset = f.tell()
                    comp_data = f.read(comp_size)

                    out_path = extract_dir / filename
                    out_path.parent.mkdir(parents=True, exist_ok=True)

                    extracted_success = False
                    if comp_method == 0:  # Stored
                        try:
                            with open(out_path, "wb") as out_f:
                                out_f.write(comp_data)
                            extracted_success = True
                        except Exception:
                            pass
                    elif comp_method == 8:  # Deflate
                        try:
                            decomp_data = zlib.decompress(comp_data, -15)
                            with open(out_path, "wb") as out_f:
                                out_f.write(decomp_data)
                            extracted_success = True
                        except Exception:
                            try:
                                decomp_data = zlib.decompress(comp_data)
                                with open(out_path, "wb") as out_f:
                                    out_f.write(decomp_data)
                                extracted_success = True
                            except Exception:
                                pass

                    if extracted_success:
                        extracted_count += 1
                        if extracted_count % 100 == 0:
                            print(f"  • Extraídos {extracted_count} archivos: '{filename[:60]}'")
                    else:
                        skipped_count += 1
                        pos += 1
                        continue

                    pos = data_offset + comp_size
                else:
                    pos += 4 + 26 + fname_len + extra_len
            else:
                pos += 1

    print(f"\n==========================================================================")
    print(f"🎉 EXTRACCIÓN Y REPARACIÓN COMPLETADA:")
    print(f"• Archivos Recuperados Exitosamente: {extracted_count}")
    print(f"• Carpeta de Destino: '{extract_dir.resolve()}'")
    print(f"==========================================================================")

if __name__ == "__main__":
    extract_raw_pk_stream()
