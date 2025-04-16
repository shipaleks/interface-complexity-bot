#!/usr/bin/env python3
import os
import json
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GPT_MODEL = "gpt-4-turbo-preview"  # For GPT-4.1, adjust if you have a specific model name

def encode_image_to_base64(image_path):
    """Encode an image to base64 string"""
    import base64
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_interface(image_path, context=None):
    """Analyze a UI screenshot using OpenAI's GPT-4 with vision capabilities"""
    logger.info(f"Analyzing interface image: {image_path}")
    
    # Initialize OpenAI client
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    # Encode the image
    base64_image = encode_image_to_base64(image_path)
    
    # Prepare system prompt
    system_prompt = """You are UIAnalyst, an expert system for analyzing user interface complexity.
    Analyze the provided UI screenshot. Evaluate it based on these six complexity categories:
    
    1. Structural Visual Organization: Layout, alignment, grouping, and visual hierarchy
    2. Visual Perceptual Complexity: Colors, contrast, density, white space
    3. Typographic Complexity: Text readability, font choices, text formatting
    4. Information Load: Amount of information, density of UI elements, choices available
    5. Cognitive Load: Mental effort required, learnability, memorability
    6. Operational Complexity: Interaction patterns, required steps, feedback mechanisms
    
    For each category:
    - Identify specific problems
    - Rate the severity of each problem on a scale from 1-10
    - Explain why it's a problem 
    - Suggest a specific design improvement
    
    Provide an overall complexity score on a scale from 0-100, where 0 is extremely simple and 100 is extremely complex.
    
    Ensure your output is valid JSON with this structure:
    {
      "overallScore": {
        "score": <0-100>,
        "interpretation": "<interpretation of the overall score>"
      },
      "categories": [
        {
          "name": "<category name>",
          "description": "<category description>",
          "score": <0-10>,
          "problems": [
            {
              "name": "<problem name>",
              "description": "<problem description>",
              "severity": <1-10>,
              "impact": "<impact on users>",
              "improvement": "<suggestion for improvement>"
            }
          ]
        }
      ]
    }
    """
    
    # Prepare user prompt
    user_prompt = "Analyze this user interface for complexity issues and provide a detailed breakdown."
    if context:
        user_prompt += f" Context about the interface: {context}"
    
    # Prepare messages
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user", 
            "content": [
                {"type": "text", "text": user_prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "high"
                    }
                }
            ]
        }
    ]
    
    # Call the API
    try:
        logger.info("Sending request to OpenAI API...")
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=4000,
        )
        
        # Extract and parse JSON content
        response_content = response.choices[0].message.content
        result = json.loads(response_content)
        logger.info("Successfully analyzed the interface")
        return result
    
    except Exception as e:
        logger.error(f"Error during OpenAI API call: {e}")
        raise

def main():
    """Main function to handle command line arguments and run the analysis"""
    parser = argparse.ArgumentParser(description="Analyze UI complexity from a screenshot")
    parser.add_argument("--image", type=str, required=True, help="Path to the UI screenshot")
    parser.add_argument("--output", type=str, required=True, help="Path to save the analysis results (JSON)")
    parser.add_argument("--context", type=str, help="Optional context about the interface")
    
    args = parser.parse_args()
    
    try:
        # Validate input file
        if not os.path.exists(args.image):
            logger.error(f"Input image not found: {args.image}")
            return 1
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(args.output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Analyze the interface
        analysis_result = analyze_interface(args.image, args.context)
        
        # Save the result
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Analysis saved to {args.output}")
        return 0
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 