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
        self.is_processing = True
        pdf_files = []
        payment_dates = {}
        all_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.pdf')]
        total_files = len(all_files)
        if self.log_callback:
            self.log_callback(f"Found {total_files} PDF files to process")
        for idx, filename in enumerate(all_files):
            if not self.is_processing:
                if self.log_callback:
                    self.log_callback("Processing cancelled")
                break
            pdf_path = os.path.join(input_dir, filename)
            if self.log_callback:
                self.log_callback(f"Processing: {filename}")
            cache_key = self.cache_manager.get_file_hash(pdf_path)
            cached_date = self.cache_manager.date_cache.get(cache_key)
            if cached_date:
                payment_date = cached_date
                if self.log_callback:
                    self.log_callback(f"Using cached date for {filename}")
            else:
                payment_date = self.extract_payment_date(pdf_path)
                if payment_date:
                    self.cache_manager.date_cache[cache_key] = payment_date
            if payment_date:
                if payment_date in payment_dates:
                    existing_pdf = payment_dates[payment_date]
                    if self.log_callback:
                        self.log_callback(f"Duplicate date detected: {payment_date} in {filename}")
                    # For simplicity, keep the first one
                else:
                    payment_dates[payment_date] = pdf_path
                    pdf_files.append((pdf_path, payment_date))
                    if self.log_callback:
                        self.log_callback(f"✅ Valid date found in {filename}")
            else:
                if self.log_callback:
                    self.log_callback(f"⚠️ No valid date in {filename}")
            if self.progress_callback:
                progress = (idx + 1) / total_files * 100
                self.progress_callback(progress)
        self.cache_manager.save_cache()
        if self.is_processing and pdf_files:
            if self.log_callback:
                self.log_callback("🔃 Sorting files by payment date...")
            pdf_files.sort(key=lambda x: x[1])
            if self.log_callback:
                self.log_callback("🔄 Merging PDFs...")
            merger = PyPDF2.PdfMerger()
            for pdf_path, _ in pdf_files:
                merger.append(pdf_path)
            merger.write(output_file)
            merger.close()
            if self.log_callback:
                self.log_callback(f"✅ Successfully merged {len(pdf_files)} files")
                self.log_callback(f"Processed {len(pdf_files)} files\nOutput file: {output_file}")
        elif self.is_processing:
            if self.log_callback:
                self.log_callback("No valid PDFs found with payment dates")
        self.is_processing = False
