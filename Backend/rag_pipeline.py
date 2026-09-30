import os
import shutil
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import Chroma

from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser


# ==========================================
# Configuration
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "openai/gpt-oss-20b"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
TOP_K = 5

DOCUMENTS_PATH = BASE_DIR / "documents"
TEMP_UPLOADS_PATH = BASE_DIR / "temp_uploads"
VECTORSTORE_PATH = BASE_DIR / "chroma_db"


# ==========================================
# Prompt
# ==========================================

ACADEMIC_PROMPT = PromptTemplate.from_template(
    """You are a helpful academic assistant.

Answer the question using ONLY the provided context
from the academic documents.

If the answer is not present in the context, say:

"I cannot find this information in the provided documents."

Always mention the source document when possible.

Context:
{context}

Question:
{question}

Answer:"""
)


# ==========================================
# Academic RAG
# ==========================================

class AcademicRAG:

    def __init__(self):

        # Local Hugging Face embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL
        )

        # Groq LLM through OpenAI-compatible API
        self.llm = ChatOpenAI(
            model=LLM_MODEL,
            temperature=0.1,
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )

        self.vectorstore = None
        self.retriever = None

    # ======================================
    # Load PDFs
    # ======================================

    def load_documents(
        self,
        docs_path: str = None
    ) -> List:

        if docs_path is None:
            docs_path = str(DOCUMENTS_PATH)

        path = Path(docs_path)

        if not path.exists():
            path.mkdir(
                parents=True,
                exist_ok=True
            )
            return []

        loader = DirectoryLoader(
            str(path),
            glob="**/*.pdf",
            loader_cls=PyPDFLoader,
            show_progress=True
        )

        documents = loader.load()

        print(
            f"Loaded {len(documents)} pages from PDFs"
        )

        return documents

    # ======================================
    # Create Vector Store
    # ======================================

    def create_vectorstore(
        self,
        documents: List,
        force_rebuild: bool = False
    ):

        if (
            VECTORSTORE_PATH.exists()
            and not force_rebuild
        ):

            print("Loading existing vector store...")

            self.vectorstore = Chroma(
                persist_directory=str(
                    VECTORSTORE_PATH
                ),
                embedding_function=self.embeddings
            )

        else:

            if not documents:

                raise ValueError(
                    "No documents found. "
                    "Please add PDFs to the documents folder."
                )

            print("Splitting documents...")

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE,
                chunk_overlap=CHUNK_OVERLAP,
                separators=[
                    "\n\n",
                    "\n",
                    ". ",
                    " ",
                    ""
                ]
            )

            chunks = splitter.split_documents(
                documents
            )

            print(
                f"Created {len(chunks)} chunks"
            )

            # Delete old vector store
            if (
                force_rebuild
                and VECTORSTORE_PATH.exists()
            ):

                shutil.rmtree(
                    VECTORSTORE_PATH
                )

            print(
                "Building Chroma vector store..."
            )

            self.vectorstore = Chroma.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                persist_directory=str(
                    VECTORSTORE_PATH
                )
            )

            print(
                "Vector store created successfully."
            )

        self.retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={
                "k": TOP_K
            }
        )

    # ======================================
    # Format Retrieved Documents
    # ======================================

    def format_docs(self, docs) -> str:

        return "\n\n".join(
            f"[Source: "
            f"{doc.metadata.get('source', 'unknown')} "
            f"| Page: "
            f"{doc.metadata.get('page', '?')}]\n"
            f"{doc.page_content}"
            for doc in docs
        )

    # ======================================
    # Build RAG Chain
    # ======================================

    def build_chain(self):

        def retrieve_and_format(
            question: str
        ):

            docs = self.retriever.invoke(
                question
            )

            return self.format_docs(
                docs
            )

        chain = (
            {
                "context": retrieve_and_format,
                "question": RunnablePassthrough()
            }
            | ACADEMIC_PROMPT
            | self.llm
            | StrOutputParser()
        )

        return chain

    # ======================================
    # Query
    # ======================================

    def query(
        self,
        question: str
    ) -> Tuple[str, List]:

        if self.retriever is None:

            raise ValueError(
                "Vector store is not initialized. "
                "Please process your documents first."
            )

        docs = self.retriever.invoke(
            question
        )

        chain = self.build_chain()

        answer = chain.invoke(
            question
        )

        return answer, docs


# ==========================================
# Process Uploaded PDFs
# ==========================================

def process_uploaded_pdfs(
    uploaded_files,
    rag: AcademicRAG
):

    TEMP_UPLOADS_PATH.mkdir(
        parents=True,
        exist_ok=True
    )

    documents = []

    for uploaded_file in uploaded_files:

        file_path = (
            TEMP_UPLOADS_PATH
            / uploaded_file.name
        )

        with open(
            file_path,
            "wb"
        ) as f:

            f.write(
                uploaded_file.getbuffer()
            )

        loader = PyPDFLoader(
            str(file_path)
        )

        documents.extend(
            loader.load()
        )

    existing = rag.load_documents()

    all_docs = existing + documents

    rag.create_vectorstore(
        all_docs,
        force_rebuild=True
    )

    return len(all_docs)