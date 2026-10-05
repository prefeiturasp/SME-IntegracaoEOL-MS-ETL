"""Sphinx configuration."""

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

project = "SME-INTEGRACAOEOL-MS-ETL"
author = "Equipe SME"
release = "1.0.0"

language = "pt"

extensions = [
    "myst_parser",
    "sphinx.ext.graphviz",
    "sphinx.ext.autosectionlabel",
]

autosectionlabel_prefix_document = True

myst_enable_extensions = [
    "colon_fence",
    "deflist",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


html_theme = "alabaster"
html_title = "SME-INTEGRACAOEOL-MS-ETL"
html_short_title = "ETL Docs"


graphviz_output_format = "png"


latex_engine = "xelatex"

latex_documents = [
    (
        "index",
        "sme-integracaoeol-ms-etl.tex",
        "SME-INTEGRACAOEOL-MS-ETL",
        "Equipe SME",
        "manual",
    ),
]

latex_elements = {
    "babel": "",
    "preamble": r"""
\usepackage{polyglossia}
\setmainlanguage{portuguese}

\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage{setspace}
\usepackage{float}

\pagestyle{fancy}

\fancyhead[L]{SME-INTEGRACAOEOL-MS-ETL}
\fancyhead[R]{\leftmark}
\fancyfoot[C]{\thepage}

\setlength{\headheight}{15pt}

\onehalfspacing

\usepackage{listings}
\lstset{
    breaklines=true,
    basicstyle=\ttfamily\small
}
""",
    "fontpkg": r"""
\setmainfont{DejaVu Serif}
\setsansfont{DejaVu Sans}
\setmonofont{DejaVu Sans Mono}
""",
    "maketitle": r"""
\begin{titlepage}
    \centering
    \vspace*{3cm}

    {\Huge\bfseries SME-INTEGRACAOEOL-MS-ETL \par}
    \vspace{1cm}

    {\Large Documentação Técnica \par}
    \vspace{2cm}

    {\large Equipe SME \par}
    \vspace{0.5cm}

    {\large \today \par}

    \vfill
\end{titlepage}
""",
    "figure_align": "H",
    "tableofcontents": r"""
\tableofcontents
\clearpage
""",
}
