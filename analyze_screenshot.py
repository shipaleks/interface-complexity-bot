#!/usr/bin/env python3
import os
import json
import time
import logging
import argparse
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Default paths
DEFAULT_OUTPUT_DIR = "analysis_results"
DEFAULT_GPT_MODEL = "gpt-4o"
DEFAULT_GEMINI_MODEL = "gemini-1.5-pro"

def ensure_dir_exists(directory):
    """Ensure directory exists"""
    os.makedirs(directory, exist_ok=True)
    return directory

def run_command(cmd, desc=None, check=True):
    """Run shell command and log output"""
    if desc:
        logger.info(f"Running: {desc}")
    
    logger.debug(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            logger.debug(f"Command stdout:\n{result.stdout}")
        
        if result.stderr:
            if result.returncode != 0:
                logger.error(f"Command stderr:\n{result.stderr}")
            else:
                logger.debug(f"Command stderr:\n{result.stderr}")
        
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        logger.error(f"Command stdout:\n{e.stdout}")
        logger.error(f"Command stderr:\n{e.stderr}")
        raise

def run_gpt_analysis(screenshot_path, description=None, user_flow=None, output_dir=None, model=DEFAULT_GPT_MODEL):
    """Run GPT analysis on screenshot"""
    output_path = os.path.join(output_dir, "gpt_analysis.json")
    
    cmd = [
        "python", "gpt_analyze.py",
        "--image", screenshot_path,
        "--output", output_path,
        "--model", model
    ]
    
    if description:
        cmd.extend(["--description", description])
    
    if user_flow:
        cmd.extend(["--user-flow", user_flow])
    
    run_command(cmd, "GPT analysis")
    
    return output_path

def run_gemini_analysis(screenshot_path, output_dir=None, model=DEFAULT_GEMINI_MODEL):
    """Run Gemini analysis to extract coordinates"""
    output_path = os.path.join(output_dir, "gemini_coordinates.json")
    
    cmd = [
        "python", "get_gemini_coordinates.py",
        "--image", screenshot_path,
        "--output", output_path,
        "--model", model
    ]
    
    run_command(cmd, "Gemini coordinate extraction")
    
    return output_path

def generate_heatmap(coordinates_path, screenshot_path, output_dir=None):
    """Generate heatmap from coordinates"""
    output_path = os.path.join(output_dir, "heatmap.png")
    
    cmd = [
        "python", "generate_heatmap.py",
        "--coordinates", coordinates_path,
        "--screenshot", screenshot_path,
        "--output", output_path
    ]
    
    run_command(cmd, "Heatmap generation")
    
    return output_path

def generate_pdf_report(gpt_analysis_path, gemini_data_path, screenshot_path, heatmap_path, output_dir=None):
    """Generate PDF report"""
    output_latex_path = os.path.join(output_dir, "ui_analysis_report.tex")
    output_pdf_path = os.path.join(output_dir, "ui_analysis_report.pdf")
    
    cmd = [
        "python", "generate_report.py",
        "--input", gpt_analysis_path,
        "--output", output_latex_path,
        "--gemini-data", gemini_data_path,
        "--image", screenshot_path,
        "--heatmap", heatmap_path,
        "--pdf"
    ]
    
    run_command(cmd, "PDF report generation")
    
    return output_pdf_path

def get_summary(gpt_analysis_path, output_dir=None):
    """Extract summary from GPT analysis"""
    output_path = os.path.join(output_dir, "summary.txt")
    
    try:
        with open(gpt_analysis_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        overall_score = data.get("overallScore", {}).get("score", 0)
        interpretation = data.get("overallScore", {}).get("interpretation", "")
        
        # Get top problems
        all_problems = []
        for category in data.get("categories", []):
            for problem in category.get("problems", []):
                all_problems.append({
                    "description": problem.get("description", ""),
                    "severity": problem.get("severity", 0),
                    "recommendation": problem.get("recommendation", "")
                })
        
        # Sort by severity
        all_problems.sort(key=lambda x: x["severity"], reverse=True)
        
        # Create summary
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"UI Complexity Analysis Summary\n")
            f.write(f"==============================\n\n")
            f.write(f"Overall Complexity Score: {overall_score}/100\n\n")
            f.write(f"Interpretation:\n{interpretation}\n\n")
            
            f.write(f"Top 5 Critical Issues:\n")
            for i, problem in enumerate(all_problems[:5]):
                f.write(f"{i+1}. {problem['description']} (Severity: {problem['severity']}/100)\n")
                f.write(f"   Recommendation: {problem['recommendation']}\n\n")
        
        logger.info(f"Summary saved to: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        return None

def analyze_screenshot(
    screenshot_path, 
    description=None, 
    user_flow=None, 
    output_dir=None,
    gpt_model=DEFAULT_GPT_MODEL,
    gemini_model=DEFAULT_GEMINI_MODEL
):
    """Full analysis pipeline"""
    start_time = time.time()
    logger.info(f"Starting UI complexity analysis for: {screenshot_path}")
    
    # Validate screenshot path
    if not os.path.exists(screenshot_path):
        raise FileNotFoundError(f"Screenshot not found: {screenshot_path}")
    
    # Create output directory
    if not output_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.splitext(os.path.basename(screenshot_path))[0]
        output_dir = os.path.join(DEFAULT_OUTPUT_DIR, f"{filename}_{timestamp}")
    
    output_dir = ensure_dir_exists(output_dir)
    logger.info(f"Analysis results will be saved to: {output_dir}")
    
    # Run GPT analysis
    gpt_analysis_path = run_gpt_analysis(
        screenshot_path=screenshot_path,
        description=description,
        user_flow=user_flow,
        output_dir=output_dir,
        model=gpt_model
    )
    
    # Run Gemini analysis for coordinates
    gemini_data_path = run_gemini_analysis(
        screenshot_path=screenshot_path,
        output_dir=output_dir,
        model=gemini_model
    )
    
    # Generate heatmap
    heatmap_path = generate_heatmap(
        coordinates_path=gemini_data_path,
        screenshot_path=screenshot_path,
        output_dir=output_dir
    )
    
    # Generate PDF report
    pdf_path = generate_pdf_report(
        gpt_analysis_path=gpt_analysis_path,
        gemini_data_path=gemini_data_path,
        screenshot_path=screenshot_path,
        heatmap_path=heatmap_path,
        output_dir=output_dir
    )
    
    # Generate summary
    summary_path = get_summary(
        gpt_analysis_path=gpt_analysis_path,
        output_dir=output_dir
    )
    
    # Report completion
    elapsed_time = time.time() - start_time
    logger.info(f"Analysis completed in {elapsed_time:.2f} seconds")
    logger.info(f"Results saved to: {output_dir}")
    logger.info(f"PDF report: {pdf_path}")
    logger.info(f"Heatmap: {heatmap_path}")
    
    return {
        "output_dir": output_dir,
        "gpt_analysis_path": gpt_analysis_path,
        "gemini_data_path": gemini_data_path,
        "heatmap_path": heatmap_path,
        "pdf_path": pdf_path,
        "summary_path": summary_path
    }

def main():
    parser = argparse.ArgumentParser(description="Analyze UI screenshot for complexity issues")
    parser.add_argument("--image", required=True, help="Path to screenshot image")
    parser.add_argument("--description", help="Description of what's in the screenshot")
    parser.add_argument("--user-flow", help="Description of user flows in the interface")
    parser.add_argument("--output-dir", help="Output directory for analysis results")
    parser.add_argument("--gpt-model", default=DEFAULT_GPT_MODEL, help="GPT model to use for analysis")
    parser.add_argument("--gemini-model", default=DEFAULT_GEMINI_MODEL, help="Gemini model to use for coordinate extraction")
    
    args = parser.parse_args()
    
    try:
        results = analyze_screenshot(
            screenshot_path=args.image,
            description=args.description,
            user_flow=args.user_flow,
            output_dir=args.output_dir,
            gpt_model=args.gpt_model,
            gemini_model=args.gemini_model
        )
        
        print(f"\nAnalysis completed successfully!")
        print(f"Results directory: {results['output_dir']}")
        print(f"PDF report: {results['pdf_path']}")
        print(f"Heatmap: {results['heatmap_path']}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        print(f"\nAnalysis failed: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main()) 