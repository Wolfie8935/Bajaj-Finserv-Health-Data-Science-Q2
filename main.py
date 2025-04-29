from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import uuid
from batch_processor import extract_text_from_image, parse_lab_tests, format_output
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Lab Report OCR API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "temp_uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@app.get("/", response_class=HTMLResponse)
async def root():
    html_content = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Lab Test OCR API</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                h1 { color: #333; }
                form { margin-top: 20px; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                button { background-color: #4CAF50; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; }
                button:hover { background-color: #45a049; }
                #result { margin-top: 20px; padding: 10px; border: 1px solid #ddd; border-radius: 5px; white-space: pre-wrap; }
                .loading { display: none; margin-left: 10px; }
            </style>
        </head>
        <body>
            <h1>Lab Test OCR API</h1>
            <p>Upload a lab test image to extract test results using OCR. Only POST requests are allowed.</p>
            
            <form id="upload-form" enctype="multipart/form-data">
                <input type="file" id="file-input" name="file" accept="image/*" required>
                <button type="submit">Process Image</button>
                <span class="loading" id="loading">Processing...</span>
            </form>
            
            <div id="result"></div>
            
            <script>
                document.getElementById('upload-form').addEventListener('submit', async (e) => {
                    e.preventDefault();
                    
                    const formData = new FormData();
                    const fileInput = document.getElementById('file-input');
                    formData.append('file', fileInput.files[0]);
                    
                    document.getElementById('loading').style.display = 'inline';
                    document.getElementById('result').textContent = '';
                    
                    try {
                        const response = await fetch('/get-lab-tests', {
                            method: 'POST',
                            body: formData,
                        });
                        
                        const data = await response.json();
                        document.getElementById('result').textContent = JSON.stringify(data, null, 2);
                    } catch (error) {
                        document.getElementById('result').textContent = `Error: ${error.message}`;
                    } finally {
                        document.getElementById('loading').style.display = 'none';
                    }
                });
            </script>
        </body>
    </html>
    """
    return html_content

@app.get("/get-lab-tests")
async def get_lab_tests_get():
    return JSONResponse(
        status_code=405,
        content={"detail": "Method Not Allowed", "message": "This endpoint only accepts POST requests with a file upload"}
    )

@app.post("/get-lab-tests")
async def get_lab_tests(file: UploadFile = File(...)):
    try:
        logger.info(f"Processing file: {file.filename}")
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ".png"
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_extension}")

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"File saved to {file_path}, running OCR...")

        text = extract_text_from_image(file_path)
        logger.info(f"Extracted text: {text[:100]}...")  # Log first 100 chars

        parsed_data = parse_lab_tests(text)
        logger.info(f"Found {len(parsed_data)} lab tests")

        formatted_data = format_output(parsed_data)

        os.remove(file_path)
        logger.info("Temporary file removed")
        
        return {"is_success": True, "data": formatted_data}
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"is_success": False, "error": str(e)}
        )