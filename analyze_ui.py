#!/usr/bin/env python3
import os
import json
import argparse
import logging
import tempfile
from typing import Dict, List, Any, Tuple, Optional
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv
import sys
import base64
from datetime import datetime
import requests
import traceback
from PIL import Image
import shutil
import asyncio
import aiohttp
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Add parent directory to path to import from the main project
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Path to existing scripts in the main project
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# API keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Check for required API keys
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in the .env file")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in the .env file")

class UIAnalyzer:
    """Class for analyzing UI screenshots and generating reports."""
    
    def __init__(self, output_dir: str = "./output"):
        """Initialize UIAnalyzer with output directory."""
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Subdirectories for organized output
        self.images_dir = os.path.join(output_dir, "images")
        self.reports_dir = os.path.join(output_dir, "reports")
        self.data_dir = os.path.join(output_dir, "data")
        
        # Create subdirectories
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load prompt templates
        self.gpt_prompt_template = self._load_prompt_template("gpt_prompt.txt")
        self.gemini_prompt_template = self._load_prompt_template("gemini_prompt.txt")
    
    def _load_prompt_template(self, filename: str) -> str:
        """Load a prompt template from file."""
        prompt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts", filename)
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"Prompt template {filename} not found. Using default.")
            if "gpt" in filename:
                return """Analyze this UI screenshot for complexity issues. 
                Score it on a scale of 1-100 and identify specific problems."""
            elif "gemini" in filename:
                return """Look at this UI screenshot and identify problem areas. 
                For each problem, provide x,y coordinates of the bounding box."""
            else:
                return "Analyze this image."
    
    async def analyze_screenshot(self, screenshot_path: str, user_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze a UI screenshot and generate a complete report.
        
        Args:
            screenshot_path: Path to the screenshot image
            user_context: Optional context about the interface
            
        Returns:
            Dictionary containing analysis results
        """
        logger.info(f"Starting analysis of screenshot: {screenshot_path}")
        
        # Generate unique ID for this analysis
        analysis_id = f"analysis_{int(time.time())}"
        
        # Create a temporary directory for this analysis
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Copy screenshot to output directory
                screenshot_filename = os.path.basename(screenshot_path)
                output_image_path = os.path.join(self.images_dir, f"{analysis_id}_{screenshot_filename}")
                shutil.copy(screenshot_path, output_image_path)
                
                # Step 1: Run GPT-4 analysis
                logger.info("Running GPT-4 analysis...")
                gpt_results_path = os.path.join(self.data_dir, f"{analysis_id}_gpt_analysis.json")
                gpt_analysis = await self._run_gpt_analysis(screenshot_path, user_context, gpt_results_path)
                
                # Step 2: Extract coordinates with Gemini
                logger.info("Extracting coordinates with Gemini...")
                coordinates_path = os.path.join(self.data_dir, f"{analysis_id}_coordinates.json")
                coordinates_data = await self._extract_coordinates(
                    screenshot_path, 
                    gpt_analysis, 
                    coordinates_path
                )
                
                # Step 3: Generate heatmap
                logger.info("Generating heatmap visualization...")
                heatmap_path = os.path.join(self.images_dir, f"{analysis_id}_heatmap.png")
                heatmap_generated = await self._generate_heatmap(
                    screenshot_path, 
                    coordinates_data, 
                    heatmap_path
                )
                
                # Step 4: Extract structured data from GPT analysis
                overall_score = gpt_analysis.get('overallScore', 0)
                category_scores = self._extract_category_scores(gpt_analysis)
                top_issues = self._extract_top_issues(gpt_analysis)
                
                # Step 5: Generate PDF report
                logger.info("Generating PDF report...")
                report_path = os.path.join(self.reports_dir, f"{analysis_id}_report.pdf")
                report_generated = await self._generate_pdf_report(
                    output_image_path,
                    gpt_results_path,
                    coordinates_path,
                    heatmap_path,
                    report_path
                )
                
                # Step 6: Generate strategic recommendations
                recommendations = self._get_strategic_recommendations(gpt_analysis, overall_score)
                
                # Prepare results
                results = {
                    "analysis_id": analysis_id,
                    "overall_score": overall_score,
                    "categories": category_scores,
                    "top_issues": top_issues,
                    "recommendations": recommendations,
                    "image_path": output_image_path,
                    "heatmap_path": heatmap_path if heatmap_generated else None,
                    "report_path": report_path if report_generated else None,
                    "gpt_analysis": gpt_analysis,
                    "coordinates_data": coordinates_data
                }
                
                # Save complete results
                results_path = os.path.join(self.data_dir, f"{analysis_id}_complete_results.json")
                with open(results_path, "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2)
                
                logger.info(f"Analysis completed successfully. ID: {analysis_id}")
                return results
                
            except Exception as e:
                logger.error(f"Error during analysis: {e}")
                logger.error(traceback.format_exc())
                raise
    
    async def _run_gpt_analysis(
        self, 
        image_path: str, 
        user_context: Optional[str], 
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze UI screenshot using GPT-4 Vision.
        
        Args:
            image_path: Path to the screenshot
            user_context: Optional context about the interface
            output_path: Optional path to save the results
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            # Read and encode image
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode("utf-8")
            
            # Prepare prompt
            prompt = self.gpt_prompt_template
            if user_context:
                prompt += f"\n\nAdditional context: {user_context}"
            
            # Prepare request
            payload = {
                "model": "gpt-4-vision-preview",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 4000
            }
            
            # Make API call
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    response_data = await response.json()
                    
                    if response.status != 200:
                        error_msg = response_data.get("error", {}).get("message", "Unknown error")
                        logger.error(f"GPT API error: {error_msg}")
                        raise Exception(f"GPT API error: {error_msg}")
                    
                    # Extract the response content
                    response_message = response_data["choices"][0]["message"]["content"]
                    
                    # Parse the JSON response
                    try:
                        start_index = response_message.find("{")
                        end_index = response_message.rfind("}")
                        
                        if start_index >= 0 and end_index > start_index:
                            json_str = response_message[start_index:end_index+1]
                            analysis_results = json.loads(json_str)
                        else:
                            logger.warning("JSON not found in GPT response. Using full response.")
                            analysis_results = {"rawResponse": response_message}
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse JSON from GPT response. Using full response.")
                        analysis_results = {"rawResponse": response_message}
                    
                    # Save to file if output path is provided
                    if output_path:
                        with open(output_path, "w", encoding="utf-8") as f:
                            json.dump(analysis_results, f, indent=2)
                    
                    return analysis_results
                    
        except Exception as e:
            logger.error(f"Error in GPT analysis: {e}")
            logger.error(traceback.format_exc())
            raise
    
    async def _extract_coordinates(
        self, 
        image_path: str, 
        gpt_analysis: Dict[str, Any], 
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract coordinates of UI problems using Gemini Vision.
        
        Args:
            image_path: Path to the screenshot
            gpt_analysis: Results from GPT analysis
            output_path: Optional path to save the results
            
        Returns:
            Dictionary containing coordinates data
        """
        try:
            # Read and encode image
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode("utf-8")
            
            # Get image dimensions
            with Image.open(image_path) as img:
                width, height = img.size
            
            # Extract problems from GPT analysis
            problems = gpt_analysis.get("problems", [])
            if not problems:
                logger.warning("No problems found in GPT analysis")
                return {"coordinates": []}
            
            # Sort problems by severity
            problems.sort(key=lambda x: x.get("severity", 0), reverse=True)
            
            # Take top 30 problems
            top_problems = problems[:30]
            
            # Prepare problem descriptions for Gemini
            problem_descriptions = []
            for idx, problem in enumerate(top_problems, 1):
                name = problem.get("name", "Unnamed issue")
                description = problem.get("description", "")
                category = problem.get("category", "")
                severity = problem.get("severity", 0)
                
                problem_descriptions.append(
                    f"{idx}. {name} ({category}): {description} (Severity: {severity}/100)"
                )
            
            # Prepare prompt for Gemini
            prompt = self.gemini_prompt_template.format(
                image_width=width,
                image_height=height,
                problem_list="\n".join(problem_descriptions)
            )
            
            # Prepare request
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": image_data
                                }
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 4000
                }
            }
            
            # Make API call
            headers = {
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key={GEMINI_API_KEY}",
                    headers=headers,
                    json=payload
                ) as response:
                    response_data = await response.json()
                    
                    if response.status != 200:
                        error_msg = response_data.get("error", {}).get("message", "Unknown error")
                        logger.error(f"Gemini API error: {error_msg}")
                        raise Exception(f"Gemini API error: {error_msg}")
                    
                    # Extract the response content
                    response_text = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    
                    # Parse coordinates from the response
                    coordinates = []
                    lines = response_text.strip().split('\n')
                    
                    for line in lines:
                        if ':' in line and '[' in line and ']' in line:
                            try:
                                # Extract problem index and coordinates
                                parts = line.split(':')
                                if len(parts) < 2:
                                    continue
                                    
                                problem_idx_str = parts[0].strip().rstrip('.')
                                coords_str = parts[1].strip()
                                
                                # Try to get problem index
                                try:
                                    problem_idx = int(problem_idx_str) - 1  # Convert to 0-based index
                                    if problem_idx < 0 or problem_idx >= len(top_problems):
                                        continue
                                        
                                    problem = top_problems[problem_idx]
                                except ValueError:
                                    continue
                                
                                # Extract coordinates
                                coords_match = coords_str.split('[')[1].split(']')[0]
                                coords_values = [int(x.strip()) for x in coords_match.split(',')]
                                
                                if len(coords_values) == 4:
                                    # Ensure coordinates are within image bounds
                                    x1 = max(0, min(coords_values[0], width))
                                    y1 = max(0, min(coords_values[1], height))
                                    x2 = max(0, min(coords_values[2], width))
                                    y2 = max(0, min(coords_values[3], height))
                                    
                                    coordinates.append({
                                        "problem": problem,
                                        "coordinates": [x1, y1, x2, y2]
                                    })
                            except Exception as e:
                                logger.warning(f"Error parsing coordinate line '{line}': {e}")
                    
                    # Create results dictionary
                    coordinates_data = {
                        "image_dimensions": {"width": width, "height": height},
                        "coordinates": coordinates
                    }
                    
                    # Save to file if output path is provided
                    if output_path:
                        with open(output_path, "w", encoding="utf-8") as f:
                            json.dump(coordinates_data, f, indent=2)
                    
                    return coordinates_data
                    
        except Exception as e:
            logger.error(f"Error in coordinate extraction: {e}")
            logger.error(traceback.format_exc())
            raise
    
    async def _generate_heatmap(
        self, 
        image_path: str, 
        coordinates_data: Dict[str, Any], 
        output_path: str
    ) -> bool:
        """
        Generate a heatmap visualization of UI problems.
        
        Args:
            image_path: Path to the screenshot
            coordinates_data: Coordinates data from Gemini
            output_path: Path to save the generated heatmap
            
        Returns:
            Boolean indicating success
        """
        try:
            # Get image dimensions
            image_dimensions = coordinates_data.get("image_dimensions", {})
            width = image_dimensions.get("width", 0)
            height = image_dimensions.get("height", 0)
            
            if width <= 0 or height <= 0:
                with Image.open(image_path) as img:
                    width, height = img.size
            
            # Create a heatmap array
            heatmap_data = np.zeros((height, width))
            
            # Add problem areas to the heatmap
            coordinates_list = coordinates_data.get("coordinates", [])
            if not coordinates_list:
                logger.warning("No coordinates found for heatmap generation")
                return False
            
            for item in coordinates_list:
                coords = item.get("coordinates", [])
                problem = item.get("problem", {})
                
                if len(coords) == 4:
                    x1, y1, x2, y2 = coords
                    
                    # Get severity weight (normalized to 0-1)
                    severity = problem.get("severity", 50) / 100
                    
                    # Add weighted area to the heatmap
                    heatmap_data[y1:y2, x1:x2] += severity
            
            # Normalize the heatmap
            if np.max(heatmap_data) > 0:
                heatmap_data = heatmap_data / np.max(heatmap_data)
            
            # Set up the plot
            plt.figure(figsize=(width/100, height/100), dpi=100)
            
            # Load and display the original image
            img = plt.imread(image_path)
            plt.imshow(img)
            
            # Overlay the heatmap
            plt.imshow(heatmap_data, cmap='hot', alpha=0.5)
            
            # Remove axes
            plt.axis('off')
            
            # Save the heatmap
            plt.tight_layout(pad=0)
            plt.savefig(output_path, bbox_inches='tight', pad_inches=0)
            plt.close()
            
            logger.info(f"Heatmap saved to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating heatmap: {e}")
            logger.error(traceback.format_exc())
            return False
    
    async def _generate_pdf_report(
        self,
        image_path: str,
        gpt_results_path: str,
        coordinates_path: str,
        heatmap_path: str,
        output_path: str
    ) -> bool:
        """
        Generate a PDF report with the analysis results.
        
        Args:
            image_path: Path to the original screenshot
            gpt_results_path: Path to GPT analysis results
            coordinates_path: Path to coordinates data
            heatmap_path: Path to heatmap image
            output_path: Path to save the PDF report
            
        Returns:
            Boolean indicating success
        """
        try:
            # Create temporary files for input data
            with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_gpt_file, \
                 tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_gemini_file:
                
                # Copy input files to temp locations
                shutil.copy(gpt_results_path, temp_gpt_file.name)
                shutil.copy(coordinates_path, temp_gemini_file.name)
                
                # Run the report generation command
                cmd = [
                    "python", "generate_report.py",
                    "--gpt", temp_gpt_file.name,
                    "--gemini-data", temp_gemini_file.name,
                    "--image", image_path,
                    "--heatmap", heatmap_path,
                    "--output", output_path,
                    "--pdf"
                ]
                
                # Create process
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                # Wait for process to complete
                stdout, stderr = await process.communicate()
                
                # Log output
                logger.info(f"Report generation stdout: {stdout.decode()}")
                if stderr:
                    logger.warning(f"Report generation stderr: {stderr.decode()}")
                
                # Check if PDF was created
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    logger.info(f"PDF report generated: {output_path}")
                    return True
                else:
                    logger.warning(f"PDF report not generated at {output_path}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error generating PDF report: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def _get_strategic_recommendations(self, analysis: Dict[str, Any], overall_score: int) -> List[str]:
        """
        Generate strategic recommendations based on analysis results.
        
        Args:
            analysis: GPT analysis results
            overall_score: Overall complexity score
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Overall complexity recommendation
        if overall_score >= 80:
            recommendations.append(
                "Consider a significant interface redesign focused on simplification. "
                "The current complexity level may cause high user frustration and abandonment."
            )
        elif overall_score >= 60:
            recommendations.append(
                "Implement targeted improvements to reduce complexity in key areas. "
                "Focus on streamlining the most severe problem areas first."
            )
        elif overall_score >= 40:
            recommendations.append(
                "Make moderate improvements to enhance usability while maintaining the current design direction. "
                "Address the identified issues incrementally."
            )
        else:
            recommendations.append(
                "The interface has good usability fundamentals. Consider fine-tuning the minor issues "
                "to further enhance user experience."
            )
        
        # Group problems by category
        problems = analysis.get("problems", [])
        problems_by_category = {}
        
        for problem in problems:
            category = problem.get("category", "Other")
            if category not in problems_by_category:
                problems_by_category[category] = []
            problems_by_category[category].append(problem)
        
        # Category-specific recommendations
        for category, category_problems in problems_by_category.items():
            # Sort by severity
            category_problems.sort(key=lambda x: x.get("severity", 0), reverse=True)
            
            if category == "Structural visual organization" and category_problems:
                recommendations.append(
                    f"Improve layout structure by addressing {category_problems[0].get('name', 'alignment issues')}. "
                    "Consider using a grid system to create a more organized visual hierarchy."
                )
                
            elif category == "Visual perceptual complexity" and category_problems:
                recommendations.append(
                    f"Reduce visual complexity by simplifying {category_problems[0].get('name', 'visual elements')}. "
                    "Aim for a cleaner design with more whitespace and visual breathing room."
                )
                
            elif category == "Information load" and category_problems:
                recommendations.append(
                    "Reduce information density by prioritizing essential content and using progressive disclosure "
                    "techniques for secondary information."
                )
                
            elif category == "Cognitive load" and category_problems:
                recommendations.append(
                    "Minimize mental effort required by simplifying choices, using familiar patterns, "
                    "and providing clear guidance throughout the interface."
                )
        
        # Ensure we have enough recommendations
        if len(recommendations) < 3:
            recommendations.append(
                "Conduct usability testing with real users to validate these findings "
                "and discover additional improvement opportunities."
            )
        
        return recommendations
    
    def _extract_category_scores(self, analysis: Dict[str, Any]) -> Dict[str, int]:
        """
        Extract category scores from GPT analysis.
        
        Args:
            analysis: GPT analysis results
            
        Returns:
            Dictionary of category scores
        """
        category_scores = {}
        
        # Try to get scores from categoryScores
        category_scores_data = analysis.get("categoryScores", {})
        if category_scores_data:
            for category, score in category_scores_data.items():
                category_scores[category] = score
            return category_scores
        
        # If categoryScores is not available, calculate from problems
        problems = analysis.get("problems", [])
        category_problems = {}
        
        for problem in problems:
            category = problem.get("category", "Other")
            if category not in category_problems:
                category_problems[category] = []
            category_problems[category].append(problem)
        
        # Calculate average severity for each category
        for category, problems_list in category_problems.items():
            if problems_list:
                avg_severity = sum(p.get("severity", 0) for p in problems_list) / len(problems_list)
                category_scores[category] = round(avg_severity)
        
        return category_scores
    
    def _extract_top_issues(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract top issues from GPT analysis.
        
        Args:
            analysis: GPT analysis results
            
        Returns:
            List of top issues
        """
        problems = analysis.get("problems", [])
        
        # Sort problems by severity
        sorted_problems = sorted(problems, key=lambda x: x.get("severity", 0), reverse=True)
        
        # Return top 10 problems
        top_issues = []
        for problem in sorted_problems[:10]:
            top_issues.append({
                "name": problem.get("name", "Unnamed issue"),
                "description": problem.get("description", ""),
                "category": problem.get("category", "Other"),
                "severity": problem.get("severity", 0)
            })
        
        return top_issues

# For standalone testing
async def analyze_screenshot(screenshot_path: str, user_context: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyze a UI screenshot (standalone function for backward compatibility).
    
    Args:
        screenshot_path: Path to the screenshot
        user_context: Optional context about the interface
        
    Returns:
        Dictionary containing analysis results
    """
    analyzer = UIAnalyzer()
    return await analyzer.analyze_screenshot(screenshot_path, user_context)

# For testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python analyze_ui.py <screenshot_path> [context]")
        sys.exit(1)
    
    screenshot_path = sys.argv[1]
    user_context = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"Analyzing screenshot: {screenshot_path}")
    if user_context:
        print(f"Context: {user_context}")
    
    async def main():
        try:
            analyzer = UIAnalyzer()
            results = await analyzer.analyze_screenshot(screenshot_path, user_context)
            print(f"Analysis completed. Overall score: {results.get('overall_score')}/100")
            print(f"PDF report: {results.get('report_path')}")
        except Exception as e:
            print(f"Error during analysis: {e}")
            traceback.print_exc()
    
    asyncio.run(main()) 