#!/usr/bin/env python3
"""
Analysis Pipeline Module.

This module orchestrates the execution of all analysis steps:
1. GPT-4.1 analysis and report generation
2. Gemini strategic interpretation generation
3. Gemini strategic recommendations generation
"""

import os
import asyncio
import subprocess
import logging
from typing import Dict, Optional, Any, List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_analysis_pipeline(
    screenshot_path: str,
    file_id: str,
    context: Optional[str] = None,
    userflows: Optional[str] = None
) -> Optional[Dict[str, str]]:
    """
    Run the complete analysis pipeline.
    
    Args:
        screenshot_path: Path to the screenshot image
        file_id: Unique identifier for this analysis run
        context: Optional description of what's in the screenshot
        userflows: Optional description of user flows
        
    Returns:
        Dictionary with paths to generated files, or None if error
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs("results", exist_ok=True)
        
        # Step 1: Run GPT-4.1 Analysis and Report Generation
        logger.info(f"Starting GPT analysis for {file_id}")
        
        gpt_analysis_path = f"results/{file_id}_gpt_analysis.json"
        tex_report_path = f"results/{file_id}_report.tex"
        pdf_report_path = f"results/{file_id}_report.pdf"
        heatmap_path = f"results/{file_id}_heatmap.png"
        
        success, output = await run_gpt_analysis(
            screenshot_path=screenshot_path,
            output_json_path=gpt_analysis_path,
            output_pdf_path=pdf_report_path,
            output_heatmap_path=heatmap_path,
            context=context,
            userflows=userflows
        )
        
        if not success:
            logger.error(f"GPT analysis failed: {output}")
            return None
            
        logger.info(f"GPT analysis completed for {file_id}")
        
        # Step 2: Generate Strategic Interpretation with Gemini
        logger.info(f"Starting Gemini interpretation for {file_id}")
        
        interpretation_path = f"results/{file_id}_interpretation.json"
        
        success, output = await run_gemini_interpretation(
            input_json_path=gpt_analysis_path,
            output_path=interpretation_path
        )
        
        if not success:
            logger.error(f"Gemini interpretation failed: {output}")
            # We can continue even if this step fails
            
        logger.info(f"Gemini interpretation completed for {file_id}")
        
        # Step 3: Generate Strategic Recommendations with Gemini
        logger.info(f"Starting Gemini recommendations for {file_id}")
        
        recommendations_path = f"results/{file_id}_recommendations.json"
        
        success, output = await run_gemini_recommendations(
            input_json_path=gpt_analysis_path,
            output_path=recommendations_path
        )
        
        if not success:
            logger.error(f"Gemini recommendations failed: {output}")
            # We can continue even if this step fails
            
        logger.info(f"Gemini recommendations completed for {file_id}")
        
        # Return paths to all generated files
        return {
            "gpt_analysis_path": gpt_analysis_path,
            "tex_report_path": tex_report_path,
            "pdf_report_path": pdf_report_path,
            "heatmap_path": heatmap_path,
            "interpretation_path": interpretation_path,
            "recommendations_path": recommendations_path
        }
        
    except Exception as e:
        logger.error(f"Error in analysis pipeline: {str(e)}", exc_info=True)
        return None
        
async def run_gpt_analysis(
    screenshot_path: str,
    output_json_path: str,
    output_pdf_path: str,
    output_heatmap_path: str,
    context: Optional[str] = None,
    userflows: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Run GPT-4.1 analysis using generate_report_v2.py.
    
    Args:
        screenshot_path: Path to the screenshot image
        output_json_path: Path to save GPT analysis JSON
        output_pdf_path: Expected path of the generated PDF (used for check)
        output_heatmap_path: Path to save heatmap image
        context: Optional description of what's in the screenshot
        userflows: Optional description of user flows
        
    Returns:
        Tuple of (success, output/error message)
    """
    try:
        # Removed --tex argument as it's not recognized by generate_report_v2.py
        # Passing screenshot as --input based on previous error.
        cmd = [
            "python", "generate_report_v2.py",
            "--input", screenshot_path,
            "--image", screenshot_path,
            "--output", output_json_path,
            "--heatmap", output_heatmap_path,
            "--pdf"  # Flag to generate PDF
        ]
        
        # Add optional arguments if provided
        if context:
            cmd.extend(["--context", context])
            
        if userflows:
            cmd.extend(["--user-flows", userflows])
            
        # Run command
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            return False, f"Command failed with exit code {process.returncode}: {stderr.decode()}"
            
        return True, stdout.decode()
        
    except Exception as e:
        return False, f"Exception during GPT analysis: {str(e)}"

async def run_gemini_interpretation(
    input_json_path: str,
    output_path: str
) -> Tuple[bool, str]:
    """
    Generate strategic interpretation using Gemini.
    
    Args:
        input_json_path: Path to the GPT analysis JSON
        output_path: Path to save Gemini interpretation
        
    Returns:
        Tuple of (success, output/error message)
    """
    try:
        cmd = [
            "python", "get_gemini_recommendations.py",
            "--input", input_json_path,
            "--prompt-file", "gemini_interpretation_prompt.md",
            "--output", output_path
        ]
        
        # Run command
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            return False, f"Command failed with exit code {process.returncode}: {stderr.decode()}"
            
        return True, stdout.decode()
        
    except Exception as e:
        return False, f"Exception during Gemini interpretation: {str(e)}"

async def run_gemini_recommendations(
    input_json_path: str,
    output_path: str
) -> Tuple[bool, str]:
    """
    Generate strategic recommendations using Gemini.
    
    Args:
        input_json_path: Path to the GPT analysis JSON
        output_path: Path to save Gemini recommendations
        
    Returns:
        Tuple of (success, output/error message)
    """
    try:
        cmd = [
            "python", "get_gemini_recommendations.py",
            "--input", input_json_path,
            "--prompt-file", "gemini_recommendations_only_prompt.md",
            "--output", output_path
        ]
        
        # Run command
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            return False, f"Command failed with exit code {process.returncode}: {stderr.decode()}"
            
        return True, stdout.decode()
        
    except Exception as e:
        return False, f"Exception during Gemini recommendations: {str(e)}" 