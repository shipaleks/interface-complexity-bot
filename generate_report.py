#!/usr/bin/env python3
import os
import json
import logging
import argparse
import tempfile
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def load_data(gpt_data_path):
    """Load GPT analysis data from JSON file"""
    logger.info(f"Loading GPT analysis data from: {gpt_data_path}")
    try:
        with open(gpt_data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info("GPT analysis data loaded successfully")
        return data
    except Exception as e:
        logger.error(f"Failed to load GPT analysis data: {e}")
        raise

def load_gemini_data(gemini_data_path):
    """Load Gemini coordinates data from JSON file"""
    if not gemini_data_path or not os.path.exists(gemini_data_path):
        logger.warning("No Gemini data provided or file doesn't exist")
        return None
    
    logger.info(f"Loading Gemini coordinates data from: {gemini_data_path}")
    try:
        with open(gemini_data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Gemini data loaded successfully with {len(data.get('coordinates', []))} elements")
        return data
    except Exception as e:
        logger.error(f"Failed to load Gemini data: {e}")
        return None

def generate_latex_header():
    """Generate LaTeX document header"""
    return r"""\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage{amssymb}
\usepackage{graphicx}
\usepackage{xcolor}
\usepackage{colortbl}
\usepackage{booktabs}
\usepackage{enumitem}
\usepackage{titlesec}
\usepackage{titling}
\usepackage{geometry}
\usepackage{hyperref}
\usepackage{tabularray}
\usepackage{float}
\usepackage{multirow}

% Set page geometry
\geometry{margin=2.5cm}

% Define colors
\definecolor{severity-critical}{RGB}{220, 20, 60}
\definecolor{severity-high}{RGB}{255, 127, 80}
\definecolor{severity-medium}{RGB}{255, 191, 0}
\definecolor{severity-low}{RGB}{46, 139, 87}

% Define custom section formatting
\titleformat{\section}
  {\large\bfseries\color{black}}
  {\thesection.}{0.5em}{}
\titleformat{\subsection}
  {\normalsize\bfseries\color{black}}
  {\thesubsection.}{0.5em}{}

% Define header and title
\title{\textbf{UI Complexity Analysis Report}}
\author{Interface Complexity Analyzer}
\date{\today}

\begin{document}

\maketitle
\thispagestyle{empty}
\vspace{-1.5cm}

% Table of contents
\tableofcontents
\newpage
"""

def generate_introduction(data):
    """Generate introduction section"""
    score = data.get("overallScore", {}).get("score", 0)
    
    level = "Низкая"
    if score >= 80:
        level = "Критическая"
    elif score >= 60:
        level = "Высокая"
    elif score >= 40:
        level = "Средняя"
    
    intro = r"""
\section{Введение}

Этот отчет содержит анализ пользовательского интерфейса на предмет его визуальной сложности и
потенциальных проблем юзабилити. Анализ выполнен с помощью алгоритмов компьютерного зрения и
моделей искусственного интеллекта.

\subsection{Методология анализа}

Анализ основан на следующих принципах:

\begin{itemize}
  \item Оценка визуальной организации и структуры интерфейса
  \item Анализ контрастности и цветового оформления
  \item Оценка типографики и читабельности текста
  \item Анализ информационной плотности и когнитивной нагрузки
  \item Выявление потенциальных проблем для взаимодействия пользователя с интерфейсом
\end{itemize}

"""
    
    date_str = datetime.now().strftime("%d.%m.%Y")
    
    intro += f"""
\\subsection{{Общая оценка сложности}}

\\begin{{itemize}}
  \\item \\textbf{{Дата анализа:}} {date_str}
  \\item \\textbf{{Общая оценка сложности:}} {score}/100 (\\textcolor{{{get_severity_color(score)}}}{{\\textbf{{{level}}}}})
\\end{{itemize}}

"""
    return intro

def get_severity_color(score):
    """Get color based on severity/score"""
    if score >= 80:
        return "severity-critical"
    elif score >= 60:
        return "severity-high"
    elif score >= 40:
        return "severity-medium"
    else:
        return "severity-low"

def generate_key_findings(data):
    """Generate key findings section"""
    all_problems = []
    categories = data.get("categories", [])
    
    for category in categories:
        category_name = category.get("name", "Unknown")
        problems = category.get("problems", [])
        
        for problem in problems:
            severity = problem.get("severity", 0)
            description = problem.get("description", "")
            recommendation = problem.get("recommendation", "")
            
            all_problems.append({
                "category": category_name,
                "severity": severity,
                "description": description,
                "recommendation": recommendation
            })
    
    # Sort problems by severity (descending)
    all_problems.sort(key=lambda x: x["severity"], reverse=True)
    
    content = r"""
\section{Ключевые проблемы}

Ниже представлены наиболее серьезные проблемы, выявленные в интерфейсе:

\begin{enumerate}[leftmargin=*]
"""
    
    # Add up to 7 most severe problems
    for i, problem in enumerate(all_problems[:7]):
        severity = problem["severity"]
        description = problem["description"]
        severity_text = get_severity_text(severity)
        severity_color = get_severity_color(severity)
        
        content += f"""
  \\item \\textbf{{{description}}} \\\\
    Серьезность: \\textcolor{{{severity_color}}}{{\\textbf{{{severity}/100 - {severity_text}}}}}
"""
    
    content += r"""\end{enumerate}
"""
    return content

def get_severity_text(severity):
    """Get text representation of severity level"""
    if severity >= 80:
        return "Критическая"
    elif severity >= 60:
        return "Высокая"
    elif severity >= 40:
        return "Средняя"
    else:
        return "Низкая"

def generate_category_analysis(data, gemini_data, image_path):
    """Generate category analysis section"""
    content = r"""
\section{Детальный анализ по категориям}

"""
    
    categories = data.get("categories", [])
    
    for category in categories:
        category_name = category.get("name", "")
        category_description = category.get("description", "")
        category_score = category.get("score", 0)
        problems = category.get("problems", [])
        
        # Skip empty categories
        if not problems:
            continue
        
        severity_text = get_severity_text(category_score)
        severity_color = get_severity_color(category_score)
        
        content += f"""
\\subsection{{{category_name}}}

{category_description}

\\textbf{{Оценка сложности:}} \\textcolor{{{severity_color}}}{{\\textbf{{{category_score}/100 - {severity_text}}}}}

\\begin{{enumerate}}[leftmargin=*]
"""
        
        for problem in problems:
            problem_desc = problem.get("description", "")
            problem_recommendation = problem.get("recommendation", "")
            problem_severity = problem.get("severity", 0)
            problem_id = problem.get("id", "")
            
            severity_text = get_severity_text(problem_severity)
            severity_color = get_severity_color(problem_severity)
            
            problem_image = ""
            if gemini_data and image_path:
                problem_image = get_problem_image(problem_id, gemini_data, image_path)
            
            content += f"""
  \\item \\textbf{{{problem_desc}}}
  
    Серьезность: \\textcolor{{{severity_color}}}{{\\textbf{{{problem_severity}/100 - {severity_text}}}}}
    
    Рекомендация: {problem_recommendation}
"""
            
            if problem_image:
                content += f"""
    \\begin{{figure}}[H]
      \\centering
      \\includegraphics[width=0.7\\textwidth]{{{problem_image}}}
      \\caption{{Проблемная область: {problem_desc}}}
    \\end{{figure}}
"""
            
        content += r"""\end{enumerate}
"""
    
    return content

def get_problem_image(problem_id, gemini_data, image_path):
    """Get image for specific problem area"""
    if not problem_id or not gemini_data or not image_path:
        return ""
    
    try:
        # Find matching coordinates for problem
        coordinates = None
        for item in gemini_data.get("coordinates", []):
            if item.get("id") == problem_id and "coords" in item and item["coords"]:
                coordinates = item["coords"]
                break
        
        if not coordinates:
            return ""
        
        # Create directory for cropped images if it doesn't exist
        output_dir = "problem_images"
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract coordinates
        import numpy as np
        from PIL import Image
        
        # Create unique filename
        output_filename = f"{output_dir}/problem_{problem_id}.png"
        
        # Skip if file already exists
        if os.path.exists(output_filename):
            return output_filename
        
        # Load and crop image
        with Image.open(image_path) as img:
            x1 = coordinates.get("x1", 0)
            y1 = coordinates.get("y1", 0)
            x2 = coordinates.get("x2", img.width)
            y2 = coordinates.get("y2", img.height)
            
            # Add some padding
            padding = 10
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(img.width, x2 + padding)
            y2 = min(img.height, y2 + padding)
            
            cropped = img.crop((x1, y1, x2, y2))
            cropped.save(output_filename)
            
        return output_filename
    except Exception as e:
        logger.error(f"Error creating problem image: {e}")
        return ""

def generate_heatmap_section(heatmap_path):
    """Generate heatmap visualization section"""
    if not heatmap_path or not os.path.exists(heatmap_path):
        return ""
    
    content = r"""
\section{Тепловая карта проблем}

Ниже представлена тепловая карта, отображающая наиболее проблемные зоны интерфейса.
Интенсивность цвета соответствует степени серьезности выявленных проблем.

"""
    
    content += f"""
\\begin{{figure}}[H]
  \\centering
  \\includegraphics[width=0.95\\textwidth]{{{heatmap_path}}}
  \\caption{{Тепловая карта проблемных зон интерфейса}}
\\end{{figure}}
"""
    
    return content

def generate_recommendations(data):
    """Generate recommendations section"""
    score = data.get("overallScore", {}).get("score", 0)
    
    content = r"""
\section{Рекомендации по улучшению}

"""
    
    if score >= 80:
        content += r"""
Интерфейс имеет \textcolor{severity-critical}{\textbf{критическую}} сложность и требует существенной оптимизации.
Рекомендуется:

\begin{itemize}
  \item Провести полный редизайн проблемных разделов интерфейса
  \item Значительно сократить информационную плотность
  \item Упростить визуальную иерархию и структуру
  \item Улучшить контрастность и читабельность элементов
  \item Оптимизировать пути взаимодействия пользователя с интерфейсом
\end{itemize}
"""
    elif score >= 60:
        content += r"""
Интерфейс имеет \textcolor{severity-high}{\textbf{высокую}} сложность и требует существенных улучшений.
Рекомендуется:

\begin{itemize}
  \item Пересмотреть организацию наиболее проблемных элементов интерфейса
  \item Улучшить визуальную иерархию и группировку элементов
  \item Оптимизировать цветовую палитру и контрастность
  \item Улучшить типографику для повышения читабельности
  \item Сократить когнитивную нагрузку на пользователя
\end{itemize}
"""
    elif score >= 40:
        content += r"""
Интерфейс имеет \textcolor{severity-medium}{\textbf{среднюю}} сложность и требует точечных улучшений.
Рекомендуется:

\begin{itemize}
  \item Улучшить группировку и выравнивание элементов
  \item Повысить читабельность текстовой информации
  \item Оптимизировать цветовое оформление проблемных областей
  \item Улучшить интуитивность взаимодействия с интерфейсом
\end{itemize}
"""
    else:
        content += r"""
Интерфейс имеет \textcolor{severity-low}{\textbf{низкую}} сложность и требует минимальных улучшений.
Рекомендуется:

\begin{itemize}
  \item Провести точечные улучшения указанных проблемных областей
  \item Рассмотреть возможность улучшения контрастности отдельных элементов
  \item Оптимизировать отдельные аспекты типографики
\end{itemize}
"""
    
    return content

def generate_summary(data):
    """Generate summary section"""
    score = data.get("overallScore", {}).get("score", 0)
    num_problems = sum(len(cat.get("problems", [])) for cat in data.get("categories", []))
    
    critical = sum(1 for cat in data.get("categories", []) for prob in cat.get("problems", []) if prob.get("severity", 0) >= 80)
    high = sum(1 for cat in data.get("categories", []) for prob in cat.get("problems", []) if 60 <= prob.get("severity", 0) < 80)
    medium = sum(1 for cat in data.get("categories", []) for prob in cat.get("problems", []) if 40 <= prob.get("severity", 0) < 60)
    low = sum(1 for cat in data.get("categories", []) for prob in cat.get("problems", []) if prob.get("severity", 0) < 40)
    
    content = r"""
\section{Заключение}

"""
    
    content += f"""
Проведенный анализ выявил {num_problems} проблем различной степени серьезности:

\\begin{{itemize}}
  \\item \\textcolor{{severity-critical}}{{\\textbf{{{critical} критических проблем}}}} (80-100 баллов)
  \\item \\textcolor{{severity-high}}{{\\textbf{{{high} серьезных проблем}}}} (60-79 баллов)
  \\item \\textcolor{{severity-medium}}{{\\textbf{{{medium} проблем средней серьезности}}}} (40-59 баллов)
  \\item \\textcolor{{severity-low}}{{\\textbf{{{low} незначительных проблем}}}} (0-39 баллов)
\\end{{itemize}}

Общая оценка сложности интерфейса: \\textbf{{{score}/100}}

Реализация рекомендаций, предложенных в отчете, позволит улучшить пользовательский опыт и повысить 
эффективность взаимодействия с интерфейсом.
"""
    
    return content

def generate_latex_document(data, gemini_data, image_path, heatmap_path):
    """Generate complete LaTeX document"""
    content = generate_latex_header()
    content += generate_introduction(data)
    content += generate_key_findings(data)
    content += generate_category_analysis(data, gemini_data, image_path)
    
    if heatmap_path:
        content += generate_heatmap_section(heatmap_path)
    
    content += generate_recommendations(data)
    content += generate_summary(data)
    
    content += r"""
\end{document}
"""
    
    return content

def save_latex_to_file(content, output_path):
    """Save LaTeX content to file"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"LaTeX report saved to: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save LaTeX file: {e}")
        return False

def generate_pdf(latex_path):
    """Generate PDF from LaTeX file"""
    logger.info(f"Generating PDF from: {latex_path}")
    try:
        # Run pdflatex twice to ensure table of contents is generated correctly
        for i in range(2):
            result = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', latex_path],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.warning(f"pdflatex returned non-zero exit code on attempt {i+1}")
                logger.debug(f"pdflatex stderr: {result.stderr}")
        
        # Get PDF file path (same as latex path but with .pdf extension)
        pdf_path = os.path.splitext(latex_path)[0] + '.pdf'
        
        if os.path.exists(pdf_path):
            logger.info(f"PDF generated successfully: {pdf_path}")
            return True
        else:
            logger.error(f"PDF file not found after compilation: {pdf_path}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to generate PDF: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Generate UI analysis report")
    parser.add_argument("--input", required=True, help="Path to GPT analysis JSON file")
    parser.add_argument("--output", required=True, help="Path to save LaTeX report")
    parser.add_argument("--gemini-data", help="Path to Gemini coordinates JSON file")
    parser.add_argument("--image", help="Path to the original UI screenshot")
    parser.add_argument("--heatmap", help="Path to heatmap image")
    parser.add_argument("--pdf", action="store_true", help="Generate PDF from LaTeX file")
    
    args = parser.parse_args()
    
    try:
        # Validate input file
        if not os.path.exists(args.input):
            logger.error(f"Input file not found: {args.input}")
            return 1
        
        # Load GPT analysis data
        data = load_data(args.input)
        
        # Load Gemini data if provided
        gemini_data = None
        if args.gemini_data:
            gemini_data = load_gemini_data(args.gemini_data)
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(os.path.abspath(args.output))
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Generate LaTeX document
        latex_content = generate_latex_document(
            data=data,
            gemini_data=gemini_data,
            image_path=args.image,
            heatmap_path=args.heatmap
        )
        
        # Save LaTeX to file
        success = save_latex_to_file(latex_content, args.output)
        
        if success:
            logger.info("Report generation complete")
            
            # Generate PDF if requested
            if args.pdf:
                if generate_pdf(args.output):
                    logger.info("PDF generation complete")
                else:
                    logger.error("Failed to generate PDF")
                    return 1
        else:
            logger.error("Failed to save report")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main()) 