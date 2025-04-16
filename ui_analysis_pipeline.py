#!/usr/bin/env python3
"""
UI Analysis Pipeline

This script orchestrates the complete UI analysis process:
1. Analyze the UI screenshot using GPT-4
2. Generate strategic interpretations with Gemini
3. Generate strategic recommendations with Gemini
4. Generate a full PDF report
5. Create a heatmap visualization

This can be used as a standalone script or integrated with a Telegram bot.
"""

import os
import sys
import json
import argparse
import asyncio
import subprocess
from pathlib import Path
import logging
import base64
from io import BytesIO
from PIL import Image
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Ensure all required scripts are available
REQUIRED_SCRIPTS = [
    "api_test.py",
    "generate_report_v2.py",
    "get_gemini_recommendations.py",
    "get_gemini_interpretations.py"
]

def check_dependencies():
    """Check if all required scripts are available."""
    missing_scripts = []
    for script in REQUIRED_SCRIPTS:
        script_path = os.path.join(".", script)
        alternate_path = os.path.join("tests", script)
        
        if not os.path.exists(script_path) and not os.path.exists(alternate_path):
            missing_scripts.append(script)
    
    if missing_scripts:
        logger.error(f"Missing required scripts: {', '.join(missing_scripts)}")
        return False
    return True

async def run_gpt_analysis(screenshot_path, output_dir):
    """Run GPT-4 analysis on the screenshot."""
    logger.info(f"Running GPT-4 analysis on {screenshot_path}")
    
    output_file = os.path.join(output_dir, "gpt_analysis.json")
    
    try:
        # Execute the GPT analysis script
        process = await asyncio.create_subprocess_exec(
            sys.executable, "tests/api_test.py",
            "--image", screenshot_path,
            "--output", output_file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"GPT analysis failed: {stderr.decode()}")
            return False, stderr.decode()
        
        logger.info(f"GPT-4 analysis completed successfully. Output saved to {output_file}")
        return True, output_file
    except Exception as e:
        logger.error(f"Error running GPT analysis: {e}")
        return False, str(e)

async def run_gemini_interpretation(screenshot_path, gpt_analysis_path, output_dir):
    """Generate strategic interpretations using Gemini."""
    logger.info("Generating strategic interpretations with Gemini")
    
    output_file = os.path.join(output_dir, "gemini_interpretation.txt")
    coords_file = os.path.join(output_dir, "gemini_coords.json")
    
    try:
        # Execute the Gemini interpretations script
        process = await asyncio.create_subprocess_exec(
            sys.executable, "get_gemini_interpretations.py",
            "--image", screenshot_path,
            "--analysis", gpt_analysis_path,
            "--output", output_file,
            "--coords", coords_file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Gemini interpretation failed: {stderr.decode()}")
            return False, stderr.decode()
        
        logger.info(f"Gemini interpretation completed successfully. Output saved to {output_file}")
        return True, {"text": output_file, "coords": coords_file}
    except Exception as e:
        logger.error(f"Error running Gemini interpretation: {e}")
        return False, str(e)

async def run_gemini_recommendations(screenshot_path, gpt_analysis_path, output_dir):
    """Generate strategic recommendations using Gemini."""
    logger.info("Generating strategic recommendations with Gemini")
    
    output_file = os.path.join(output_dir, "gemini_recommendations.txt")
    
    try:
        # Execute the Gemini recommendations script
        process = await asyncio.create_subprocess_exec(
            sys.executable, "get_gemini_recommendations.py",
            "--image", screenshot_path,
            "--analysis", gpt_analysis_path,
            "--output", output_file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Gemini recommendations failed: {stderr.decode()}")
            return False, stderr.decode()
        
        logger.info(f"Gemini recommendations completed successfully. Output saved to {output_file}")
        return True, output_file
    except Exception as e:
        logger.error(f"Error running Gemini recommendations: {e}")
        return False, str(e)

async def generate_heatmap(gpt_analysis_path, gemini_coords_path, screenshot_path, output_dir):
    """Generate a heatmap visualization of problem areas."""
    logger.info("Generating heatmap visualization")
    
    output_file = os.path.join(output_dir, "heatmap.png")
    
    # This would typically call a heatmap generation script
    # For now, we'll assume it's part of the report generation
    logger.info(f"Heatmap will be generated as part of the report process")
    return True, output_file

async def generate_report(gpt_analysis_path, gemini_coords_path, screenshot_path, heatmap_path, output_dir):
    """Generate the PDF report using all the analysis data."""
    logger.info("Generating comprehensive PDF report")
    
    output_tex = os.path.join(output_dir, "ui_analysis_report.tex")
    output_pdf = os.path.join(output_dir, "ui_analysis_report.pdf")
    
    try:
        # Execute the report generation script
        process = await asyncio.create_subprocess_exec(
            sys.executable, "generate_report_v2.py",
            "--input", gpt_analysis_path,
            "--output", output_tex,
            "--pdf",
            "--gemini-data", gemini_coords_path,
            "--image", screenshot_path,
            "--heatmap", heatmap_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"Report generation failed: {stderr.decode()}")
            return False, stderr.decode()
        
        logger.info(f"Report generation completed successfully. PDF saved to {output_pdf}")
        return True, {"tex": output_tex, "pdf": output_pdf}
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return False, str(e)

async def run_analysis_pipeline(screenshot_path, context=None, userflows=None):
    """
    Run the complete analysis pipeline from start to finish.
    
    Args:
        screenshot_path (str): Path to the UI screenshot to analyze
        context (str, optional): Description of what's in the screenshot
        userflows (str, optional): Description of user flows/scenarios
        
    Returns:
        tuple: (success (bool), results (dict))
    """
    logger.info(f"Starting UI analysis pipeline for {screenshot_path}")
    
    # Create a unique output directory for this analysis
    file_id = os.path.splitext(os.path.basename(screenshot_path))[0]
    output_dir = os.path.join("output", file_id)
    os.makedirs(output_dir, exist_ok=True)
    
    # Save context and userflows if provided
    if context:
        with open(os.path.join(output_dir, "context.txt"), "w") as f:
            f.write(context)
    
    if userflows:
        with open(os.path.join(output_dir, "userflows.txt"), "w") as f:
            f.write(userflows)
    
    results = {}
    
    # Step 1: Run GPT-4 analysis
    success_gpt, gpt_result = await run_gpt_analysis(screenshot_path, output_dir)
    if not success_gpt:
        return False, {"error": f"GPT analysis failed: {gpt_result}"}
    
    results["gpt_analysis"] = gpt_result
    
    # Step 2: Generate Gemini interpretation and get coordinates
    success_interpret, interpret_result = await run_gemini_interpretation(
        screenshot_path, gpt_result, output_dir
    )
    if not success_interpret:
        return False, {"error": f"Gemini interpretation failed: {interpret_result}"}
    
    results["gemini_interpretation"] = interpret_result["text"]
    results["gemini_coords"] = interpret_result["coords"]
    
    # Step 3: Generate Gemini recommendations
    success_recommend, recommend_result = await run_gemini_recommendations(
        screenshot_path, gpt_result, output_dir
    )
    if not success_recommend:
        return False, {"error": f"Gemini recommendations failed: {recommend_result}"}
    
    results["gemini_recommendations"] = recommend_result
    
    # Step 4: Generate heatmap (this might be done as part of report generation)
    success_heatmap, heatmap_result = await generate_heatmap(
        gpt_result, results["gemini_coords"], screenshot_path, output_dir
    )
    
    results["heatmap"] = heatmap_result
    
    # Step 5: Generate comprehensive PDF report
    success_report, report_result = await generate_report(
        gpt_result, results["gemini_coords"], screenshot_path, 
        results["heatmap"], output_dir
    )
    if not success_report:
        return False, {"error": f"Report generation failed: {report_result}"}
    
    results["report_tex"] = report_result["tex"]
    results["report_pdf"] = report_result["pdf"]
    
    logger.info(f"UI analysis pipeline completed successfully for {screenshot_path}")
    return True, results

def process_base64_image(base64_string, output_dir):
    """
    Process a base64 encoded image and save it to disk.
    
    Args:
        base64_string (str): Base64 encoded image string
        output_dir (str): Directory to save the image
        
    Returns:
        str: Path to the saved image
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Decode base64 image
        image_data = base64.b64decode(base64_string)
        image = Image.open(BytesIO(image_data))
        
        # Generate a temporary file name
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png", dir=output_dir)
        image_path = temp_file.name
        temp_file.close()
        
        # Save the image
        image.save(image_path, format="PNG")
        logger.info(f"Saved base64 image to {image_path}")
        
        return image_path
    except Exception as e:
        logger.error(f"Error processing base64 image: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="UI Analysis Pipeline")
    parser.add_argument("--image", "-i", type=str, required=True, 
                        help="Path to the UI screenshot or base64 encoded image")
    parser.add_argument("--context", "-c", type=str, 
                        help="Description of what's in the screenshot")
    parser.add_argument("--userflows", "-u", type=str, 
                        help="Description of user flows/scenarios")
    parser.add_argument("--output-dir", "-o", type=str, default="output",
                        help="Directory to store output files")
                        
    args = parser.parse_args()
    
    # Check if all dependencies are available
    if not check_dependencies():
        sys.exit(1)
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Check if the image is a file path or base64 string
    screenshot_path = args.image
    if not os.path.exists(args.image) and len(args.image) > 100:
        # This is likely a base64 string
        screenshot_path = process_base64_image(args.image, args.output_dir)
        if not screenshot_path:
            logger.error("Failed to process base64 image")
            sys.exit(1)
    
    # Run the analysis pipeline
    success, results = asyncio.run(run_analysis_pipeline(
        screenshot_path, args.context, args.userflows
    ))
    
    if success:
        print("UI Analysis completed successfully!")
        print("\nResults:")
        print(f"  GPT Analysis: {results.get('gpt_analysis', 'N/A')}")
        print(f"  Gemini Interpretation: {results.get('gemini_interpretation', 'N/A')}")
        print(f"  Gemini Recommendations: {results.get('gemini_recommendations', 'N/A')}")
        print(f"  Heatmap: {results.get('heatmap', 'N/A')}")
        print(f"  PDF Report: {results.get('report_pdf', 'N/A')}")
    else:
        print(f"UI Analysis failed: {results.get('error', 'Unknown error')}")
        sys.exit(1)

if __name__ == "__main__":
    main() 