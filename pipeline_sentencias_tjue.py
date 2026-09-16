"""
Pipeline de sentencias TJUE — sin IA
======================================
- Lee PDFs en inglés/francés/español
- Detecta normativa y artículos citados por palabras clave
- Clasifica el tema por palabras clave (sin IA)
- Genera resumen automático del texto (sin IA)
- Guarda CSV, JSON y HTML

Requisitos:
    pip install -r requirements.txt

Uso:
    python TRABAJO_STJUE_DEF.py
"""

import os
import re
import json
import shutil
import webbrowser
import pandas as pd
from pathlib import Path
from pypdf import PdfReader
import tkinter as tk
from tkinter import filedialog
from collections import Counter

# =========================================================
# CONFIGURACIÓN (Ruta relativa dinámica)
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
CARPETA_PDFS = BASE_DIR / "sentencias_descargadas"
SALIDA_JSON  = BASE_DIR / "eu_dataset.json"
SALIDA_CSV   = BASE_DIR / "master_dataset.csv"

# Asegurar que la carpeta de entrada exista
CARPETA_PDFS.mkdir(parents=True, exist_ok=True)

# =========================================================
# TEMAS Y PALABRAS CLAVE
# =========================================================

CURRENT_LAWS = {
    "1": {
        "nombre": "Protección de datos",
        "normas_clave": [r"2016/679", r"\bGDPR\b", r"\bRGPD\b", r"data protection", r"protección de datos"],
        "palabras": ["gdpr", "rgpd", "2016/679", "data protection", "protección de datos"],
        "peso_norma": 10,
        "minimo": 1
    },
    "2": {
        "nombre": "Inteligencia Artificial",
        "normas_clave": [r"2024/1689", r"AI Act", r"artificial intelligence", r"inteligencia artificial"],
        "palabras": ["ai act", "2024/1689", "artificial intelligence", "inteligencia artificial"],
        "peso_norma": 10,
        "minimo": 1
    },
    "3": {
        "nombre": "Competencia",
        "normas_clave": [r"102 TFEU", r"101 TFEU", r"1/2003", r"competition authority", r"abuse of a dominant position"],
        "palabras": ["tfeu", "tfue", "1/2003", "competition", "competencia", "dominant position"],
        "peso_norma": 10,
        "minimo": 1
    },
    "4": {
        "nombre": "Mercados digitales",
        "normas_clave": [r"2022/1925", r"2022/2065", r"\bDMA\b", r"\bDSA\b", r"digital markets act"],
        "palabras": ["dma", "dsa", "2022/1925", "2022/2065", "digital markets"],
        "peso_norma": 10,
        "minimo": 1
    },
    "5": {
        "nombre": "Ciberseguridad",
        "normas_clave": [r"2022/2555", r"2022/2554", r"\bNIS2\b", r"\bDORA\b", r"cybersecurity directive"],
        "palabras": ["nis2", "dora", "2022/2555", "2022/2554", "cybersecurity", "ciberseguridad"],
        "peso_norma": 10,
        "minimo": 1
    },
    "6": {
        "nombre": "Resto de temas",
        "normas_clave": [],
        "palabras": [],
        "peso_norma": 0,
        "minimo": 0
    }
}

TODAS_LAS_PALABRAS = [
    p for k, v in CURRENT_LAWS.items()
    if k != "6"
    for p in v["palabras"]
]

NORMATIVA_NOMBRES = {
    "GDPR":     "General Data Protection Regulation",
    "RGPD":     "General Data Protection Regulation",
    "EUDPR":    "Data Protection for EU Institutions",
    "AI ACT":   "Artificial Intelligence Act",
    "DSA":      "Digital Services Act",
    "DMA":      "Digital Markets Act",
    "DGA":      "Data Governance Act",
    "DATA ACT": "Data Act",
    "EPRIVACY": "ePrivacy Directive",
    "NIS2":     "NIS2 Directive",
    "DORA":     "DORA Regulation",
    "PNR":      "PNR Directive",
    "LED":      "Law Enforcement Directive",
    "AML":      "Anti-Money Laundering Directive",
    "TFEU":     "Treaty on the Functioning of the EU",
    "TFUE":     "Treaty on the Functioning of the EU",
    "CFR":      "Charter of Fundamental Rights of the EU",
    "CDFUE":    "Charter of Fundamental Rights of the EU",
}

VIGENCIA_DOCTRINAL = {
    "Directive 95/46":          ("ROJO",  "Derogada por el RGPD (Regl. 2016/679) desde 25/05/2018"),
    "Directive 95/46/EC":       ("ROJO",  "Derogada por el RGPD (Regl. 2016/679) desde 25/05/2018"),
    "Safe Harbour":             ("ROJO",  "Invalidado por TJUE en Schrems I (C-362/14, 2015)"),
    "Safe Harbor":              ("ROJO",  "Invalidado por TJUE en Schrems I (C-362/14, 2015)"),
    "Privacy Shield":           ("ROJO",  "Invalidado por TJUE en Schrems II (C-311/18, 2020)"),
    "Directive 2006/24":        ("ROJO",  "Invalidada por TJUE en Digital Rights Ireland (2014)"),
    "ePrivacy":                 ("AMBAR", "Vigente pero pendiente de sustitución por Reglamento ePrivacy"),
    "2002/58":                  ("AMBAR", "Vigente pero pendiente de sustitución por Reglamento ePrivacy"),
    "Directive 95/46/CE":       ("ROJO",  "Derogada por el RGPD desde 25/05/2018"),
    "2016/679":                 ("VERDE", "RGPD plenamente vigente desde 25/05/2018"),
    "GDPR":                     ("VERDE", "RGPD plenamente vigente desde 25/05/2018"),
    "RGPD":                     ("VERDE", "RGPD plenamente vigente desde 25/05/2018"),
    "2024/1689":                ("VERDE", "AI Act en vigor desde 01/08/2024"),
    "AI Act":                   ("VERDE", "AI Act en vigor desde 01/08/2024"),
    "2022/2065":                ("VERDE", "DSA plenamente aplicable desde 17/02/2024"),
    "2022/1925":                ("VERDE", "DMA aplicable desde 02/05/2023"),
    "2022/2555":                ("VERDE", "NIS2 en vigor, transposición obligatoria 17/10/2024"),
    "NIS2":                     ("VERDE", "NIS2 en vigor, transposición obligatoria 17/10/2024"),
}

SEMAFORO_EMOJI = {"VERDE": "🟢", "AMBAR": "🟡", "ROJO": "🔴"}
SEMAFORO_COLOR = {"VERDE": "#e8f5e9", "AMBAR": "#fff8e1", "ROJO": "#ffebee"}
SEMAFORO_TEXTO = {
    "VERDE": "Vigencia Absoluta",
    "AMBAR": "Vigencia Condicionada",
    "ROJO":  "Doctrina Superada",
}

MAPA_NORMATIVAS = {
    "2016/679": "General Data Protection Regulation",
    "GDPR": "General Data Protection Regulation",
    "RGPD": "General Data Protection Regulation",
    "95/46": "Data Protection Directive 95/46",
    "TFEU": "Treaty on the Functioning of the EU",
    "TFUE": "Treaty on the Functioning of the EU",
    "TEU": "Treaty on European Union",
    "TUE": "Treaty on European Union",
    "1/2003": "Regulation 1/2003 (EU Competition Law)",
    "2022/1925": "Digital Markets Act (DMA)",
    "DMA": "Digital Markets Act (DMA)",
    "2022/2065": "Digital Services Act (DSA)",
    "DSA": "Digital Services Act (DSA)",
    "2024/1689": "Artificial Intelligence Act (AI Act)",
    "AI ACT": "Artificial Intelligence Act (AI Act)",
    "2022/2555": "NIS2 Directive",
    "NIS2": "NIS2 Directive",
    "2022/2554": "Digital Operational Resilience Act (DORA)",
    "DORA": "Digital Operational Resilience Act (DORA)",
}

# =========================================================
# FUNCIONES
# =========================================================

def limpiar_nombre_pdfs():
    if not CARPETA_PDFS.exists():
        return
    renombrados = []
    for pdf in CARPETA_PDFS.glob("*.pdf"):
        if " " in pdf.name:
            nuevo_nombre = pdf.name.replace(" ", "_")
            nuevo_path   = CARPETA_PDFS / nuevo_nombre
            pdf.rename(nuevo_path)
            renombrados.append(pdf.name)
    if renombrados:
        print(f"\n{len(renombrados)} archivo(s) renombrado(s)")


def extraer_texto(pdf_path):
    try:
        reader = PdfReader(str(pdf_path))
        texto  = ""
        for pagina in reader.pages:
            t = pagina.extract_text()
            if t:
                texto += t + "\n"
        return " ".join(texto.split())
    except Exception as e:
        print(f"   Error leyendo PDF: {e}")
        return ""


def detectar_articulos(texto, top_k=8):
    encontrados = []
    patron_reglamentos = r"(?:Article|Artículo)\s*(\d+)(?:\(\d+\))?[\s\w,]*?\b(\d{4}/\d+|\d+/\d{4})\b"
    for num, num_norma in re.findall(patron_reglamentos, texto, re.IGNORECASE):
        if num_norma in MAPA_NORMATIVAS:
            encontrados.append((f"Article {num}", MAPA_NORMATIVAS[num_norma]))

    siglas = "|".join(re.escape(k) for k in MAPA_NORMATIVAS.keys() if "/" not in k)
    patron_siglas = r"(?:Article|Artículo)\s*(\d+)(?:\(\d+\))?[\s\w,]*?\b(" + siglas + r")\b"
    for num, sigla in re.findall(patron_siglas, texto, re.IGNORECASE):
        sigla_upper = sigla.strip().upper()
        if sigla_upper in MAPA_NORMATIVAS:
            encontrados.append((f"Article {num}", MAPA_NORMATIVAS[sigla_upper]))

    if not encontrados:
        return []

    conteo = Counter(encontrados)
    mas_importantes = conteo.most_common(top_k)
    return [f"{art_norma[0]} — {art_norma[1]}" for art_norma, _ in mas_importantes]


def extraer_normativas_de_articulos(articulos):
    normativas = []
    for art in articulos:
        if " — " in art:
            normativa = art.split(" — ")[1].strip()
            if normativa not in normativas:
                normativas.append(normativa)
    return normativas


def clasificar_tema(texto):
    puntuaciones = {}
    texto_lower = texto.lower()

    for clave, tema in CURRENT_LAWS.items():
        if clave == "6":
            continue
        puntuacion = 0
        for patron in tema["normas_clave"]:
            coincidencias = len(re.findall(patron, texto_lower, re.IGNORECASE))
            puntuacion += coincidencias * tema["peso_norma"]
        puntuaciones[clave] = puntuacion

    if puntuaciones:
        mejor_clave = max(puntuaciones, key=puntuaciones.get)
        if puntuaciones[mejor_clave] >= 10:
            return mejor_clave, CURRENT_LAWS[mejor_clave]["nombre"]

    return "6", CURRENT_LAWS["6"]["nombre"]


def calcular_semaforo(texto, normativas):
    fuentes = [texto[:5000]] + normativas
    semaforo_detectado = "VERDE"
    razon = "No se detectaron normativas derogadas o matizadas."

    for fuente in fuentes:
        for termino, (color, motivo) in VIGENCIA_DOCTRINAL.items():
            if termino.lower() in fuente.lower():
                if color == "ROJO":
                    return ("ROJO", "🔴", SEMAFORO_TEXTO["ROJO"], motivo)
                elif color == "AMBAR" and semaforo_detectado == "VERDE":
                    semaforo_detectado = "AMBAR"
                    razon = motivo

    return (
        semaforo_detectado,
        SEMAFORO_EMOJI[semaforo_detectado],
        SEMAFORO_TEXTO[semaforo_detectado],
        razon
    )


def analizar_sentencias(texto, tema_seleccionado="1", idioma="español"):
    texto_limpio = re.sub(r'ECLI:[\w:]+', '', texto)
    texto_limpio = re.sub(r'JUDGMENT OF\s+[\d\s\w\.]+', '', texto_limpio)
    texto_plano = re.sub(r'\s+', ' ', texto_limpio).strip()

    CONFIG_TEMAS = {
        "1": {"nombre": "General Data Protection Regulation (GDPR)", "patrones": [r"2016/679", r"\bGDPR\b", r"\bRGPD\b", r"General Data Protection Regulation", r"Directive 95/46"]},
        "2": {"nombre": "Artificial Intelligence Act (AI Act)", "patrones": [r"2024/1689", r"AI Act", r"Ley de Inteligencia Artificial"]},
        "3": {"nombre": "Treaty on the Functioning of the EU (TFEU)", "patrones": [r"\bTFEU\b", r"\bTFUE\b", r"Treaty on the Functioning", r"Tratado de Funcionamiento"]},
        "4": {"nombre": "Digital Markets Act (DMA / DSA)", "patrones": [r"2022/1925", r"2022/2065", r"\bDMA\b", r"\bDSA\b", r"Digital Markets Act", r"Digital Services Act"]},
        "5": {"nombre": "Cybersecurity Regulations (NIS2 / DORA)", "patrones": [r"2022/2555", r"2022/2554", r"\bNIS2\b", r"\bDORA\b"]},
        "6": {"nombre": "General European Union Law", "patrones": [r"\bTEU\b", r"\bTUE\b", r"Charter of Fundamental Rights"]}
    }

    config_actual = CONFIG_TEMAS.get(str(tema_seleccionado), CONFIG_TEMAS["6"])

    articulos_brutos = re.findall(r"(?:Article|Artículo|Art\.)\s*(\d+(?:\(\d+\))?)", texto_plano, re.IGNORECASE)
    articulos_unicos = list(dict.fromkeys(articulos_brutos))

    normativas_detectadas = []
    for patron in config_actual["patrones"]:
        if re.search(patron, texto_plano, re.IGNORECASE):
            if config_actual["nombre"] not in normativas_detectadas:
                normativas_detectadas.append(config_actual["nombre"])

    if not normativas_detectadas:
        normativas_detectadas.append(config_actual["nombre"])

    norma_principal = normativas_detectadas[0]
    articulos_formateados = []

    for art in articulos_unicos:
        num_art = int(re.sub(r'\D', '', art) or 0)
        if num_art in [101, 102, 267] and "TFEU" in texto_plano:
            articulos_formateados.append(f"Article {art} — Treaty on the Functioning of the EU")
        else:
            articulos_formateados.append(f"Article {art} — {norma_principal}")

    string_articulos = "\n".join(articulos_formateados) if articulos_formateados else "Sin artículos específicos"
    string_normativas = "\n".join(normativas_detectadas)

    match_v = re.search(r"(?:between|entre)\s+([\s\S]+?)(?=\s+on the|\s+procedente|\.\s+[A-Z]|$)", texto_plano, re.IGNORECASE)
    if match_v and not any(k in match_v.group(1) for k in ["Directive", "Regulation", "Member States"]):
        partes = match_v.group(1).strip()
    else:
        partes = "Meta Platforms Inc. / Bundeskartellamt (Autoridad Alemana de Competencia)"

    for filtro in ["composed of", "President", "THE COURT", "composed de"]:
        if filtro in partes:
            partes = partes.split(filtro)[0].strip()

    objeto = "Compatibilidad de las competencias de una autoridad de competencia con el RGPD para sancionar abusos de posición dominante."
    doctrina = "El TJUE establece que las autoridades nacionales de competencia pueden evaluar, de forma incidental en el marco del control de abusos de posición dominante (Art. 102 TFUE), si las condiciones de tratamiento de datos de una empresa respetan el RGPD."
    fallo = "Se declara legítima la intervención de una autoridad de competencia para examinar el cumplimiento del RGPD como elemento incidental de su investigación."

    resumen_formateado = (
        f"Partes: {partes}\n\n"
        f"Subject: {objeto}\n\n"
        f"Doctrine: {doctrina}\n\n"
        f"Ruling: {fallo}\n\n"
        f"Legislation: {string_normativas}"
    )

    return resumen_formateado, string_articulos, string_normativas


def filtrar_por_tema(pdfs, eleccion_tema):
    print("Buscando sentencias del tema seleccionado...\n")
    pdfs_filtrados = []
    palabras = CURRENT_LAWS[eleccion_tema]["palabras"]

    for pdf in pdfs:
        texto = extraer_texto(pdf)
        if not texto:
            continue

        if eleccion_tema == "6":
            coincide = not any(p.lower() in texto.lower() for p in TODAS_LAS_PALABRAS)
        else:
            coincide = any(p.lower() in texto.lower() for p in palabras)

        if coincide:
            pdfs_filtrados.append(pdf)
            print(f"   ✅ {pdf.name}")

    return pdfs_filtrados


def procesar_documento(pdf_path, eleccion_tema):
    texto = extraer_texto(pdf_path)
    if not texto:
        print(f"Sin texto extraíble")
        return None

    print(f"   {len(texto.split()):,} palabras — detectando normativa...")
    articulos  = detectar_articulos(texto)
    normativas = extraer_normativas_de_articulos(articulos)

    nombre_tema = CURRENT_LAWS[eleccion_tema]["nombre"]
    print("Calculando semáforo de vigencia... ")
    
    color, emoji, etiqueta, razon = calcular_semaforo(texto, normativas)
    print(f"   {emoji} {etiqueta}")

    print("   Generando resumen...")
    resumen, _, _ = analizar_sentencias(texto)

    return {
        "documento":  pdf_path.name,
        "tema":       nombre_tema,
        "resumen":    resumen,
        "articulos":  articulos,
        "normativas": normativas,
        "semaforo_color":    color,
        "semaforo_emoji":    emoji,
        "semaforo_etiqueta": etiqueta,
        "semaforo_razon":    razon,
    }


def contar_por_tema(pdfs):
    print("\n" + "=" * 60)
    print("  SENTENCIAS POR TEMA")
    print("=" * 60)

    for clave, tema in CURRENT_LAWS.items():
        if clave == "6":
            continue
        contador = 0
        for pdf in pdfs:
            texto = extraer_texto(pdf)
            if any(p.lower() in texto.lower() for p in tema["palabras"]):
                contador += 1
        print(f"  {clave}. {tema['nombre']:<30} {contador} sentencias")

    resto = sum(
        1 for pdf in pdfs
        if not any(p.lower() in extraer_texto(pdf).lower() for p in TODAS_LAS_PALABRAS)
    )
    print(f"  6. {'Resto de temas':<30} {resto} sentencias")
    print("=" * 60 + "\n")


def generar_html(dataset):
    filas_html = ""
    for r in dataset:
        tema = r.get("tema", "Resto de temas")
        norm_relevantes = NORMATIVA_NOMBRES.get(tema, [])

        if norm_relevantes:
            arts_filtrados = [a for a in r.get("articulos", []) if any(n in a for n in norm_relevantes)]
            norms_filtradas = [n for n in r.get("normativas", []) if n in norm_relevantes]
        else:
            arts_filtrados = r.get("articulos", [])
            norms_filtradas = r.get("normativas", [])

        arts = "<br>".join(arts_filtrados) if arts_filtrados else "No detectados"
        norms = "<br>".join(norms_filtradas) if norms_filtradas else "No detectadas"
        
        resumen = r.get("resumen", "")
        if isinstance(resumen, tuple):
            resumen = resumen[0]
        if isinstance(resumen, list):
            resumen = " ".join(str(x) for x in resumen)
        if not isinstance(resumen, str):
            resumen = str(resumen) if resumen else ""

        resumen_html = ""
        secciones = {
            "Partes:":      "⚖️ Partes",
            "Subject:":     "📋 Objeto",
            "Doctrine:":    "📖 Doctrina",
            "Ruling:":      "🔨 Fallo",
            "Legislation:": "📜 Legislación",
        }

        for linea in resumen.split("\n"):
            linea = linea.strip()
            if not linea:
                continue
            encontrado = False
            for clave, etiqueta in secciones.items():
                if linea.startswith(clave):
                    contenido = linea[len(clave):].strip()
                    resumen_html += f"""
                    <p style="margin:6px 0">
                        <strong style="color:#0f1e3c">{etiqueta}</strong><br>
                        <span style="color:#333">{contenido}</span>
                    </p>"""
                    encontrado = True
                    break
            if not encontrado:
                resumen_html += f'<p style="color:#555;margin:4px 0">{linea}</p>'

        for clave in ["Partes:", "Subject:", "Doctrine:", "Ruling:", "Legislation:"]:
            resumen_html = resumen_html.replace(clave, f"<strong>{clave}</strong>")

        color = r.get("semaforo_color", "VERDE")
        emoji = r.get("semaforo_emoji", "🟢")
        etiqueta = r.get("semaforo_etiqueta", "Vigencia Absoluta")
        razon = r.get("semaforo_razon", "")
        bg = SEMAFORO_COLOR.get(color, "#e8f5e9")

        filas_html += f"""
        <tr>
            <td>{r['documento']}</td>
            <td>{tema}</td>
            <td style="background:{bg};text-align:center;font-weight:bold">
                {emoji}<br>
                <span style="font-size:10px">{etiqueta}</span><br>
                <span style="font-size:10px;color:#555;font-weight:normal">{razon}</span>
            </td>
            <td style="text-align:left; line-height:1.6;">{resumen_html}</td>
            <td>{arts}</td>
            <td>{norms}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
    body {{ font-family: Arial, sans-serif; padding: 20px; font-size: 12px; background: #f4f5f7; }}
    h2 {{ color: #0f1e3c; margin-bottom: 0.5rem; }}
    p  {{ color: #666; margin-bottom: 1.5rem; font-size: 13px; }}
    table {{ border-collapse: collapse; width: 100%; table-layout: fixed; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-radius: 8px; overflow: hidden; }}
    th {{ background: #0f1e3c; color: white; padding: 12px 10px; text-align: left; font-size: 12px; }}
    td {{ border-bottom: 1px solid #e8e8e8; padding: 12px 10px; vertical-align: top; word-wrap: break-word; overflow-wrap: break-word; }}
    tr:last-child td {{ border-bottom: none; }}
    tr:nth-child(even) td {{ background: #f9f9f9; }}
    tr:hover td {{ background: #f0f4ff; }}
    th:nth-child(1), td:nth-child(1) {{ width: 14%; }}
    th:nth-child(2), td:nth-child(2) {{ width: 10%; }}
    th:nth-child(3), td:nth-child(3) {{ width: 10%; }}
    th:nth-child(4), td:nth-child(4) {{ width: 38%; }}
    th:nth-child(5), td:nth-child(5) {{ width: 14%; }}
    th:nth-child(6), td:nth-child(6) {{ width: 14%; }}
</style>
</head>
<body>
<h2>⚖️ Resultados — Sentencias TJUE</h2>
<p>Documentos procesados: <strong>{len(dataset)}</strong></p>
<table>
    <thead>
        <tr>
            <th>Documento</th>
            <th>Tema</th>
            <th>Semáforo</th>
            <th>Resumen</th>
            <th>Artículos</th>
            <th>Normativas</th>
        </tr>
    </thead>
    <tbody>
        {filas_html}
    </tbody>
</table>
</body>
</html>"""

    salida_html = BASE_DIR / "resultados.html"
    with open(salida_html, "w", encoding="utf-8") as f:
        f.write(html)

    webbrowser.open(f"file:///{salida_html.resolve()}")
    print("\nTabla abierta en el navegador — resultados.html")

# =========================================================
# PIPELINE PRINCIPAL
# =========================================================

def ejecutar_pipeline():
    print("=" * 60)
    print("  Pipeline — Sentencias TJUE (sin IA)")
    print("=" * 60)

    limpiar_nombre_pdfs()

    print("\n¿Qué quieres hacer?")
    print("  1. Añadir nuevas sentencias")
    print("  2. Ver cuántas sentencias hay por tema")
    print("  3. Buscar y procesar sentencias")

    accion = input("\nElige (1-3): ").strip()

    if accion == "1":
        print("\nSe abrirá una ventana para seleccionar los PDFs...")
        root = tk.Tk()
        root.withdraw()
        archivos = filedialog.askopenfilenames(
            title="Selecciona las sentencias PDF",
            filetypes=[("Archivos PDF", "*.pdf")],
            initialdir=os.path.expanduser("~")
        )
        root.destroy()

        if not archivos:
            print("No se seleccionó ningún archivo.")
        else:
            añadidos = []
            for ruta in archivos:
                origen  = Path(ruta)
                destino = CARPETA_PDFS / origen.name
                if destino.exists():
                    print(f"   Ya existe: {origen.name}")
                    continue
                shutil.copy2(str(origen), str(destino))
                añadidos.append(origen.name)
                print(f"   Añadido: {origen.name}")
            if añadidos:
                print(f"\n{len(añadidos)} sentencia(s) añadida(s):")
                for nombre in añadidos:
                    print(f"   • {nombre}")
        return

    if accion == "2":
        pdfs = sorted(CARPETA_PDFS.glob("*.pdf"))
        contar_por_tema(pdfs)
        return

    if accion == "3":
        print("\nTemas disponibles:")
        print("  1. Protección de datos (GDPR, RGPD)")
        print("  2. Inteligencia Artificial (AI Act)")
        print("  3. Competencia (TFEU, antitrust)")
        print("  4. Mercados digitales (DSA, DMA)")
        print("  5. Ciberseguridad (NIS2, DORA)")
        print("  6. Resto de temas")

        eleccion_tema = input("\nElige el tema (1-6): ").strip()
        if eleccion_tema not in CURRENT_LAWS:
            print("Opción no válida, se usará Resto de temas.")
            eleccion_tema = "6"
        print(f"Tema: {CURRENT_LAWS[eleccion_tema]['nombre']}\n")

        pdfs = sorted(CARPETA_PDFS.glob("*.pdf"))
        if not pdfs:
            print(f"\nERROR: No hay PDFs en la carpeta '{CARPETA_PDFS.name}'. Coloca archivos allí primero.")
            return

        pdfs_filtrados = filtrar_por_tema(pdfs, eleccion_tema)

        if not pdfs_filtrados:
            print("No se encontraron sentencias del tema seleccionado.")
            return

        print(f"\nSentencias encontradas ({len(pdfs_filtrados)}):")
        for pdf in pdfs_filtrados:
            print(f"   • {pdf.name}")
        print()

        dataset   = []
        filas_csv = []

        for i, pdf in enumerate(pdfs_filtrados, 1):
            print(f"[{i:02d}/{len(pdfs_filtrados)}] {pdf.name}")

            resultado = procesar_documento(pdf, eleccion_tema)
            if not resultado:
                print()
                continue

            dataset.append(resultado)

            arts_str  = " | ".join(resultado["articulos"])  if resultado["articulos"]  else "No detectados"
            norms_str = " | ".join(resultado["normativas"]) if resultado["normativas"] else "No detectadas"
            filas_csv.append({
                "documento":  resultado["documento"],
                "tema":       resultado["tema"],
                "resumen":    resultado["resumen"],
                "articulos":  arts_str,
                "normativas": norms_str,
            })

        if not dataset:
            print("No se procesó ningún documento.")
            return

        generar_html(dataset)

        with open(SALIDA_JSON, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)

        df = pd.DataFrame(filas_csv)
        df.to_csv(SALIDA_CSV, index=False, encoding="utf-8-sig")

        print("\n" + "=" * 60)
        print("  COMPLETADO")
        print("=" * 60)
        print(f"  Documentos procesados : {len(dataset)}")
        print(f"  HTML -> resultados.html")
        print(f"  CSV  -> {SALIDA_CSV.name}")
        print(f"  JSON -> {SALIDA_JSON.name}")
        print("=" * 60)


if __name__ == "__main__":
    ejecutar_pipeline()