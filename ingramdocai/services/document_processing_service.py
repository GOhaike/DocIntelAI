import os
from pathlib import Path
from typing import Dict, List, Any
from ingramdocai.core.logger import setup_logger

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyMuPDFLoader,
    PDFMinerLoader,
    UnstructuredFileLoader,
    Docx2txtLoader,
    CSVLoader,
    UnstructuredExcelLoader
)

logger = setup_logger("document_processor")


class DocumentProcessingService:
    def process(self, file_path: str) -> Dict[str, Any]:
        """
        Detects file type, loads the document using the appropriate LangChain loader,
        and returns chunked documents and metadata.

        Returns:
            {
                "chunks": List[Document],
                "metadata": Dict
            }
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        extension = Path(file_path).suffix.lower()
        loader = self._resolve_loader(file_path, extension)

        logger.debug(f"Using loader: {loader.__class__.__name__}")
        raw_docs = loader.load()

        if not raw_docs:
            raise ValueError("Loaded document is empty.")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
            separators=["\n\n", "\n", ".", " ", ""]
        )

        chunks = splitter.split_documents(raw_docs)

        logger.info(f"Processed {len(chunks)} chunks from {file_path}")

        return {
            "chunks": chunks,
            "metadata": {
                "file_path": file_path,
                "source_type": extension.lstrip("."),
                "chunk_count": len(chunks),
            }
        }

    def _resolve_loader(self, file_path: str, extension: str):
        """
        Returns the appropriate LangChain loader for a given file type.
        Falls back to Unstructured loader with OCR if needed.
        """
        try:
            if extension == ".pdf":
                try:
                    return PyMuPDFLoader(file_path)
                except Exception:
                    logger.warning("PyMuPDF failed, falling back to Unstructured loader with OCR")
                    return UnstructuredFileLoader(file_path, strategy="hi_res")

            elif extension == ".docx":
                return Docx2txtLoader(file_path)

            elif extension in [".xlsx", ".xls"]:
                return UnstructuredExcelLoader(file_path)

            elif extension == ".csv":
                return CSVLoader(file_path)

            elif extension == ".txt":
                return UnstructuredFileLoader(file_path)

            else:
                raise ValueError(f"Unsupported file extension: {extension}")

        except Exception as e:
            logger.error(f"Loader resolution failed for {file_path}: {str(e)}")
            raise
