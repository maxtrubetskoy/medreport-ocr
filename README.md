# Medical Report Translation Pipeline (MRTP) - PDF & OCR Version

## 1. Objective
To build an automated script that processes a directory of Russian medical reports in **.docx** format. The script converts each `.docx` file to a `.pdf`, uses a vision model to perform OCR on each page, extracts the text, and then uses a text-based model to translate the content into both Kazakh and English. The final structured data is saved into a single JSON file.

This version is designed to handle scanned documents or documents where text is embedded in images.

## 2. Core Technologies
- **Programming Language**: Python 3
- **DOCX to PDF Conversion**: `docx2pdf` library (requires Microsoft Word on Windows).
- **LLM (Vision)**: A vision-capable model for OCR (e.g., Gemma 3 Vision).
- **LLM (Text)**: A text-based model for translation and structuring (e.g., Gemma 3).
- **LLM Hosting**: LM Studio, running local inference servers for both models.
- **Key Libraries**: `docx2pdf`, `PyMuPDF`, `requests`, `Pillow`, `python-docx`.

## 3. Workflow
1.  **File Discovery**: The script scans the input directory for all `.docx` files.
2.  **DOCX to PDF Conversion**: Each `.docx` file is converted to a temporary `.pdf` file using the `docx2pdf` library, which leverages a local Microsoft Word installation.
3.  **PDF to Image Conversion**: Each page of the temporary PDF is converted into a high-resolution image.
4.  **OCR with Vision LLM**: Each page image is sent to the vision model to extract the text.
5.  **Text Aggregation**: The OCR'd text from all pages of a single document is combined.
6.  **Data Structuring & Translation**: The aggregated text is sent to the text-based LLM to be structured and translated.
7.  **Output Generation**: All processed data is compiled into a single JSON file.

## 4. How to Set Up the Environment
It is recommended to use a virtual environment.

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`

# Install dependencies
pip install -r requirements.txt
```

## 5. How to Run the Script
First, ensure that LM Studio is running with **both a vision model and a text model loaded** and that their local servers are active.

To process the reports, run the script from the command line:

```bash
python process_reports.py --input-dir ./reports --output-file ./output/results.json
```

- `--input-dir`: The path to the directory containing the **.docx** files.
- `--output-file`: The path to the output JSON file.

## 6. Prerequisites
- **Microsoft Word**: You must have Microsoft Word installed for the `.docx` to `.pdf` conversion to work.
- **LM Studio**: You must have LM Studio installed and running.
- **Models Loaded**:
  - A **vision model** must be loaded and served for OCR.
  - A **text-based model** must be loaded and served for translation and data structuring.
- **Input Files**: Your input documents must be in **.docx** format.