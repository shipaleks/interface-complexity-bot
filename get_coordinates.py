#!/usr/bin/env python3
import os
import json
import argparse
import logging
import time
from typing import Dict, List, Any, Optional

import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY not found in environment variables")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)

def load_gpt_analysis(analysis_file: str) -> Dict[str, Any]:
    """
    Load the GPT analysis results from a JSON file.
    
    Args:
        analysis_file: Path to the GPT analysis JSON file
        
    Returns:
        Dictionary containing the GPT analysis data
    """
    try:
        with open(analysis_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading GPT analysis from {analysis_file}: {e}")
        raise

def extract_problems(analysis_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract problem descriptions from GPT analysis.
    
    Args:
        analysis_data: Dictionary containing GPT analysis data
        
    Returns:
        List of problems with their descriptions and severity
    """
    problems = []
    
    try:
        # Extract problems from each category
        categories = analysis_data.get("categories", [])
        for category in categories:
            category_name = category.get("name", "Unknown")
            category_problems = category.get("problems", [])
            
            for problem in category_problems:
                problem_data = {
                    "category": category_name,
                    "name": problem.get("name", "Unknown"),
                    "description": problem.get("description", ""),
                    "severity": problem.get("severity", 50),
                    "recommendations": problem.get("recommendations", [])
                }
                problems.append(problem_data)
        
        # Sort problems by severity (descending)
        problems.sort(key=lambda x: x.get("severity", 0), reverse=True)
        
        # Limit to top 30 most severe problems if there are more
        return problems[:30] if len(problems) > 30 else problems
    
    except Exception as e:
        logger.error(f"Error extracting problems from analysis data: {e}")
        return []

def get_coordinates_from_gemini(image_path: str, problems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Get coordinates for UI problems using Gemini Vision.
    
    Args:
        image_path: Path to the UI screenshot
        problems: List of problems extracted from GPT analysis
        
    Returns:
        List of problems with added coordinates
    """
    try:
        # Load image
        image = Image.open(image_path)
        width, height = image.size
        
        # Initialize Gemini Pro Vision model
        model = genai.GenerativeModel('gemini-pro-vision')
        
        # Prepare prompt template
        prompt_template = """
        You are a UI analysis expert. I need you to identify the exact coordinates of UI problems in this screenshot.
        
        For each problem, provide the x1, y1, x2, y2 coordinates (in pixels) that define a bounding box around the problematic area.
        The coordinates should be relative to the image size ({width}x{height} pixels).
        
        Coordinates format:
        - x1, y1: top-left corner of the bounding box
        - x2, y2: bottom-right corner of the bounding box
        
        For each problem, provide the coordinates that best capture the affected UI elements.
        
        Problems to identify:
        {problems_text}
        
        Respond in JSON format as follows:
        {{
          "coordinates": [
            {{
              "problem_index": 1,
              "problem_name": "Problem name",
              "category": "Category name",
              "severity": severity_value,
              "x1": x1_value,
              "y1": y1_value,
              "x2": x2_value,
              "y2": y2_value
            }},
            ...
          ]
        }}
        
        Only include the JSON in your response, no other text.
        """
        
        # Process problems in batches of 5 to avoid context length issues
        batch_size = 5
        problem_batches = [problems[i:i+batch_size] for i in range(0, len(problems), batch_size)]
        
        all_coordinates = []
        for batch_index, problem_batch in enumerate(problem_batches):
            # Create problem text for this batch
            problems_text = ""
            for i, problem in enumerate(problem_batch, 1):
                problems_text += f"{i}. {problem['name']} (Category: {problem['category']}, Severity: {problem['severity']}/100): {problem['description']}\n\n"
            
            # Format prompt with image dimensions and problems
            prompt = prompt_template.format(
                width=width,
                height=height,
                problems_text=problems_text
            )
            
            # Get response from Gemini
            logger.info(f"Sending batch {batch_index+1}/{len(problem_batches)} to Gemini")
            response = model.generate_content([prompt, image])
            
            try:
                # Extract JSON from response
                response_text = response.text
                
                # Look for JSON content
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx > start_idx:
                    json_text = response_text[start_idx:end_idx]
                    batch_coordinates = json.loads(json_text).get("coordinates", [])
                    
                    # Adjust problem indices to be global across all batches
                    global_offset = batch_index * batch_size
                    for coord in batch_coordinates:
                        if "problem_index" in coord:
                            coord["problem_index"] += global_offset
                        
                        # Link back to the original problem data
                        problem_idx = coord.get("problem_index", 0) - 1
                        if 0 <= problem_idx < len(problems):
                            orig_problem = problems[problem_idx]
                            coord["problem_name"] = orig_problem.get("name", "Unknown")
                            coord["category"] = orig_problem.get("category", "Unknown")
                            coord["severity"] = orig_problem.get("severity", 50)
                    
                    all_coordinates.extend(batch_coordinates)
                else:
                    logger.warning(f"Failed to extract JSON from Gemini response for batch {batch_index+1}")
            
            except Exception as e:
                logger.error(f"Error processing Gemini response for batch {batch_index+1}: {e}")
            
            # Sleep briefly to avoid rate limits
            if batch_index < len(problem_batches) - 1:
                time.sleep(2)
        
        return all_coordinates
    
    except Exception as e:
        logger.error(f"Error getting coordinates from Gemini: {e}")
        return []

def save_coordinates(coordinates: List[Dict[str, Any]], output_file: str) -> None:
    """
    Save coordinates to a JSON file.
    
    Args:
        coordinates: List of problems with coordinates
        output_file: Path to save the coordinates JSON file
    """
    try:
        with open(output_file, 'w') as f:
            json.dump({"coordinates": coordinates}, f, indent=2)
        logger.info(f"Coordinates saved to {output_file}")
    except Exception as e:
        logger.error(f"Error saving coordinates to {output_file}: {e}")
        raise

def main() -> int:
    """Main function to extract problem coordinates."""
    parser = argparse.ArgumentParser(description="Extract UI problem coordinates using Gemini Vision")
    parser.add_argument("--gpt-analysis", required=True, help="Path to GPT analysis JSON file")
    parser.add_argument("--image", required=True, help="Path to UI screenshot")
    parser.add_argument("--output", required=True, help="Path to save coordinates JSON file")
    args = parser.parse_args()
    
    try:
        # Load GPT analysis
        logger.info(f"Loading GPT analysis from {args.gpt_analysis}")
        analysis_data = load_gpt_analysis(args.gpt_analysis)
        
        # Extract problems
        logger.info("Extracting problems from GPT analysis")
        problems = extract_problems(analysis_data)
        logger.info(f"Extracted {len(problems)} problems from GPT analysis")
        
        # Get coordinates from Gemini
        logger.info(f"Getting coordinates for problems using Gemini Vision")
        coordinates = get_coordinates_from_gemini(args.image, problems)
        logger.info(f"Got coordinates for {len(coordinates)} problems")
        
        # Save coordinates
        logger.info(f"Saving coordinates to {args.output}")
        save_coordinates(coordinates, args.output)
        
        logger.info("Coordinate extraction completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Error extracting coordinates: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 