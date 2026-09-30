from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from langchain_community.document_loaders import PyPDFLoader

from Backend.rag_pipeline import AcademicRAG


# ==========================================
# Configuration
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent

FRONTEND_DIR = BASE_DIR / "Frontend"
DOCUMENTS_DIR = BASE_DIR / "documents"
TEMP_DIR = BASE_DIR / "temp_uploads"


DOCUMENTS_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)


# ==========================================
# FastAPI
# ==========================================

app = FastAPI(
    title="Academic RAG API",
    description="Academic Question Answering System using RAG",
    version="1.0"
)


# ==========================================
# RAG
# ==========================================

rag = AcademicRAG()


# ==========================================
# Request Model
# ==========================================

class QuestionRequest(BaseModel):

    question: str


# ==========================================
# Frontend
# ==========================================

app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static"
)


@app.get("/")
def home():

    return FileResponse(
        FRONTEND_DIR / "index.html"
    )


# ==========================================
# Upload PDF
# ==========================================

@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...)
):

    if not file.filename.lower().endswith(".pdf"):

        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )


    file_path = TEMP_DIR / file.filename


    # Save uploaded PDF

    contents = await file.read()

    with open(file_path, "wb") as f:

        f.write(contents)


    try:

        # Load uploaded PDF

        loader = PyPDFLoader(
            str(file_path)
        )

        uploaded_documents = loader.load()


        # Load existing documents

        existing_documents = rag.load_documents(
            str(DOCUMENTS_DIR)
        )


        # Combine documents

        all_documents = (
            existing_documents +
            uploaded_documents
        )


        # Rebuild vector database

        rag.create_vectorstore(
            all_documents,
            force_rebuild=True
        )


        return {
            "message": "PDF uploaded and processed successfully.",
            "filename": file.filename,
            "pages": len(uploaded_documents)
        }


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ==========================================
# Ask Question
# ==========================================

@app.post("/ask")
def ask_question(
    request: QuestionRequest
):

    question = request.question.strip()


    if not question:

        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )


    try:

        # Load existing vector database

        if rag.retriever is None:

            rag.create_vectorstore(
                [],
                force_rebuild=False
            )


        # Ask RAG

        answer, docs = rag.query(
            question
        )


        # Prepare sources

        sources = []


        for doc in docs:

            source = Path(
                doc.metadata.get(
                    "source",
                    "unknown"
                )
            ).name


            page = doc.metadata.get(
                "page",
                "?"
            )


            # PyPDFLoader pages start from 0

            if isinstance(page, int):

                page = page + 1


            sources.append({

                "source": source,

                "page": page

            })


        return {

            "answer": answer,

            "sources": sources

        }


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )