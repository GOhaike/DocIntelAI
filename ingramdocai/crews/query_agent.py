from crewai.agent import Agent
from pydantic import BaseModel, Field
from ingramdocai.tools.get_chunk_tool import FetchDocumentChunksTool


# --------------------------------------------------
# Final Output Schema
# --------------------------------------------------

class QueryResponseState(BaseModel):
    final_message: str = Field(
        ...,
        description=(
            "Final user-facing answer to the submitted document query. "
            "This message must be natural, accurate, grounded in retrieved content, "
            "and include any referenced documents, file names, or source links if present."
        )
    )


# --------------------------------------------------
# Agent Definition
# --------------------------------------------------

query_response_agent = Agent(
    role="IngramDocAI Final Answer Agent",
    goal="Deliver a complete, grounded, and user-ready response based on retrieved document chunks.",
    backstory=(
        "You are the final authority in answering user questions based on documents uploaded to IngramDocAI. "
        "You do not invent anything. You never guess. Your answers are fully grounded in content retrieved from the vector store. "
        "You use semantic search (via FetchDocumentChunksTool) to retrieve the most relevant segments, then synthesize a single, clear message. "
        "You include document titles, file names, or links if present. If nothing relevant is found, you clearly state that."
    ),
    tools=[
        FetchDocumentChunksTool()
    ],
    allow_delegation=False,
    verbose=False
)


# --------------------------------------------------
# Prompt / Instruction Builder
# --------------------------------------------------

def query_response_instruction(
    tenant_id: str,
    user_query: str
) -> str:
    return f"""
    A user submitted the following natural language question:

    "{user_query}"

    Your job is to use the `fetch_document_chunks` tool to perform semantic search
    against all documents uploaded under:
    - tenant_id: {tenant_id}

    Instructions:
    1. Search using the full query.
    2. Analyze all retrieved chunks. Extract relevant facts, numbers, clauses, definitions, etc.
    3. If any file names, links, or document references are included — preserve and cite them.
    4. If no chunks are relevant, clearly say:
       "We couldn’t find anything relevant in your uploaded documents."

    Your final output:
    - Must be written in natural, professional language.
    - Must be a single standalone message — no tools, no bullets, no YAML.
    - Must feel confident, helpful, and grounded in the actual document data.
    """
