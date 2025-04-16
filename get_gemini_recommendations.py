#!/usr/bin/env python3
import os
import json
import logging
import argparse
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY not found in environment variables")
    raise ValueError("GEMINI_API_KEY is required")

genai.configure(api_key=GEMINI_API_KEY)

def load_prompt_template(file_path="prompts/recommendation_prompt.txt"):
    """Load the recommendation prompt template from a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.warning(f"Prompt template file not found: {file_path}")
        
        # Return a default prompt template if file doesn't exist
        return """You are a UX design expert. Based on the UI analysis provided, give 5-7 strategic recommendations 
to improve the interface. Focus on the most severe problems first and provide actionable suggestions.

Here is the UI analysis:
{analysis_json}"""

def load_gpt_analysis(analysis_file):
    """Load GPT analysis data from JSON file."""
    try:
        with open(analysis_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading GPT analysis file: {e}")
        raise

def get_recommendations(analysis_data, model_name="gemini-1.5-pro"):
    """Get strategic recommendations using Gemini."""
    logger.info("Generating strategic recommendations with Gemini")
    
    # Load prompt template
    prompt_template = load_prompt_template()
    
    # Insert analysis data into prompt
    analysis_json = json.dumps(analysis_data, indent=2)
    prompt = prompt_template.replace("{analysis_json}", analysis_json)
    
    try:
        # Generate recommendations with Gemini
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        
        # Process response
        recommendations = []
        text = response.text.strip()
        
        # Parse the numbered list format
        lines = text.split("\n")
        current_rec = None
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Check if this is a new recommendation number
            if line[0].isdigit() and "." in line[:5]:
                # Save previous recommendation if exists
                if current_rec:
                    recommendations.append(current_rec)
                
                # Start new recommendation
                title = line.split(".", 1)[1].strip()
                current_rec = {
                    "title": title,
                    "description": "",
                    "impact": "",
                    "priority": ""
                }
            elif current_rec:
                # Add content to current recommendation
                lower_line = line.lower()
                if "impact" in lower_line and ":" in line:
                    current_rec["impact"] = line.split(":", 1)[1].strip()
                elif "priority" in lower_line and ":" in line:
                    current_rec["priority"] = line.split(":", 1)[1].strip()
                else:
                    # If not a special field, add to description
                    if current_rec["description"]:
                        current_rec["description"] += " " + line
                    else:
                        current_rec["description"] = line
        
        # Add the last recommendation
        if current_rec:
            recommendations.append(current_rec)
        
        logger.info(f"Generated {len(recommendations)} recommendations")
        return recommendations
    
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        return [{"title": "Error generating recommendations", 
                 "description": f"An error occurred: {str(e)}",
                 "priority": "N/A"}]

def save_recommendations(recommendations, output_file):
    """Save recommendations to a JSON file."""
    try:
        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(recommendations, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Recommendations saved to: {output_file}")
        return True
    
    except Exception as e:
        logger.error(f"Error saving recommendations: {e}")
        return False

def main():
    """Main function to process command line arguments."""
    parser = argparse.ArgumentParser(description="Generate strategic recommendations using Gemini")
    parser.add_argument("--gpt-analysis", required=True, help="Path to GPT analysis JSON file")
    parser.add_argument("--output", required=True, help="Path to save recommendations JSON file")
    parser.add_argument("--model", default="gemini-1.5-pro", help="Gemini model to use")
    parser.add_argument("--prompt", help="Path to custom prompt template file")
    
    args = parser.parse_args()
    
    try:
        # Load analysis data
        analysis_data = load_gpt_analysis(args.gpt_analysis)
        
        # Get recommendations
        recommendations = get_recommendations(analysis_data, args.model)
        
        # Save recommendations
        success = save_recommendations(recommendations, args.output)
        
        if success:
            logger.info("Recommendations generated successfully")
            return 0
        else:
            logger.error("Failed to save recommendations")
            return 1
    
    except Exception as e:
        logger.error(f"Error in recommendation generation: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 