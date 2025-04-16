#!/usr/bin/env python3
import os
import json
import logging
import argparse
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
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

def load_coordinates(coordinates_file):
    """Load the coordinates data from JSON file"""
    logger.info(f"Loading coordinates from {coordinates_file}")
    try:
        with open(coordinates_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if "coordinates" not in data:
            raise ValueError("The coordinates file does not contain a 'coordinates' key")
        
        logger.info(f"Loaded {len(data['coordinates'])} coordinate sets")
        return data
    except Exception as e:
        logger.error(f"Failed to load coordinates: {e}")
        raise

def create_heatmap(coordinates_data, image_path, output_path, opacity=0.7, colormap="hot_r"):
    """Generate a heatmap overlay based on the coordinates and severity"""
    logger.info(f"Generating heatmap for image: {image_path}")
    
    try:
        # Open the original image
        original_img = Image.open(image_path)
        img_width, img_height = original_img.size
        
        # Create a heat map matrix
        heatmap = np.zeros((img_height, img_width), dtype=float)
        
        # Check if coordinates data has imageSize
        if "imageSize" in coordinates_data:
            coord_img_width = coordinates_data["imageSize"]["width"]
            coord_img_height = coordinates_data["imageSize"]["height"]
            
            # If image dimensions don't match the coordinates data, log a warning
            if img_width != coord_img_width or img_height != coord_img_height:
                logger.warning(f"Image dimensions ({img_width}x{img_height}) don't match coordinates data "
                              f"({coord_img_width}x{coord_img_height}). Will scale coordinates.")
                scale_x = img_width / coord_img_width
                scale_y = img_height / coord_img_height
            else:
                scale_x = scale_y = 1.0
        else:
            scale_x = scale_y = 1.0
            logger.warning("No imageSize in coordinates data, assuming 1:1 scale")
        
        # Extract coordinates and their severity
        valid_coords = 0
        for item in coordinates_data["coordinates"]:
            if "coords" in item and item["coords"] is not None:
                coords = item["coords"]
                severity = item.get("severity", 5)  # Default to medium severity if not provided
                
                # Scale coordinates if needed
                x1 = int(coords["x1"] * scale_x)
                y1 = int(coords["y1"] * scale_y)
                x2 = int(coords["x2"] * scale_x)
                y2 = int(coords["y2"] * scale_y)
                
                # Validate coordinates are within image bounds
                x1 = max(0, min(x1, img_width-1))
                y1 = max(0, min(y1, img_height-1))
                x2 = max(0, min(x2, img_width-1))
                y2 = max(0, min(y2, img_height-1))
                
                # Normalize severity to 0-1 range
                if isinstance(severity, (int, float)):
                    norm_severity = min(1.0, max(0.0, severity / 10.0))
                else:
                    norm_severity = 0.5  # Default if severity is not a number
                
                # Apply the heat to the region
                heatmap[y1:y2+1, x1:x2+1] = np.maximum(heatmap[y1:y2+1, x1:x2+1], norm_severity)
                valid_coords += 1
        
        logger.info(f"Applied {valid_coords} coordinates to heatmap")
        
        if valid_coords == 0:
            logger.warning("No valid coordinates found. Heatmap will be empty.")
        
        # Create a figure for plotting
        plt.figure(figsize=(img_width/100, img_height/100), dpi=100)
        plt.axis('off')
        
        # Display the original image
        plt.imshow(original_img)
        
        # Create a custom colormap with transparency
        colors = plt.cm.get_cmap(colormap)(np.linspace(0, 1, 256))
        colors[:, 3] = np.linspace(0, opacity, 256)  # Set alpha channel
        custom_cmap = LinearSegmentedColormap.from_list('custom_cmap', colors)
        
        # Overlay the heatmap
        plt.imshow(heatmap, cmap=custom_cmap, interpolation='bilinear')
        
        # Save the figure
        plt.tight_layout(pad=0)
        plt.savefig(output_path, bbox_inches='tight', pad_inches=0)
        plt.close()
        
        logger.info(f"Heatmap saved to {output_path}")
        return output_path
    
    except Exception as e:
        logger.error(f"Failed to generate heatmap: {e}", exc_info=True)
        raise

def main():
    parser = argparse.ArgumentParser(description="Generate heatmap from UI coordinates")
    parser.add_argument("--coordinates", required=True, help="Path to the coordinates JSON file")
    parser.add_argument("--screenshot", required=True, help="Path to the original screenshot")
    parser.add_argument("--output", required=True, help="Path to save the heatmap image")
    parser.add_argument("--opacity", type=float, default=0.7, help="Opacity of the heatmap overlay (0-1)")
    parser.add_argument("--colormap", default="hot_r", 
                        help="Matplotlib colormap to use (e.g., hot_r, inferno, YlOrRd)")
    
    args = parser.parse_args()
    
    try:
        # Validate paths
        if not os.path.exists(args.coordinates):
            logger.error(f"Coordinates file does not exist: {args.coordinates}")
            return 1
        
        if not os.path.exists(args.screenshot):
            logger.error(f"Screenshot does not exist: {args.screenshot}")
            return 1
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        
        # Load coordinates
        coordinates_data = load_coordinates(args.coordinates)
        
        # Generate heatmap
        create_heatmap(
            coordinates_data=coordinates_data,
            image_path=args.screenshot,
            output_path=args.output,
            opacity=args.opacity,
            colormap=args.colormap
        )
        
        logger.info("Heatmap generation completed successfully")
        return 0
    
    except Exception as e:
        logger.error(f"Heatmap generation failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main()) 