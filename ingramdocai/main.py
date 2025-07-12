import uuid
import os
from pathlib import Path
from datetime import datetime
from ingramdocai.persistence.db import Base, engine
from ingramdocai.persistence.models import DocumentSession
from crewai.flow import Flow, start, listen, router, and_, or_
from ingramdocai.core.state import IngramDocAIFlowState
from ingramdocai.core.logger import setup_logger

from ingramdocai.services.document_processing_service import DocumentProcessingService
from ingramdocai.services.weaviate_class_manager import sync_schema, ensure_tenant_registered
from ingramdocai.services.document_upsert_embedding import bulk_upsert_document_chunks
from ingramdocai.core.crewai_output_normalizer import normalize_crewai_output 
from ingramdocai.tools.save_session_record import SaveSessionRecordTool

from ingramdocai.crews.status_request_agent import status_query_agent, status_query_instruction, StatusQueryState
from ingramdocai.crews.query_agent import query_response_agent,query_response_instruction, QueryResponseState
from ingramdocai.crews.document_analysis.document_analysis import DocumentAnalysisCrew


logger = setup_logger("ingramdocai_flow")


class IngramDocAIMainFlow(Flow[IngramDocAIFlowState]):

    @start()
    def receive_input(self):
        """
        Loads and validates required input fields from a flat JSON payload.
        Supports user_id, tenant_id, task_type, session_id, and user_query (if needed).
        """
        logger.info("Starting IngramDocAI input validation")

        user_id = str(self.state.user_id or "").strip()
        tenant_id = str(self.state.tenant_id or "").strip()
        task_type = str(self.state.task_type or "").strip().lower()
        session_id = str(self.state.session_id or str(uuid.uuid4())).strip()
        user_query = str(self.state.user_query or "").strip()

        if not user_id or not tenant_id:
            raise ValueError("Missing required fields: user_id and tenant_id.")

        if not task_type:
            raise ValueError("Missing required field: task_type.")

        if task_type in {"query", "analyze"} and not user_query:
            raise ValueError("Missing 'user_query' for task type 'query' or 'analyze'.")

        # Set validated values back into state
        self.state.user_id = user_id
        self.state.tenant_id = tenant_id
        self.state.task_type = task_type
        self.state.session_id = session_id
        self.state.user_query = user_query if task_type in {"query", "analyze"} else None

        logger.info(f"Task type: {task_type}, Tenant: {tenant_id}, Session: {session_id}")


    @router(receive_input)
    def Orchestrator(self) -> str:
        """
        Routes to the appropriate handler based on the user-specified task type.
        Supported routes: inject, analyze, query, status.
        """
        task = self.state.task_type

        if task == "inject":
            return "InjectDocumentRouter"
        elif task == "analyze":
            return "AnalyzeDocumentRouter"
        elif task == "query":
            return "QueryRouter"
        elif task == "status":
            return "StatusCheckRouter"
        else:
            raise ValueError(f"Unrecognized task type: {task}")


    @listen("InjectDocumentRouter")
    def inject_document(self):
        logger.info("Checking and initializing database schema if needed...")
        Base.metadata.create_all(bind=engine)

        try:
            sample_docs_dir = Path("tests/sample_docs").resolve()
            sample_docs_dir.mkdir(parents=True, exist_ok=True)

            file_paths = [str(f) for f in sample_docs_dir.glob("*") if f.is_file()]
            if not file_paths:
                logger.warning("No documents found in tests/sample_docs. Nothing to process.")
                return

            session_id = self.state.session_id
            tenant_id = self.state.tenant_id
            user_id = self.state.user_id


            logger.info(f"Injecting {len(file_paths)} document(s)")
            logger.debug(f"Session → ID: {session_id}, Tenant: {tenant_id}, User: {user_id}")

            SaveSessionRecordTool()._run(
                session_id=session_id,
                tenant_id=tenant_id,
                user_id=user_id,
                file_path=";".join(file_paths),
                status="in_progress",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            processor = DocumentProcessingService()
            all_chunks = []

            for file_path in file_paths:
                logger.info(f"Processing file: {file_path}")
                result = processor.process(file_path)
                for chunk in result["chunks"]:
                    chunk.metadata.update({
                        "file_name": Path(file_path).name,
                        "file_type": Path(file_path).suffix.lstrip("."),
                        "tenant_id": tenant_id,
                        "session_id": session_id
                    })
                    all_chunks.append(chunk)

            if not all_chunks:
                logger.warning("⚠️ No chunks generated from input documents.")
                return

            payloads = [{
                "tenant_id": chunk.metadata["tenant_id"],
                "session_id": chunk.metadata["session_id"],
                "file_name": chunk.metadata["file_name"],
                "file_type": chunk.metadata["file_type"],
                "text": chunk.page_content,
                "chunk_id": f"{i+1}",
                "char_count": len(chunk.page_content),
                "source": "document_upload",
                "created_at": datetime.utcnow().isoformat() + "Z"
            } for i, chunk in enumerate(all_chunks)]

            logger.info(f"Prepared {len(payloads)} chunks for upsert")

            sync_schema(tenant_id)
            ensure_tenant_registered(tenant_id)

            bulk_upsert_document_chunks(payloads)
            logger.info(f"Upserted {len(payloads)} document chunks into Weaviate")

            SaveSessionRecordTool()._run(
                session_id=session_id,
                tenant_id=tenant_id,
                user_id=user_id,
                status="completed",
                chunk_count=len(payloads),
                updated_at=datetime.utcnow()
            )

            self.state.chunk_count = len(payloads)

            print("\n====== Document Injection Completed ======")
            print(f"Session ID: {session_id}")
            print(f"Total Chunks: {self.state.chunk_count}")
            print("==========================================\n")

        except Exception as e:
            logger.error(f"Injection failed: {str(e)}")
            SaveSessionRecordTool()._run(
                session_id=self.state.session_id,
                tenant_id=self.state.user_info.get("tenant_id"),
                user_id=self.state.user_info.get("user_id"),
                status="failed",
                error_message=str(e),
                updated_at=datetime.utcnow()
            )
            raise


    @listen("StatusCheckRouter")
    def status_check(self):
        """
        Handles the StatusCheckRouter request.
        Executes the status_query_agent using session ID only,
        then stores the result in self.state.status_summary.
        """
        logger.info("[StatusCheckRouter] Launching document status check")

        try:
            session_id = self.state.session_id
            logger.debug(f"[StatusCheckRouter] Input → session_id={session_id}")
            prompt = status_query_instruction(session_id=session_id)
            response = status_query_agent.kickoff(
                prompt,
                response_format=StatusQueryState
            )

            self.state.status_summary = response
            logger.info("[StatusCheckRouter] Status response stored in self.state.status_summary")
            logger.debug(f"[StatusCheckRouter] Summary: {self.state.status_summary}")

            print("\n====== Document Status Result ======")
            print(self.state.status_summary)
            print("====================================\n")

        except Exception as e:
            logger.exception(f"[StatusCheckRouter] Failed to resolve document status: {str(e)}")
            raise



    @listen("QueryRouter")
    def query(self):
        logger.info("[QueryRouter] Starting document query handling")

        try:
            user_query = self.state.user_query
            tenant_id = self.state.tenant_id

            logger.debug(f"[QueryRouter] Inputs → query='{user_query}', tenant_id={tenant_id}")

            prompt = query_response_instruction(
                tenant_id=tenant_id,
                user_query=user_query
            )

            response = query_response_agent.kickoff(
                prompt,
                response_format=QueryResponseState
            )


            # print("\n====== Document Query Response ======")
            # print(response)
         
            self.state.query_answer = response

            logger.info("[QueryRouter] Query answer stored in self.state.query_answer")
            logger.debug(f"[QueryRouter] Answer: {self.state.query_answer}")

            print("\n====== Document Query Response ======")
            print(self.state.query_answer)
            print("=====================================\n")

        except Exception as e:
            logger.exception(f"[QueryRouter] Query handling failed: {str(e)}")
            raise


    @listen("AnalyzeDocumentRouter")
    def analyze_documents(self):
        """
        Loads all documents from tests/sample_docs using the same processor logic,
        merges their contents, and analyzes them as one unit.
        """
        logger.info("Starting unified document analysis from tests/sample_docs")

        base_dir = Path(__file__).resolve().parent.parent
        sample_docs_dir = base_dir / "tests" / "sample_docs"
        processor = DocumentProcessingService()

        all_text_blocks = []
        file_count = 0

        for file_path in sample_docs_dir.glob("*"):
            if file_path.is_file():
                try:
                    result = processor.process(str(file_path))
                    chunks = result.get("chunks", [])
                    for chunk in chunks:
                        all_text_blocks.append(f"\n\n### {file_path.name}\n{chunk.page_content.strip()}")
                    file_count += 1
                except Exception as e:
                    logger.warning(f"⚠ Failed to process {file_path.name}: {e}")

        if not all_text_blocks:
            logger.error("✘ No content found in tests/sample_docs.")
            return

        merged_content = "\n".join(all_text_blocks)
        logger.info(f"✔ Loaded {file_count} file(s). Running analysis...")

        try:
            result = DocumentAnalysisCrew().crew().kickoff(inputs={"documents": merged_content})
            self.state.document_analysis = result
            logger.info("✔ Document analysis complete. Result stored in self.state.document_analysis")

            print("\n====== Document Analysis Result ======")
            print(self.state.document_analysis)
            print("======================================\n")

        except Exception as e:
            logger.exception(f"✘ Document analysis failed: {e}")
            raise




def start():
    flow = IngramDocAIMainFlow()
    flow.kickoff(inputs={
        "user_id": "user-123",
        "tenant_id": "tenant-xyz",
        "task_type": "analyze",
        "session_id": "session-abc123",
        "user_query": "Tell me more about Ingram Micro"
    })


def plot():
    flow = IngramDocAIMainFlow(inputs={
        "user_id": "user-123",
        "tenant_id": "tenant-xyz",
        "task_type": "inject",
        "session_id": "session-abc123",
        "user_query": "What are the key provisions in the uploaded contract?"
    })
    flow.plot()


if __name__ == "__main__":
    start()
