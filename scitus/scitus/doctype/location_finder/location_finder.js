// location_finder.js
frappe.ui.form.on('Location Finder', {
    upload_image: function(frm) {
        if (frm.doc.upload_image) {
            extract_coordinates_from_image(frm);
        }
    },
    
    refresh: function(frm) {
        // Add debug button
        frm.add_custom_button(__('Debug OCR'), function() {
            if (frm.doc.upload_image) {
                extract_coordinates_from_image(frm, true);
            } else {
                frappe.msgprint(__('Please upload an image first.'));
            }
        });
    }
});

function extract_coordinates_from_image(frm, show_debug = false) {
    frappe.show_alert({
        message: __('Processing image with OCR...'),
        indicator: 'blue'
    });
    
    frappe.call({
        method: 'scitus.scitus.doctype.location_finder.location_finder.extract_coordinates_from_image',
        args: {
            'image_url': frm.doc.upload_image
        },
        callback: function(r) {
            if (r.message) {
                if (r.message.success) {
                    // Update the fields
                    frm.set_value('latitude', r.message.latitude);
                    frm.set_value('longitude', r.message.longitude);
                    
                    // Refresh fields
                    frm.refresh_field('latitude');
                    frm.refresh_field('longitude');
                    
                    let success_msg = __('✅ ' + r.message.message);
                    if (r.message.processing_time) {
                        success_msg += ` (${r.message.processing_time})`;
                    }
                    
                    frappe.show_alert({
                        message: success_msg,
                        indicator: 'green'
                    });
                    
                    // Show debug info if requested
                    if (show_debug && r.message.debug_text) {
                        frappe.msgprint({
                            title: __('OCR Debug Info'),
                            message: `
                                <p><strong>Extracted Text:</strong> ${r.message.debug_text}</p>
                                <p><strong>Processing Time:</strong> ${r.message.processing_time || 'N/A'}</p>
                            `
                        });
                    }
                } else {
                    let error_msg = r.message.message;
                    
                    // Show debug info if available
                    if (r.message.debug_text) {
                        error_msg += `<br><br><strong>Extracted Text:</strong> "${r.message.debug_text}"`;
                    }
                    
                    if (r.message.processing_time) {
                        error_msg += `<br><strong>Processing Time:</strong> ${r.message.processing_time}`;
                    }
                    
                    frappe.msgprint({
                        title: __('OCR Processing Result'),
                        indicator: 'red',
                        message: error_msg
                    });
                }
            }
        },
        error: function(err) {
            console.error('OCR Error:', err);
            frappe.msgprint({
                title: __('Error'),
                indicator: 'red',
                message: __('Failed to process image. Please check the error log.')
            });
        }
    });
}