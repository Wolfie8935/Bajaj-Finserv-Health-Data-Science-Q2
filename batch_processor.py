import os
import json
import cv2
import pytesseract
import numpy as np
import re
import platform
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if platform.system() == 'Windows':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

INPUT_DIR = "lbmaske"
OUTPUT_DIR = "output"

def format_output(parsed_data):
    formatted_data = []
    for entry in parsed_data:
        formatted_data.append({
            "test_name": entry["test_name"],
            "test_value": entry["test_value"],
            "bio_reference_range": entry["bio_reference_range"],
            "test_unit": entry["test_unit"],
            "lab_test_out_of_range": entry["lab_test_out_of_range"]
        })
    return formatted_data

def extract_text_from_image(image_path):
    try:
        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"Failed to read image: {image_path}")
            return ""

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

        denoised = cv2.medianBlur(binary, 3)

        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(denoised, config=custom_config)
        
        logger.info(f"OCR extraction completed: {len(text)} characters extracted")
        return text
    except Exception as e:
        logger.error(f"Error in OCR extraction: {str(e)}", exc_info=True)
        return ""

def parse_lab_tests(text):
    lines = text.splitlines()
    results = []
    
    pattern = r"(.*?)[\s:]+([\d.]+)[\s]*([a-zA-Z%/]+)?[\s]*[\(]?([\d.]+-[\d.]+)?[\)]?"
    
    for line in lines:
        if not line.strip():
            continue
            
        match = re.match(pattern, line.strip())
        if match:
            name, value, unit, ref_range = match.groups()
            
            name = name.strip().upper() if name else ""
            value = value.strip() if value else ""
            unit = unit.strip() if unit else ""
            ref_range = ref_range.strip() if ref_range else ""
            
            if not name or not value:
                continue
                
            try:
                float_value = float(value)
                
                is_out_of_range = False
                if ref_range:
                    try:
                        low, high = map(float, ref_range.split('-'))
                        is_out_of_range = not (low <= float_value <= high)
                    except ValueError:
                        pass
                
                results.append({
                    "test_name": name,
                    "test_value": value,
                    "bio_reference_range": ref_range,
                    "test_unit": unit or "",
                    "lab_test_out_of_range": is_out_of_range
                })
            except ValueError:
                logger.warning(f"Skipped line due to invalid value: {line}")
                continue
                
    logger.info(f"Parsed {len(results)} lab tests from text")
    return results

def process_all_images():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if not os.path.exists(INPUT_DIR):
        logger.error(f"Input directory '{INPUT_DIR}' does not exist")
        return
        
    image_count = 0
    for file_name in os.listdir(INPUT_DIR):
        if file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp')):
            path = os.path.join(INPUT_DIR, file_name)
            logger.info(f"Processing: {file_name}")

            text = extract_text_from_image(path)
            
            parsed_data = parse_lab_tests(text)
            
            output_path = os.path.join(OUTPUT_DIR, os.path.splitext(file_name)[0] + ".json")
            with open(output_path, "w", encoding='utf-8') as f:
                json.dump(parsed_data, f, indent=4, ensure_ascii=False)
                
            logger.info(f"Saved results to: {output_path}")
            image_count += 1
            
    logger.info(f"Batch processing complete. Processed {image_count} images.")

if __name__ == "__main__":
    process_all_images()