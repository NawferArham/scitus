import frappe
import os
import re
import traceback
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import io
import pytesseract
from frappe.utils import get_site_path
import time

class OCRService:
    def __init__(self):
        self.supported_formats = ['png', 'jpg', 'jpeg', 'gif', 'bmp']
        self.coordinate_patterns = self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile all regex patterns for better performance"""
        return [
            # Main patterns
            re.compile(r'Lat\s*:\s*([+-]?\d+\.\d+)\s*,\s*Lon\s*:\s*([+-]?\d+\.\d+)', re.IGNORECASE),
            re.compile(r'lat\s*:\s*([+-]?\d+\.\d+)\s*,\s*lon\s*:\s*([+-]?\d+\.\d+)', re.IGNORECASE),
            re.compile(r'LAT\s*:\s*([+-]?\d+\.\d+)\s*,\s*LON\s*:\s*([+-]?\d+\.\d+)', re.IGNORECASE),
            
            # Variations with different spacing
            re.compile(r'Lat\s*:\s*([+-]?\d+\.\d+)\s*,?\s*Lon\s*:\s*([+-]?\d+\.\d+)', re.IGNORECASE),
            re.compile(r'Latitude\s*:\s*([+-]?\d+\.\d+)\s*,?\s*Longitude\s*:\s*([+-]?\d+\.\d+)', re.IGNORECASE),
            
            # General coordinate patterns
            re.compile(r'([+-]?\d+\.\d+)\s*,\s*([+-]?\d+\.\d+)'),
            re.compile(r'\(?\s*([+-]?\d+\.\d+)\s*,\s*([+-]?\d+\.\d+)\s*\)?'),
            
            # Patterns with different separators
            re.compile(r'Lat\s*[=:]\s*([+-]?\d+\.\d+)\s*[,;]\s*Lon\s*[=:]\s*([+-]?\d+\.\d+)', re.IGNORECASE),
        ]
    
    def extract_coordinates_from_image(self, image_path):
        """
        Extract coordinates from image using reliable OCR
        """
        start_time = time.time()
        try:
            frappe.log_error(f"Starting reliable OCR for: {image_path}")
            
            file_path = self.get_file_path(image_path)
            
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'message': f'File not found at path: {file_path}'
                }
            
            with open(file_path, 'rb') as f:
                image_data = f.read()
            
            # Use reliable OCR approach
            text_results = self.perform_reliable_ocr(image_data)
            
            processing_time = time.time() - start_time
            frappe.log_error(f"Reliable OCR completed in {processing_time:.2f}s")
            
            # Try each text result for coordinates
            coordinates = None
            best_text = ""
            
            for text in text_results:
                if not text:
                    continue
                    
                current_coords = self.extract_coordinates(text)
                if current_coords:
                    coordinates = current_coords
                    best_text = text
                    break
            
            if coordinates:
                safe_text = best_text[:100] + "..." if len(best_text) > 100 else best_text
                return {
                    'success': True,
                    'latitude': coordinates['latitude'],
                    'longitude': coordinates['longitude'],
                    'message': f"Found coordinates: Lat {coordinates['latitude']}, Lon {coordinates['longitude']}",
                    'processing_time': f"{processing_time:.2f}s",
                    'debug_text': safe_text
                }
            else:
                # Show all extracted texts for debugging
                all_text = " | ".join([t[:50] for t in text_results if t])
                safe_text = all_text[:200] + "..." if len(all_text) > 200 else all_text
                
                return {
                    'success': False,
                    'message': 'No coordinates found in the extracted text',
                    'debug_text': safe_text,
                    'processing_time': f"{processing_time:.2f}s"
                }
            
        except Exception as e:
            error_msg = f"OCR Error: {str(e)}\n{traceback.format_exc()}"
            frappe.log_error(error_msg)
            return {
                'success': False,
                'message': f'OCR Processing Error: {str(e)}'
            }
    
    def get_file_path(self, file_url):
        """Convert file URL to absolute path"""
        if not file_url:
            return None
            
        file_url = file_url.strip()
        
        if file_url.startswith('/private/files/'):
            filename = file_url.split('/')[-1]
            return get_site_path('private', 'files', filename)
        elif file_url.startswith('/files/'):
            filename = file_url.split('/')[-1]
            return get_site_path('public', 'files', filename)
        elif file_url.startswith('private/files/'):
            filename = file_url.split('/')[-1]
            return get_site_path('private', 'files', filename)
        elif file_url.startswith('files/'):
            filename = file_url.split('/')[-1]
            return get_site_path('public', 'files', filename)
        else:
            return get_site_path('public', 'files', file_url)
    
    def perform_reliable_ocr(self, image_data):
        """
        Simple but reliable OCR with multiple approaches
        """
        text_results = []
        
        try:
            original_image = Image.open(io.BytesIO(image_data))
            
            # Strategy 1: Simple grayscale with contrast
            text1 = self.simple_grayscale_ocr(original_image)
            if text1:
                text_results.append(text1)
            
            # Strategy 2: High contrast version
            text2 = self.high_contrast_ocr(original_image)
            if text2:
                text_results.append(text2)
            
            # Strategy 3: Inverted colors
            text3 = self.inverted_ocr(original_image)
            if text3:
                text_results.append(text3)
            
            # Strategy 4: Resized version for small text
            text4 = self.resized_ocr(original_image)
            if text4:
                text_results.append(text4)
            
            # Remove duplicates
            unique_texts = []
            seen = set()
            for text in text_results:
                if text and text not in seen:
                    unique_texts.append(text)
                    seen.add(text)
            
            frappe.log_error(f"Found {len(unique_texts)} unique text results")
            return unique_texts
            
        except Exception as e:
            frappe.log_error(f"Reliable OCR failed: {str(e)}")
            return text_results
    
    def simple_grayscale_ocr(self, image):
        """Simple grayscale OCR"""
        try:
            gray = image.convert('L')
            config = '--oem 3 --psm 6'
            return pytesseract.image_to_string(gray, config=config).strip()
        except:
            return ""
    
    def high_contrast_ocr(self, image):
        """High contrast OCR"""
        try:
            gray = image.convert('L')
            enhancer = ImageEnhance.Contrast(gray)
            high_contrast = enhancer.enhance(3.0)
            config = '--oem 3 --psm 7'
            return pytesseract.image_to_string(high_contrast, config=config).strip()
        except:
            return ""
    
    def inverted_ocr(self, image):
        """Inverted colors OCR"""
        try:
            gray = image.convert('L')
            inverted = ImageOps.invert(gray)
            config = '--oem 3 --psm 8'
            return pytesseract.image_to_string(inverted, config=config).strip()
        except:
            return ""
    
    def resized_ocr(self, image):
        """Resized OCR for small text"""
        try:
            # Resize if image is small
            if image.size[0] < 500:
                scale = 2.0
                new_size = (int(image.size[0] * scale), int(image.size[1] * scale))
                resized = image.resize(new_size, Image.LANCZOS)
            else:
                resized = image
            
            gray = resized.convert('L')
            enhancer = ImageEnhance.Contrast(gray)
            enhanced = enhancer.enhance(2.0)
            
            config = '--oem 3 --psm 6'
            return pytesseract.image_to_string(enhanced, config=config).strip()
        except:
            return ""
    
    def extract_coordinates(self, text):
        """
        Extract coordinates from text
        """
        if not text:
            return None
        
        text = re.sub(r'\s+', ' ', text).strip()
        
        for pattern in self.coordinate_patterns:
            matches = pattern.findall(text)
            if matches:
                for match in matches:
                    try:
                        lat, lon = match
                        lat_val = float(lat)
                        lon_val = float(lon)
                        
                        if self.is_valid_coordinate(lat_val, lon_val):
                            return {
                                'latitude': lat_val,
                                'longitude': lon_val
                            }
                    except (ValueError, TypeError):
                        continue
        
        return self.fallback_coordinate_search(text)
    
    def fallback_coordinate_search(self, text):
        """
        Simple fallback coordinate search
        """
        try:
            numbers = re.findall(r'[+-]?\d+\.\d+', text)
            
            if len(numbers) >= 2:
                for i in range(len(numbers) - 1):
                    try:
                        lat = float(numbers[i])
                        lon = float(numbers[i + 1])
                        
                        if self.is_valid_coordinate(lat, lon):
                            return {
                                'latitude': lat,
                                'longitude': lon
                            }
                    except (ValueError, TypeError):
                        continue
            
            return None
            
        except Exception:
            return None
    
    def is_valid_coordinate(self, lat, lon):
        """
        Validate coordinate ranges
        """
        return (-90 <= lat <= 90) and (-180 <= lon <= 180)

def get_ocr_service():
    return OCRService()