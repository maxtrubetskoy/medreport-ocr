# This is the main script for the Medical Report Translation Pipeline (MRTP).
import os
import json
import argparse
import base64
import io
import tempfile
import pymupdf  # PyMuPDF
import requests
from PIL import Image
from docx2pdf import convert

# --- Configuration ---
VISION_LLM_API_URL = "http://localhost:1234/v1/chat/completions"
VISION_MODEL_NAME = "google/gemma-3-12b"

# --- File Processing ---
def get_docx_files(directory):
    """Scans a directory for .docx files."""
    if not os.path.isdir(directory):
        print(f"Error: Input directory not found at {directory}")
        return []
    return [os.path.join(directory, f) for f in os.listdir(directory) if f.lower().endswith('.docx')]

def convert_docx_to_pdf(input_path):
    """Converts a DOCX file to PDF using the docx2pdf library."""
    try:
        print(f"  - Converting {os.path.basename(input_path)} to PDF...")
        temp_pdf_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
        convert(input_path, temp_pdf_path)
        print(f"  - Successfully converted to temporary file: {os.path.basename(temp_pdf_path)}")
        return temp_pdf_path
    except Exception as e:
        print(f"  - Error converting DOCX to PDF with docx2pdf: {e}")
        print("  - Please ensure Microsoft Word is installed and accessible.")
        return None

def pdf_to_images(filepath):
    """Converts each page of a PDF into a PIL Image."""
    try:
        doc = pymupdf.open(filepath)
        images = [page.get_pixmap(dpi=500).pil_image() for page in doc]
        images = [im.resize((im.size[0]*2, im.size[1]*2), 3) for im in images]
        doc.close()
        return images
    except Exception as e:
        print(f"  - Error processing PDF file {os.path.basename(filepath)}: {e}")
        return []
    
def pdf_to_text(filepath):
    """Extracts text from pdf directly using PyMuPDF. Needs fallback to OCR when the document contains screenshots of text isntead of a text"""
    try:
        doc = pymupdf.open(filepath)
        text = ""
        for page in range(doc.page_count):
            text += doc.get_page_text(page)
        return text
    except Exception as e:
        print(f"  - Error processing PDF file {os.path.basename(filepath)}: {e}")
        return ""
    
def image_to_base64(image, format="jpeg"):
    """Converts a PIL image to a base64 encoded string."""
    buffered = io.BytesIO()
    image.save(buffered, format=format)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

# --- LLM Interaction ---
def call_text_llm(messages, temperature=0.1):
    """Generic function to call the LM Studio Text API."""
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": VISION_MODEL_NAME,
        "messages": messages,
        "temperature": temperature,
        # "response_format": {"type": "json_object"},
    }
    try:
        response = requests.post(VISION_LLM_API_URL, headers=headers, json=payload, timeout=180)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        print(f"  - API request to text model failed: {e}")
        return None

def ocr_image_with_vision_llm(image):
    """Performs OCR on a single image using a vision LLM."""
    base64_image = image_to_base64(image)

    headers = {"Content-Type": "application/json"}
    payload = {
        "model": VISION_MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract all text from this image of a medical report page. Do not translate anything (content will be primarily in Russian), do not output any extra text - only what you see from the image."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ],
        "max_tokens": 32000,
    }

    try:
        response = requests.post(VISION_LLM_API_URL, headers=headers, json=payload, timeout=180)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        print(f"  - API request to vision model failed: {e}")
        return f"Simulated OCR text due to API failure: {e}"

def parse_llm_json_output(text):
    """Parses the LLM output that should be a JSON object."""
    try:
        text = text.replace("json", "").replace("```", "")
        return json.loads(text)
    except json.JSONDecodeError:
        print("  - Failed to parse LLM output as JSON. Received:", text)
        return None

def extract_structured_ru_data(text):
    """Extracts patient info and organ descriptions from OCR'd Russian text."""
    system_prompt = "You are a data extraction assistant. Extract patient information and organ descriptions from the provided medical report text. Output a single JSON object."
    prompt = f"""
Please extract the patient information (patient_group, patient_id, age, gender) and the descriptions for each organ from the following Russian medical report text.

The output must be a single, well-formed JSON object with this structure:
{{
  "patient_group": "...",
  "patient_id": "...",
  "age": "...",
  "gender": "...",
  "captions_ru": {{
    "organ_name_1": "description in Russian...",
    "organ_name_2": "description in Russian...",
    ...
    "conclusion": "conclusion extracted from the text"
  }}
}}

Report Text:
---
{text}
---
"""
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": [{"type": "text", "text": prompt}]}]
    response_text = call_text_llm(messages)
    return parse_llm_json_output(response_text) if response_text else None

def translate_captions(captions, target_language):
    """Translates a dictionary of captions to the target language."""
    system_prompt = f"You are an expert medical translator. Translate the provided JSON values from Russian to {target_language}. Preserve the JSON structure and keys. Do not add any commentary."
    prompt = f"""
Translate the values in the following JSON object to {target_language}.
Return a single JSON object with the same keys.

Input:
{json.dumps(captions, ensure_ascii=False, indent=2)}
"""
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
    response_text = call_text_llm(messages)
    return parse_llm_json_output(response_text) if response_text else None

# --- Main Pipeline ---
def main():
    """Main function to drive the report processing pipeline."""
    parser = argparse.ArgumentParser(description="Medical Report Translation Pipeline (MRTP)")
    parser.add_argument("--input-dir", type=str, required=True, help="Input directory containing .docx files.")
    parser.add_argument("--output-file", type=str, required=True, help="Output JSON file path.")
    parser.add_argument("--force-ocr", type=bool, required=False, default=False, help="Use OCR to extract textual data?")
    args = parser.parse_args()

    docx_files = get_docx_files(args.input_dir)
    if not docx_files:
        print(f"No .docx files found in {args.input_dir}. Exiting.")
        return

    all_report_data = []

    for docx_file in docx_files:
        print(f"Processing {os.path.basename(docx_file)}...")

        temp_pdf = convert_docx_to_pdf(docx_file)
        if not temp_pdf:
            print(f"  - Skipping {os.path.basename(docx_file)} due to conversion failure.")
            continue


        if args.force_ocr:
            images = pdf_to_images(temp_pdf)

            if not images:
                print(f"  - Could not extract images from the converted PDF. Skipping.")
                continue

            print(f"  - Extracted {len(images)} page(s). Performing OCR...")
            full_ocr_text = ""
            for i, image in enumerate(images):
                print(f"    - Processing page {i+1}/{len(images)}...")
                ocr_text = ocr_image_with_vision_llm(image)
                if ocr_text:
                    full_ocr_text += ocr_text + "\n\n"
        else:
            full_ocr_text = pdf_to_text(temp_pdf)
            if len(full_ocr_text) < 50:
                images = pdf_to_images(temp_pdf)
                
                if not images:
                    print(f"  - Could not extract images from the converted PDF. Skipping.")
                    continue

                print(f"  - Extracted {len(images)} page(s). Performing OCR...")
                for i, image in enumerate(images):
                    print(f"    - Processing page {i+1}/{len(images)}...")
                    ocr_text = ocr_image_with_vision_llm(image)
                    if ocr_text:
                        full_ocr_text += ocr_text + "\n\n"
                
        os.remove(temp_pdf)
        if not full_ocr_text.strip():
            print(f"  - No text could be extracted. Skipping.")
            continue

        print("  - OCR complete. Extracting structured data...")
        structured_data = extract_structured_ru_data(full_ocr_text)
        if not structured_data or "captions_ru" not in structured_data:
            print(f"  - Failed to extract structured data. Skipping.")
            continue

        captions_ru = structured_data.get("captions_ru", {})

        print("  - Translating to English...")
        captions_en = translate_captions(captions_ru, "English")
        if not captions_en:
            print(f"  - Failed to translate to English. Skipping.")
            continue

        print("  - Translating to Kazakh...")
        captions_kz = translate_captions(captions_ru, "Kazakh")
        if not captions_kz:
            print(f"  - Failed to translate to Kazakh. Skipping.")
            continue

        final_report = {
            "source_file": os.path.basename(docx_file),
            "patient_group": structured_data.get("patient_group", "N/A"),
            "patient_id": structured_data.get("patient_id", "N/A"),
            "age": structured_data.get("age", "N/A"),
            "gender": structured_data.get("gender", "N/A"),
            "captions_ru": captions_ru,
            "captions_en": captions_en,
            "captions_kz": captions_kz,
        }
        all_report_data.append(final_report)
        print(f"  - Successfully processed {os.path.basename(docx_file)}.")

    if not all_report_data:
        print("\nNo data was processed successfully.")
        return

    output_dir = os.path.dirname(args.output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(args.output_file, 'w', encoding='utf-8') as f:
        json.dump(all_report_data, f, ensure_ascii=False, indent=4)
    print(f"\nProcessing complete. Results saved to {args.output_file}")


if __name__ == "__main__":
    main()
