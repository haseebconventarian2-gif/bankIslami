import json
import os
import sys

from dotenv import load_dotenv
from langchain_community.document_loaders import PDFPlumberLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import AzureOpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

pdfs_directory = "pdfs/"
os.makedirs(pdfs_directory, exist_ok=True)

load_dotenv()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


# Save uploaded file to local directory
def upload_pdf(file):
    filename = getattr(file, "filename", None) or getattr(file, "name", None) or "upload.pdf"
    file_path = os.path.join(pdfs_directory, filename)

    if hasattr(file, "file"):
        data = file.file.read()
    elif hasattr(file, "read"):
        data = file.read()
    elif hasattr(file, "getbuffer"):
        data = file.getbuffer()
    else:
        data = file

    with open(file_path, "wb") as f:
        f.write(data)
    return file_path


def _extract_texts_from_json(data):
    if isinstance(data, list):
        texts = []
        for item in data:
            if isinstance(item, str):
                texts.append(item)
                continue
            if not isinstance(item, dict):
                continue

            content = item.get("content")
            if isinstance(content, dict):
                title = content.get("title")
                body = content.get("text") or content.get("content") or content.get("body")
                if isinstance(body, str):
                    if isinstance(title, str) and title.strip():
                        texts.append(f"{title.strip()}\n{body}")
                    else:
                        texts.append(body)
                    continue

            for key in ("text", "content", "body"):
                if key in item and isinstance(item[key], str):
                    texts.append(item[key])
                    break
        return texts

    if isinstance(data, dict):
        if isinstance(data.get("documents"), list):
            return [d for d in data["documents"] if isinstance(d, str)]
        for key in ("text", "content", "body"):
            if isinstance(data.get(key), str):
                return [data[key]]

    return []


def load_json(file):
    if hasattr(file, "file"):
        raw = file.file.read()
    elif hasattr(file, "read"):
        raw = file.read()
    else:
        raw = file
    data = json.loads(raw)
    texts = _extract_texts_from_json(data)
    return [Document(page_content=t) for t in texts]


def load_json_path(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    texts = _extract_texts_from_json(data)
    return [Document(page_content=t) for t in texts]


# Load PDF contents
def load_pdf(file_path):
    loader = PDFPlumberLoader(file_path)
    return loader.load()


# Split into chunks
def create_chunks(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True,
    )
    return splitter.split_documents(documents)


# Get embedding model
def get_embedding_model():
    return AzureOpenAIEmbeddings(
        azure_endpoint=require_env("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        azure_deployment=require_env("AZURE_EMBEDDING_DEPLOYMENT"),
        api_key=require_env("AZURE_OPENAI_API_KEY"),
    )


# Create FAISS index from uploaded file
def create_faiss_index_from_uploaded_pdf(file):
    filename = getattr(file, "filename", None) or getattr(file, "name", None) or ""
    if filename.lower().endswith(".json"):
        docs = load_json(file)
    else:
        file_path = upload_pdf(file)
        docs = load_pdf(file_path)
    chunks = create_chunks(docs)
    embeddings = get_embedding_model()
    return FAISS.from_documents(chunks, embeddings)


def create_faiss_index_from_path(file_path):
    if file_path.lower().endswith(".json"):
        docs = load_json_path(file_path)
    else:
        docs = load_pdf(file_path)
    chunks = create_chunks(docs)
    embeddings = get_embedding_model()
    return FAISS.from_documents(chunks, embeddings)


def build_and_save_faiss_index(data_path, index_path):
    print(f"Loading data from {data_path}...")
    vectorstore = create_faiss_index_from_path(data_path)
    print("FAISS index created.")
    os.makedirs(index_path, exist_ok=True)
    vectorstore.save_local(index_path)
    print(f"FAISS index saved to {index_path}.")


if __name__ == "__main__":
    data_path = os.getenv("RAG_DATA_PATH")
    if len(sys.argv) > 1:
        data_path = sys.argv[1]

    if not data_path:
        raise SystemExit("Missing RAG_DATA_PATH or file path argument.")

    index_path = os.getenv("RAG_INDEX_PATH", "faiss_index")
    build_and_save_faiss_index(data_path, index_path)
