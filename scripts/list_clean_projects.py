#!/usr/bin/env python3
"""
Direct 1-to-1 Project Folder Scanner.
Scans root subdirectories inside 2025 folder directly to eliminate double-counting of file revisions.
"""

import os
import sqlite3
import pandas as pd
from pathlib import Path

def list_clean_projects():
    base_2025 = Path("2025")
    
    # Locate inner 2025 if nested
    if (base_2025 / "2025").exists():
        target_dir = base_2025 / "2025"
    else:
        target_dir = base_2025

    print("==========================================================================")
    print("📂 CARPETAS ÚNICAS DE PROYECTOS IDENTIFICADAS EN 2025 (SIN DUPLICADOS)")
    print("==========================================================================")
    
    subdirs = sorted([d for d in target_dir.iterdir() if d.is_dir()])
    print(f"• Total Carpetas Principales de Proyectos 2025: {len(subdirs)}\n")

    projects_list = []

    for idx, d in enumerate(subdirs, 1):
        name = d.name
        client = "Otros"
        p_lower = name.lower()
        if "transelec" in p_lower: client = "Transelec"
        elif "chilquinta" in p_lower: client = "Chilquinta"
        elif "aes" in p_lower: client = "AES Andes"
        elif "colbun" in p_lower: client = "Colbún"
        elif "saesa" in p_lower: client = "SAESA"
        elif "cge" in p_lower: client = "CGE"
        elif "enel" in p_lower: client = "Enel"

        projects_list.append({"index": idx, "folder_name": name, "client": client})
        print(f" {idx:2d}. [{client:<10}] {name}")

    print("\n==========================================================================")

if __name__ == "__main__":
    list_clean_projects()
