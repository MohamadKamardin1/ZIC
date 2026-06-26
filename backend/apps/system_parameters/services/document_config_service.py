import logging

from .config_service import ConfigurationService

logger = logging.getLogger(__name__)


class DocumentConfigService:
    """Configuration-driven document upload rules.

    Reads MIME types, file size limits, and other upload restrictions
    from System Parameters. No hardcoded values.
    """

    @staticmethod
    def get_allowed_mime_types() -> list:
        return ConfigurationService.get_json_parameter(
            "ALLOWED_MIME_TYPES",
            [
                "application/pdf",
                "image/jpeg",
                "image/png",
                "image/jpg",
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ],
        )

    @staticmethod
    def get_max_file_size_mb() -> int:
        return ConfigurationService.get_int_parameter("MAX_FILE_SIZE_MB", 10)

    @staticmethod
    def get_max_file_size_bytes() -> int:
        return DocumentConfigService.get_max_file_size_mb() * 1024 * 1024

    @staticmethod
    def get_excel_extensions() -> list:
        return ConfigurationService.get_json_parameter(
            "EXCEL_EXTENSIONS", [".xlsx", ".xls"]
        )


document_config = DocumentConfigService
