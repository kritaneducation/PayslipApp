import os
import re
import queue
from dateutil import parser
import pdfplumber
import PyPDF2
import pytesseract

class PayslipProcessor:
    def __init__(self, cache_manager, log_callback=None, progress_callback=None):
        self.cache_manager = cache_manager
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.is_processing = False
        self.task_queue = queue.Queue()

    def extract_payment_date(self, pdf_path):
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text(x_tolerance=2, y_tolerance=2)
                    if text:
                        full_text += text + "\n"
                    else:
                        img = page.to_image(resolution=300).original.convert('L')
                        text = pytesseract.image_to_string(img, config='--oem 3 --psm 6')
                        full_text += text + "\n"
                date_patterns = [
                    r'Payment Date[:\s]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
                    r'Date of Payment[:\s]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
                    r'Pay Date[:\s]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
                    r'Pmt Date[:\s]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
                    r'Date Paid[:\s]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
                    r'Paid On[:\s]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
                    r'Issue Date[:\s]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
                    r'Salary Date[:\s]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
                    r'Payslip Date[:\s]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
                    r'Date[:\s]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
                ]
                for pattern in date_patterns:
                    date_match = re.search(pattern, full_text, re.IGNORECASE)
                    if date_match:
                        raw_date = date_match.group(1)
                        try:
                            return parser.parse(raw_date, dayfirst=True, fuzzy=True)
                        except Exception:
                            continue
                return None
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"Error processing {pdf_path}: {str(e)}")
            return None

    def process_payslips(self, input_dir, output_file):
        """Process all payslips in the input directory."""
        try:
            pdf_files = []
            # First, collect all PDF files
            for root, _, files in os.walk(input_dir):
                for file in files:
                    if file.lower().endswith('.pdf'):
                        pdf_files.append(os.path.join(root, file))
            
            if not pdf_files:
                if self.log_callback:
                    self.log_callback("No PDF files found in the input directory.", "Warning")
                return

            # Create temporary directory for split pages
            temp_dir = os.path.join(input_dir, "_temp_split_pages")
            os.makedirs(temp_dir, exist_ok=True)

            # Process each PDF and split if needed
            processed_files = []
            total_pdfs = len(pdf_files)
            for i, pdf_path in enumerate(pdf_files):
                if not self.is_processing:
                    break

                if self.log_callback:
                    self.log_callback(f"Processing {os.path.basename(pdf_path)}", "Info")

                # Split PDF if it has multiple pages
                split_pages = self.split_pdf_pages(pdf_path, temp_dir)
                processed_files.extend(split_pages)

                if self.progress_callback:
                    progress = ((i + 1) / total_pdfs) * 100
                    self.progress_callback(progress)

            # Sort files by payment date
            sorted_files = []
            for file in processed_files:
                payment_date = self.extract_payment_date(file)
                if payment_date:
                    sorted_files.append((payment_date, file))

            sorted_files.sort()  # Sort by payment date

            # Merge sorted files
            if sorted_files:
                self.merge_pdfs([f[1] for f in sorted_files], output_file)
                if self.log_callback:
                    self.log_callback(f"Successfully processed {len(sorted_files)} payslips", "Success")
            else:
                if self.log_callback:
                    self.log_callback("No valid payslips found to process", "Warning")

            # Cleanup temporary files
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)

        except Exception as e:
            if self.log_callback:
                self.log_callback(f"Error processing payslips: {str(e)}", "Error")
        self.is_processing = False

    def split_pdf_pages(self, pdf_path, output_dir):
        """Split a multi-page PDF into individual page PDFs."""
        try:
            with open(pdf_path, 'rb') as file:
                pdf = PyPDF2.PdfReader(file)
                num_pages = len(pdf.pages)
                
                # If single page, return original path
                if num_pages == 1:
                    return [pdf_path]
                
                # Create output directory for split pages
                pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
                split_dir = os.path.join(output_dir, f"{pdf_name}_pages")
                os.makedirs(split_dir, exist_ok=True)
                
                split_paths = []
                for page_num in range(num_pages):
                    output_path = os.path.join(split_dir, f"{pdf_name}_page_{page_num + 1}.pdf")
                    pdf_writer = PyPDF2.PdfWriter()
                    pdf_writer.add_page(pdf.pages[page_num])
                    
                    with open(output_path, 'wb') as output_file:
                        pdf_writer.write(output_file)
                    split_paths.append(output_path)
                    
                if self.log_callback:
                    self.log_callback(f"Split PDF into {num_pages} pages", "Info")
                return split_paths
                
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"Error splitting PDF: {str(e)}", "Error")
            return [pdf_path]  # Return original on error
