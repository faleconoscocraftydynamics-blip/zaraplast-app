from pathlib import Path
import io
import base64
from pdf2image import convert_from_path
from openai import OpenAI

client = OpenAI(api_key="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")


def encode_image(image):
    """Convert PIL image to base64 for GPT Vision."""
    img_bytes = io.BytesIO()
    image.save(img_bytes, format="PNG")
    return base64.b64encode(img_bytes.getvalue()).decode("utf-8")

def build_prompt():
    return """
You are a product extraction agent.

Your task

1. Read the document.
2. Extract ALL product details:
    - Product name
    - SKU / product code
    - Quantity
    - Price
    - Description
    - Attributes (size, color, weight, etc)
    - Billing Address

3. Extract ALL document metadata *if present*, including:
    - Billing address
    - Shipping address
    - Supplier address
    - Supplier name
    - Customer name
    - Customer addrss
    - Document number
    - Issue data
    - Any header or footer fields

Return the result in JSON:

{
  "metadata": {
    "billing_address": "",
    "shipping_address": "",
    "supplier_name": "",
    "supplier_address": "",
    "customer_name": "",
    "customer_address": "",
    "document_number": "",
    "issue_date": ""
  },
  "products": [
    {
      "name": "",
      "sku": "",
      "quantity": "",
      "price": "",
      "description": "",
      "attributes": {}
    }
  ]
}

If information is missing, return an empty string

Here is an example of output:

{
  "metadata": {
    "billing_address": "",
    "shipping_address": "",
    "supplier_name": "Nestlé Brasil Ltda.",
    "supplier_address": "Avenida das Nações Unidas, São Paulo – Brasil",
    "customer_name": "",
    "customer_address": "",
    "document_number": "",
    "issue_date": ""
  },
  "products": [
    {
      "name": "Creme de Leite Nestlé",
      "sku": "",
      "quantity": "300 g",
      "price": "",
      "description": "Creme de leite tradicional para uso culinário.",
      "attributes": {
        "brand": "Nestlé",
        "package_type": "Lata",
        "weight": "300 g",
        "allergens": "Contém leite",
        "nutritional_info": {
          "porção": "50 g (3 colheres de sopa)",
          "energia": "85 kcal",
          "carboidratos": "2.9 g",
          "proteínas": "1.1 g",
          "gorduras_totais": "7.8 g",
          "gorduras_saturadas": "4.8 g",
          "gorduras_trans": "0 g",
          "sódio": "18 mg"
        }
      }
    }
  ]
}

"""



def extract_text_from_pdf(pdf_path: str):
    pdf_path = Path(pdf_path)
    methods_used = []
    text = ""
    prompt = build_prompt()

    # ----------------------------------------------------------------------
    # 1) Try PDFPLUMBER (best for clean digital PDFs)
    # ----------------------------------------------------------------------
    try:
        import pdfplumber
        with pdfplumber.open(str(pdf_path)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]

        text = "\n\n".join(pages).strip()

        response = client.responses.create(
            model="gpt-4.1",
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt
                        },
                        {
                            "type": "input_text",
                            "text": text
                        }
                    ]
                }
            ]
        )
        page_text = response.output_text.strip()

        print("plumber >>>", page_text)

        if text:
            print(">>> Extracted using PDFPlumber")
            methods_used.append("pdfplumber")
            return page_text, methods_used
    except Exception as e:
        print(">>> pdfplumber error:", e)

    # ----------------------------------------------------------------------
    # 2) Try PyPDF2 (secondary digital PDF extractor)
    # ----------------------------------------------------------------------
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(str(pdf_path))
        pages = [p.extract_text() or "" for p in reader.pages]

        text = "\n\n".join(pages).strip()
        if text:
            print(">>> Extracted using PyPDF2")
            methods_used.append("PyPDF2")
            return text, methods_used
    except Exception as e:
        print(">>> PyPDF2 error:", e)

    # ----------------------------------------------------------------------
    # 3) GPT-4.1 Vision OCR (BEST fallback for scanned PDFs)
    # ----------------------------------------------------------------------
    print(">>> No text found → Using GPT-4.1 Vision OCR...")
    methods_used.append("GPT-4.1-Vision")

    try:
        images = convert_from_path(str(pdf_path), dpi=200, poppler_path=r"C:\poppler-25.11.0\Library\bin")
    except Exception as e:
        print(">>> ERROR converting PDF to images:", e)
        return "", methods_used

    gpt_results = []

    for idx, img in enumerate(images):
        print(f">>> Processing page {idx+1}/{len(images)} with GPT-4.1 Vision...")

        img_b64 = encode_image(img)

        response = client.responses.create(
            model="gpt-4.1",
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/png;base64,{img_b64}"
                        }
                    ]
                }
            ]
        )

        page_text = response.output_text.strip()
        gpt_results.append(page_text)

    final_text = "\n\n".join(gpt_results).strip()
    return final_text, methods_used

#print(extract_text_from_pdf(r"C:\Users\christian\Downloads\Especif_GreenPharma.pdf"))


# from pathlib import Path
# import boto3
# import time
# import io


# # ===== TEXTRACT ASYNC HELPERS =====

# def start_textract_job(bucket, key):
#     textract = boto3.client("textract")
#     response = textract.start_document_analysis(
#         DocumentLocation={"S3Object": {"Bucket": bucket, "Name": key}},
#         FeatureTypes=["TABLES", "FORMS"]
#     )
#     return response["JobId"]


# def is_job_complete(job_id):
#     textract = boto3.client("textract")
#     response = textract.get_document_analysis(JobId=job_id)
#     status = response["JobStatus"]
#     return status in ["SUCCEEDED", "FAILED"]


# def get_job_results(job_id):
#     textract = boto3.client("textract")
#     pages = []

#     response = textract.get_document_analysis(JobId=job_id)
#     pages.append(response)

#     # If document has multiple pages, fetch pagination token
#     next_token = response.get("NextToken")

#     while next_token:
#         response = textract.get_document_analysis(JobId=job_id, NextToken=next_token)
#         pages.append(response)
#         next_token = response.get("NextToken")

#     return pages


# # ===== MAIN EXTRACTOR =====

# def extract_text_from_pdf(pdf_path: str, s3_bucket="apllos-zarplast-poc", s3_prefix="general-docs/"):
#     pdf_path = Path(pdf_path)
#     s3 = boto3.client("s3")

#     # ---- Step 1: upload PDF to S3 ----
#     s3_key = f"{s3_prefix}{pdf_path.name}"

#     print(f">>> Uploading {pdf_path.name} to s3://{s3_bucket}/{s3_key}")
#     s3.upload_file(str(pdf_path), s3_bucket, s3_key)

#     # ---- Step 2: Start Textract async job ----
#     print(">>> Starting Textract async job...")
#     job_id = start_textract_job(s3_bucket, s3_key)
#     print(f">>> Job started with ID: {job_id}")

#     # ---- Step 3: Poll until completion ----
#     print(">>> Waiting for Textract to finish...")
#     while not is_job_complete(job_id):
#         print("    - Still processing...")
#         time.sleep(3)

#     print(">>> Textract job completed!")

#     # ---- Step 4: Retrieve results ----
#     pages = get_job_results(job_id)

#     # ---- Step 5: Extract lines of text ----
#     text_lines = []
#     for page in pages:
#         for block in page["Blocks"]:
#             if block["BlockType"] == "LINE":
#                 text_lines.append(block["Text"])

#     text = "\n".join(text_lines).strip()
#     methods_used = ["AWS_Textract_Async"]

#     return text, methods_used

# text, methods = extract_text_from_pdf(
#     r"C:\Users\christian\Downloads\Especif_Nestle1.pdf")
#     #s3_bucket="zaraplast-textract-pdf",
#     #s3_prefix="incoming/"
# #)


### TEXTRACT WITHOUT STRUCTURE
# from pathlib import Path
# import boto3
# import io

# def extract_text_from_pdf(pdf_path: str):
#     pdf_path = Path(pdf_path)
#     text = ""
#     methods_used = []

#     # 1) Try pdfplumber (fast + handles digital PDFs)
#     try:
#         import pdfplumber
#         with pdfplumber.open(str(pdf_path)) as pdf:
#             pages = [p.extract_text() or "" for p in pdf.pages]
#         text = "\n\n".join(pages).strip()
#         if text:
#             methods_used.append("pdfplumber")
#             return text, methods_used
#     except Exception as e:
#         print(">>> pdfplumber error:", e)

#     # 2) Try PyPDF2
#     try:
#         import PyPDF2
#         reader = PyPDF2.PdfReader(str(pdf_path))
#         pages = [p.extract_text() or "" for p in reader.pages]
#         text = "\n\n".join(pages).strip()
#         if text:
#             methods_used.append("PyPDF2")
#             return text, methods_used
#     except Exception as e:
#         print(">>> PyPDF2 error:", e)

#     # 3) AWS TEXTRACT (best OCR for scans/invoices)
#     try:
#         print(">>> Running AWS Textract OCR...")

#         client = boto3.client("textract")

#         with open(pdf_path, "rb") as f:
#             content = f.read()

#         response = client.analyze_document(
#             Document={"Bytes": content},
#             FeatureTypes=["TABLES", "FORMS"]
#         )

#         extracted_lines = []

#         for block in response.get("Blocks", []):
#             if block["BlockType"] == "LINE":
#                 extracted_lines.append(block.get("Text", ""))

#         text = "\n".join(extracted_lines).strip()

#         if text:
#             methods_used.append("AWS_Textract")
#             return text, methods_used

#     except Exception as e:
#         print(">>> TEXTRACT ERROR:", e)

#     # 4) Fallback raw extraction (last resort)
#     try:
#         print(">>> Raw bytes fallback")
#         raw = pdf_path.read_bytes()
#         import re
#         segs = re.findall(rb'[\x20-\x7E]{30,}', raw)
#         segs = [s.decode("latin-1") for s in segs[:10]]
#         text = "\n\n".join(segs).strip()
#         if text:
#             methods_used.append("raw-bytes")
#             return text, methods_used
#     except Exception as e:
#         print("raw fallback error:", e)

#     return text, methods_used


#### GOOGLE VISION ####
# from pathlib import Path
# import io
# import os

# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\google\vision-key.json"

# from google.cloud import vision
# client = vision.ImageAnnotatorClient()

# def extract_text_from_pdf(pdf_path: str):
#     pdf_path = Path(pdf_path)
#     text = ""
#     methods_used = []

#     # 1) Try pdfplumber FIRST (fastest & handles text-based PDFs)
#     try:
#         import pdfplumber
#         with pdfplumber.open(str(pdf_path)) as pdf:
#             pages = [p.extract_text() or "" for p in pdf.pages]
#         text = "\n\n".join(pages).strip()
#         if text:
#             methods_used.append("pdfplumber")
#             return text, methods_used
#     except Exception as e:
#         print("pdfplumber error:", e)

#     # 2) Try PyPDF2 second (another text extractor)
#     if not text:
#         try:
#             import PyPDF2
#             reader = PyPDF2.PdfReader(str(pdf_path))
#             pages = [p.extract_text() or "" for p in reader.pages]
#             text = "\n\n".join(pages).strip()
#             if text:
#                 methods_used.append("PyPDF2")
#                 return text, methods_used
#         except Exception as e:
#             print("PyPDF2 error:", e)

#     # 3) GOOGLE VISION OCR (best-quality OCR)
#     try:
#         print(">>> Running Google Vision OCR...")

#         from google.cloud import vision

#         client = vision.ImageAnnotatorClient()

#         # Vision requires PDF to be converted to images
#         # Vision can process images directly OR full Document AI PDF
#         # Here we do per-page conversion using pdf2image
#         from pdf2image import convert_from_path

#         images = convert_from_path(str(pdf_path), poppler_path=r"C:\poppler-25.11.0\Library\bin")
#         print(f">>> Loaded {len(images)} page(s) for OCR")

#         ocr_texts = []

#         for idx, img in enumerate(images):
#             print(f">>> Vision OCR page {idx+1}")

#             img_byte_arr = io.BytesIO()
#             img.save(img_byte_arr, format="PNG")
#             content = img_byte_arr.getvalue()

#             image = vision.Image(content=content)
#             response = client.document_text_detection(image=image)

#             if response.error.message:
#                 print("Vision API Error:", response.error.message)

#             page_text = response.full_text_annotation.text
#             ocr_texts.append(page_text)

#         text = "\n\n".join(ocr_texts).strip()

#         if text:
#             methods_used.append("Google_Vision_OCR")
#             return text, methods_used

#     except Exception as e:
#         print(">>> Google Vision OCR ERROR:", e)

#     # 4) Fallback — raw bytes heuristics
#     try:
#         print(">>> Raw bytes fallback")
#         raw = pdf_path.read_bytes()
#         import re
#         segs = re.findall(rb'[\x20-\x7E]{30,}', raw)
#         segs = [s.decode("latin-1") for s in segs[:10]]
#         text = "\n\n".join(segs).strip()
#         if text:
#             methods_used.append("raw-bytes")
#             return text, methods_used
#     except Exception as e:
#         print("raw fallback error:", e)

#     return text, methods_used


#### pytesseract #########################
# from pathlib import Path
# import pytesseract
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# def extract_text_from_pdf(pdf_path: str):
#     pdf_path = Path(pdf_path)
#     text = ""
#     methods_used = []

#     # 1) pdfplumber
#     try:
#         import pdfplumber
#         with pdfplumber.open(str(pdf_path)) as pdf:
#             pages = [p.extract_text() or "" for p in pdf.pages]
#         text = "\n\n".join(pages).strip()
#         methods_used.append("pdfplumber")
#         print(">>>PLUMBER", "----", text)
#     except:
#         pass

#     # 2) PyPDF2
#     if not text:
#         try:
#             import PyPDF2
#             reader = PyPDF2.PdfReader(str(pdf_path))
#             pages = [p.extract_text() or "" for p in reader.pages]
#             text = "\n\n".join(pages).strip()
#             methods_used.append("PyPDF2")
#             print(">>>PYPDF")
#         except:
#             pass

#     # 3) OCR
#     if not text:
#         try:
#             print(">>>", "PYTESSERACT INICIO")
#             from pdf2image import convert_from_path
#             import pytesseract

#             images = convert_from_path(str(pdf_path), poppler_path=r"C:\poppler-25.11.0\Library\bin")
#             print(">>> OCR IMAGES LOADED:", len(images))

#             print(">>> PDF PATH:", pdf_path)
#             print("Exists? ", Path(pdf_path).exists())

#             ocr_texts = []
#             for i, img in enumerate(images):
#                 print(f"OCR PAGE {i+1}")
#                 ocr_texts.append(pytesseract.image_to_string(img, lang="por+eng"))


#             text = "\n\n".join(ocr_texts).strip()
#             methods_used.append("pytesseract(pdf2image)")
#             print("OCR >>>>", text)
            
#         except Exception as e:
#             #pass
#             print(">>> OCR ERROR:", e)

#     # 4) raw fallback
#     if not text:
#         try:
#             print(">>>", "raw")
#             raw = pdf_path.read_bytes()
#             import re
#             segs = re.findall(rb'[\x20-\x7E]{30,}', raw)
#             segs = [s.decode("latin-1") for s in segs[:10]]
#             text = "\n\n".join(segs).strip()
#             if text:
#                 methods_used.append("raw-bytes-ascii")
#         except:
#             pass

#     return text, methods_used
