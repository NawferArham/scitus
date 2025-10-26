import frappe
from frappe.model.document import Document
from scitus.scitus.doctype.ocr_service import get_ocr_service

class LocationFinder(Document):
    def validate(self):
        if self.latitude and self.longitude:
            self.validate_coordinates()
    
    def validate_coordinates(self):
        try:
            lat = float(self.latitude)
            lon = float(self.longitude)
            
            if not (-90 <= lat <= 90):
                frappe.throw("Latitude must be between -90 and 90")
            if not (-180 <= lon <= 180):
                frappe.throw("Longitude must be between -180 and 180")
                
        except ValueError:
            frappe.throw("Latitude and Longitude must be valid numbers")

@frappe.whitelist()
def extract_coordinates_from_image(image_url):
    """
    Extract coordinates from uploaded image
    """
    try:
        ocr_service = get_ocr_service()
        result = ocr_service.extract_coordinates_from_image(image_url)
        return result
        
    except Exception as e:
        frappe.log_error(f"Location Finder OCR Error: {str(e)}")
        return {
            'success': False,
            'message': f'System error: {str(e)}'
        }