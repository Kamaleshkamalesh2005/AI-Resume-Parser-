"""Upload use-case: orchestrates file validation, storage, and resume parsing."""

import logging
from typing import Any, Dict, List, Tuple

from app.models.resume_model import ResumeModel
from app.services.file_service import FileService
from app.utils.validators import validate_file_upload

logger = logging.getLogger(__name__)


class UploadUseCase:
    """Business logic for upload operations."""

    def __init__(self, upload_folder: str, allowed_extensions: set[str]):
        self.upload_folder = upload_folder
        self.allowed_extensions = allowed_extensions

    def validate(self, file_obj) -> Tuple[bool, str | None]:
        return validate_file_upload(file_obj, self.allowed_extensions)

    def process_single(self, file_obj) -> Tuple[Dict[str, Any], int]:
        is_valid, error = self.validate(file_obj)
        if not is_valid:
            return {
                "success": False,
                "error": "Invalid file",
                "message": error,
            }, 400

        success, result = FileService.save_upload(file_obj, self.upload_folder)
        if not success:
            return {
                "success": False,
                "error": "Upload failed",
                "message": result,
            }, 500

        resume = ResumeModel(filepath=result)
        if not resume.load_from_file():
            return {
                "success": False,
                "error": "File processing failed",
                "message": resume.error_message,
            }, 500

        if not resume.parse():
            return {
                "success": False,
                "error": "Resume parsing failed",
                "message": resume.error_message,
            }, 400

        resume.extract_features()
        return {
            "success": True,
            "data": resume.to_dict(),
            "message": "Resume processed successfully",
        }, 200

    def process_batch(self, files: List[Any]) -> Tuple[Dict[str, Any], int]:
        results: List[Dict[str, Any]] = []
        failed: List[Dict[str, str]] = []

        for file_obj in files:
            try:
                is_valid, error = self.validate(file_obj)
                if not is_valid:
                    failed.append({"filename": file_obj.filename, "error": error})
                    continue

                success, file_path = FileService.save_upload(file_obj, self.upload_folder)
                if not success:
                    failed.append({"filename": file_obj.filename, "error": file_path})
                    continue

                resume = ResumeModel(filepath=file_path)
                if resume.load_from_file() and resume.parse():
                    resume.extract_features()
                    results.append(resume.to_dict())
                else:
                    failed.append({"filename": file_obj.filename, "error": resume.error_message})
            except Exception as exc:
                logger.error("Batch upload item failed for %s: %s", file_obj.filename, exc)
                failed.append({"filename": file_obj.filename, "error": str(exc)})

        payload = {
            "success": len(results) > 0,
            "data": results,
            "failed": failed,
            "summary": {
                "total": len(files),
                "successful": len(results),
                "failed": len(failed),
            },
        }
        return payload, 200

    def process_job_description(self, text: str | None, file_obj) -> Tuple[Dict[str, Any], int]:
        clean_text = (text or "").strip()
        if clean_text:
            return {
                "success": True,
                "data": {
                    "source": "text",
                    "content": clean_text,
                    "length": len(clean_text),
                },
                "message": "Job description saved",
            }, 200

        if file_obj is None or file_obj.filename == "":
            return {
                "success": False,
                "error": "No content provided",
                "message": "Provide job description text or upload a file",
            }, 400

        allowed_for_jd = set(self.allowed_extensions) | {"txt"}
        is_valid, error = validate_file_upload(file_obj, allowed_for_jd)
        if not is_valid:
            return {
                "success": False,
                "error": "Invalid file",
                "message": error,
            }, 400

        success, path_or_error = FileService.save_upload(file_obj, self.upload_folder)
        if not success:
            return {
                "success": False,
                "error": "Upload failed",
                "message": path_or_error,
            }, 500

        file_path = path_or_error
        extract_ok, extracted = FileService.extract_text(file_path)
        if not extract_ok:
            return {
                "success": False,
                "error": "File processing failed",
                "message": extracted,
            }, 400

        jd_content = extracted.strip()
        if not jd_content:
            return {
                "success": False,
                "error": "Empty content",
                "message": "No readable text found in job description file",
            }, 400

        return {
            "success": True,
            "data": {
                "source": "file",
                "filename": file_obj.filename,
                "content": jd_content,
                "length": len(jd_content),
            },
            "message": "Job description saved",
        }, 200
