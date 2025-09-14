# Medical Report Translation and Analysis Pipeline (MRTAP)

## 1. Objective
To build an automated script that processes a directory of Russian medical reports in **.docx** format. The script orchestrates a multi-step pipeline:
1.  **Converts** each `.docx` file to a temporary `.pdf`.
2.  **Extracts text** using a hybrid approach: it first attempts direct text extraction from the PDF, and if that fails to yield sufficient content, it falls back to a more robust vision-based OCR.
3.  **Extracts structured data** from the raw text using a Large Language Model (LLM).
4.  **Translates** the extracted medical descriptions into both **English** and **Kazakh**.
5.  **Generates one-hot encoded labels** (0 for healthy, 1 for diseased) for each organ based on the translated text.

The final, enriched data from all reports is aggregated and saved into a single, structured JSON file.

## 2. Core Technologies
- **Programming Language**: Python 3
- **File Conversion/Handling**: `docx2pdf`, `PyMuPDF`
- **LLM Interaction**: `requests`
- **Image Processing**: `Pillow`
- **LLM Hosting (Assumed)**: LM Studio or a similar tool serving a local API endpoint.
- **Key Libraries**: `docx2pdf`, `PyMuPDF`, `requests`, `Pillow`, `python-docx`.

## 3. Workflow
1.  **File Discovery**: The script scans the input directory for all `.docx` files.
2.  **DOCX to PDF Conversion**: Each `.docx` is converted to a temporary PDF. This requires a local installation of Microsoft Word.
3.  **Hybrid Text Extraction**:
    *   The script first attempts to extract text directly from the PDF using `PyMuPDF`. This is fast and works for text-based PDFs.
    *   If the extracted text is too short (under 50 characters), the script assumes the PDF contains scanned images and automatically switches to the OCR workflow.
    *   **OCR Workflow**: The PDF pages are converted to images, and each image is sent to a vision LLM to extract the text.
    *   The `--force-ocr` flag can be used to skip the direct extraction and use the OCR workflow for all files.
4.  **LLM-based Data Enrichment (Multi-step)**:
    *   **Step 1: Extract Structured Russian Data**: The aggregated text is sent to an LLM to identify and extract patient information and organ-specific medical descriptions into a structured JSON format.
    *   **Step 2: Translate to English & Kazakh**: The Russian descriptions are sent back to the LLM to be translated into English and Kazakh.
    *   **Step 3: Generate Labels**: The translated English descriptions are then used to generate one-hot encoded labels (`0` or `1`) indicating the health status of each organ.
5.  **Output Generation**: All processed data for each report is compiled and saved into a single JSON file.

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
First, ensure that your local LLM server (e.g., LM Studio) is running and the required models are loaded and served.

To process the reports, run the script from the command line:

```bash
python process_reports.py --input-dir ./reports --output-file ./output/results.json
```

### Command-Line Arguments
- `--input-dir` (required): The path to the directory containing the **.docx** files.
- `--output-file` (required): The path where the output JSON file will be saved.
- `--force-ocr` (optional): A boolean flag (`True`/`False`) that, when set to `True`, forces the script to use the OCR workflow for all documents, even if direct text extraction is possible. Example: `python process_reports.py ... --force-ocr True`.

## 6. Output JSON Structure
The output file is a JSON array where each object represents a processed medical report. Here is an example of the structure for a single report:

```json
[
    {
        "source_file": "report_01.docx",
        "patient_group": "group_A",
        "patient_id": "report_01.txt",
        "age": "45",
        "gender": "Male",
        "captions_ru": {
            "Печень": "эхогенность паренхимы повышена, структура однородная...",
            "Желчный пузырь": "стенки не утолщены, содержимое однородное...",
            "conclusion": "Умеренные диффузные изменения в паренхиме печени."
        },
        "captions_en": {
            "Liver": "parenchymal echogenicity is increased, structure is homogeneous...",
            "Gallbladder": "walls are not thickened, contents are homogeneous...",
            "conclusion": "Moderate diffuse changes in the liver parenchyma."
        },
        "captions_kz": {
            "Бауыр": "паренхиманың эхогенділігі жоғарылаған, құрылымы біркелкі...",
            "Өт қабы": "қабырғалары қалыңдамаған, ішіндегісі біркелкі...",
            "conclusion": "Бауыр паренхимасындағы орташа диффузиялық өзгерістер."
        },
        "labels": {
            "Liver": 1,
            "Gallbladder": 0,
            "conclusion": 1
        }
    }
]
```

## 7. Prerequisites
- **Microsoft Word**: You must have Microsoft Word installed for the `.docx` to `.pdf` conversion to work.
- **LLM Server**: You must have a local or remote LLM inference server running that is compatible with the OpenAI chat completions API format.
- **Models Loaded**:
  - A **vision-capable model** must be available for the OCR task.
  - A powerful **text-based model** must be available for the extraction, translation, and labeling tasks.
- **Input Files**: Your input documents must be in **.docx** format.