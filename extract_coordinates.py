#!/usr/bin/env python3
import os
import json
import base64
import logging
import argparse
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def configure_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-pro-vision')

def load_prompt_template(template_path="prompt_templates/coordinate_extraction.txt"):
    if not os.path.exists(template_path):
        logger.warning(f"Prompt template not found at {template_path}, using default prompt")
        return """
        You are an expert in UI analysis. I need you to identify all UI elements in this screenshot and provide their coordinates.
        
        For each problem area identified in the json data, find the corresponding UI element in the image and provide its coordinates.
        
        Analyze the image and return a JSON object with the following structure:
        {
            "coordinates": [
                {
                    "problemId": "unique_id_from_json",
                    "problemName": "name_of_problem",
                    "category": "category_name",
                    "severity": severity_score,
                    "coords": {
                        "x1": top_left_x,
                        "y1": top_left_y,
                        "x2": bottom_right_x,
                        "y2": bottom_right_y
                    }
                },
                ...
            ],
            "imageSize": {
                "width": image_width,
                "height": image_height
            }
        }
        
        Notes:
        - Coordinates should be in pixels
        - x1,y1 is top-left corner and x2,y2 is bottom-right corner
        - Each coordinate should correspond to a specific problem from the input JSON
        - If you can't find a UI element for a problem, set coords to null
        """
    
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

def extract_coordinates(model, image_path, gpt_analysis_path, prompt_template):
    logger.info(f"Extracting coordinates from image: {image_path}")
    
    # Load the GPT analysis
    try:
        with open(gpt_analysis_path, "r", encoding="utf-8") as f:
            gpt_analysis = json.load(f)
            logger.info(f"Loaded GPT analysis with {len(gpt_analysis.get('categories', []))} categories")
    except Exception as e:
        logger.error(f"Failed to load GPT analysis: {e}")
        raise
    
    # Load and get image dimensions
    try:
        img = Image.open(image_path)
        img_width, img_height = img.size
        logger.info(f"Image dimensions: {img_width}x{img_height}")
    except Exception as e:
        logger.error(f"Failed to load image: {e}")
        raise
    
    # Prepare prompt with GPT analysis JSON
    formatted_prompt = prompt_template + f"\n\nHere is the JSON data from GPT analysis:\n{json.dumps(gpt_analysis, indent=2)}"
    
    try:
        # Request the coordinates from Gemini
        logger.info("Sending request to Gemini API")
        response = model.generate_content([formatted_prompt, img])
        
        # Process the response
        response_text = response.text
        
        # Extract JSON from response
        import re
        json_match = re.search(r'```json\n(.*?)```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find any JSON-like structure
            json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response_text
        
        # Try to parse the JSON
        try:
            coordinate_data = json.loads(json_str)
            
            # Add image dimensions if not present
            if "imageSize" not in coordinate_data:
                coordinate_data["imageSize"] = {
                    "width": img_width,
                    "height": img_height
                }
            
            # Add metadata
            coordinate_data["meta"] = {
                "timestamp": datetime.now().isoformat(),
                "model": "gemini-pro-vision",
                "version": "1.0"
            }
            
            return coordinate_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response as JSON: {e}")
            logger.debug(f"Raw response: {response_text}")
            raise ValueError("Response could not be parsed as JSON") from e
            
    except Exception as e:
        logger.error(f"Gemini API request failed: {e}")
        raise

def save_coordinates(coordinates_data, output_path):
    logger.info(f"Saving coordinates to {output_path}")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Save to file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(coordinates_data, f, indent=2, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser(description="Extract UI element coordinates with Gemini")
    parser.add_argument("--screenshot", required=True, help="Path to the UI screenshot")
    parser.add_argument("--gpt-analysis", required=True, help="Path to the GPT analysis JSON")
    parser.add_argument("--output", required=True, help="Path to save the coordinates JSON")
    parser.add_argument("--prompt", help="Path to the prompt template file")
    
    args = parser.parse_args()
    
    try:
        # Validate paths
        if not os.path.exists(args.screenshot):
            logger.error(f"Screenshot does not exist: {args.screenshot}")
            return 1
        
        if not os.path.exists(args.gpt_analysis):
            logger.error(f"GPT analysis does not exist: {args.gpt_analysis}")
            return 1
        
        # Configure Gemini
        model = configure_gemini()
        
        # Load the prompt template
        prompt_path = args.prompt if args.prompt else "prompt_templates/coordinate_extraction.txt"
        prompt_template = load_prompt_template(prompt_path)
        
        # Extract coordinates
        coordinates_data = extract_coordinates(model, args.screenshot, args.gpt_analysis, prompt_template)
        
        # Save the coordinates
        save_coordinates(coordinates_data, args.output)
        
        logger.info("Coordinate extraction completed successfully")
        logger.info(f"Found coordinates for {len(coordinates_data.get('coordinates', []))} UI elements")
        return 0
        
    except Exception as e:
        logger.error(f"Coordinate extraction failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main()) 