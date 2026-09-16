⚖️ Pipeline de Análisis de Sentencias del TJUE (Sin IA)Versión 1.
Este repositorio contiene un pipeline automatizado desarrollado en Python para procesar, clasificar y extraer información estructurada de las sentencias del Tribunal de Justicia de la Unión Europea (TJUE) sin necesidad de utilizar modelos de inteligencia artificial externos, apoyándose en análisis de texto basado en reglas y expresiones regulares.
---
🚀 Características Principales
Lectura y Limpieza Automática: Extrae el contenido de archivos PDF digitales en múltiples idiomas (español, inglés y francés).
Detección de Normativa y Artículos: Identifica automáticamente los artículos y cuerpos legales más relevantes citados en cada resolución jurídica.
Clasificación Temática por Palabras Clave: Categoriza los documentos según áreas clave del Derecho Comunitario:
Protección de Datos (GDPR / RGPD)
Inteligencia Artificial (AI Act)
Derecho de la Competencia (TFUE / Antitrust)
Mercados Digitales (DMA / DSA)
Ciberseguridad (NIS2 / DORA)
Semáforo de Vigencia Doctrinal: Clasifica el estado de validez jurídica de las normas citadas mediante alertas visuales:
🟢 Vigencia Absoluta: Normativa plenamente aplicable.
🟡 Vigencia Condicionada: Normas vigentes sujetas a revisiones o matices jurisprudenciales.
🔴 Doctrina Superada / Derogada: Normas o acuerdos invalidados (p. ej., Safe Harbor, Privacy Shield, Directiva 95/46/CE).
Exportación Multiformato: Genera informes interactivos en HTML y exporta conjuntos de datos en CSV y JSON.
---
📁 Estructura del Repositorio
```text
.
├── TRABAJO_STJUE_DEF.py     # Código fuente principal del pipeline
├── requirements.txt         # Dependencias de librerías de Python
├── .gitignore               # Filtro de archivos excluidos en Git
└── README.md                # Documentación del proyecto
```
---
🛠️ Instalación y Uso Local
Requisitos previos: Asegúrate de tener instalado Python en tu equipo.
Instalar dependencias:
```bash
   pip install -r requirements.txt
   ```
Ejecutar el pipeline:
```bash
   python TRABAJO_STJUE_DEF.py
   ```
Instrucciones de uso:
Al ejecutar el programa, se creará automáticamente la carpeta `sentencias_descargadas/`.
Usa la Opción 1 del menú interactivo para añadir nuevos archivos PDF o colócalos directamente dentro de dicha carpeta.
Utiliza la Opción 3 para procesar y analizar las sentencias. El reporte interactivo se abrirá automáticamente en tu navegador web.
