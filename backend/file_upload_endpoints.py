# File upload endpoints to be added to main.py
# Add these after the main APO workflow endpoint

from fastapi import File, UploadFile, HTTPException, Depends
from typing import Dict, Any
from pathlib import Path
import uuid
import logging
import PyPDF2
from fastapi.responses import FileResponse

# Add to imports in main.py:
# from fastapi import File, UploadFile
# from fastapi.responses import FileResponse
# import PyPDF2

# ==========================================================
# ================== FILE UPLOAD ENDPOINTS =================
# ==========================================================

async def upload_pdf(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = None,
    db_pool = None
):
    """
    Upload a PDF file and extract text content.
    Returns extracted text for use in document_context field.
    Max file size: 10MB
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if file.size and file.size > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")
    
    if file.content_type not in ["application/pdf"]:
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        # Read PDF content
        pdf_bytes = await file.read()
        pdf_reader = PyPDF2.PdfReader(stream=pdf_bytes)
        
        # Extract text from all pages
        extracted_text = ""
        for page_num, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            if page_text:
                extracted_text += f"\n--- Page {page_num + 1} ---\n{page_text}"
        
        if not extracted_text.strip():
            raise ValueError("No text content found in PDF")
        
        logging.info(f"PDF uploaded by {current_user.get('client_email')}: {len(extracted_text)} chars extracted")
        
        return {
            "status": "success",
            "filename": file.filename,
            "pages": len(pdf_reader.pages),
            "text_length": len(extracted_text),
            "extracted_text": extracted_text[:50000],  # Return first 50k chars
            "note": "Use the 'extracted_text' field as document_context in your APO request"
        }
    except Exception as e:
        logging.error(f"PDF extraction error: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to extract PDF: {str(e)}")


async def upload_video(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = None,
    db_pool = None
):
    """
    Upload a video file (MP4, WebM, MOV).
    Returns a reference URL for use in video_url field.
    Max file size: 500MB
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if file.size and file.size > 500 * 1024 * 1024:  # 500MB limit
        raise HTTPException(status_code=400, detail="File size exceeds 500MB limit")
    
    allowed_types = ["video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video type. Supported: MP4, WebM, MOV, AVI. Got: {file.content_type}"
        )
    
    try:
        # Save video to uploads directory
        uploads_dir = Path(__file__).resolve().parent / "uploads"
        uploads_dir.mkdir(exist_ok=True)
        
        # Generate unique filename
        file_ext = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = uploads_dir / unique_filename
        
        # Save file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Create reference URL
        video_ref_url = f"/api/video/{unique_filename}"
        
        logging.info(f"Video uploaded by {current_user.get('client_email')}: {unique_filename} ({len(content)} bytes)")
        
        return {
            "status": "success",
            "filename": file.filename,
            "file_size_mb": round(len(content) / (1024 * 1024), 2),
            "video_ref_url": video_ref_url,
            "note": "Use the 'video_ref_url' as the video_url field in your APO request"
        }
    except Exception as e:
        logging.error(f"Video upload error: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to upload video: {str(e)}")


async def get_video(filename: str, current_user: Dict[str, Any] = None):
    """
    Internal endpoint to retrieve uploaded video files.
    Only accessible by authenticated users.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    uploads_dir = Path(__file__).resolve().parent / "uploads"
    file_path = uploads_dir / filename
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Video file not found")
    
    import mimetypes
    mime_type, _ = mimetypes.guess_type(str(file_path))
    mime_type = mime_type or "application/octet-stream"
    
    return FileResponse(file_path, media_type=mime_type)

# Add to main.py routes:
# @app.post("/upload/pdf")
# async def endpoint_upload_pdf(file: UploadFile = File(...), current_user: Dict[str, Any] = Depends(get_current_user), db_pool=Depends(get_db_pool)):
#     return await upload_pdf(file, current_user, db_pool)
#
# @app.post("/upload/video")
# async def endpoint_upload_video(file: UploadFile = File(...), current_user: Dict[str, Any] = Depends(get_current_user), db_pool=Depends(get_db_pool)):
#     return await upload_video(file, current_user, db_pool)
#
# @app.get("/video/{filename}")
# async def endpoint_get_video(filename: str, current_user: Dict[str, Any] = Depends(get_current_user)):
#     return await get_video(filename, current_user)
