import os
import sys

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI

from langchain_community.vectorstores import FAISS

from vector_database import create_faiss_index_from_path, create_faiss_index_from_uploaded_pdf, get_embedding_model

load_dotenv()


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


llm_model = AzureChatOpenAI(
    azure_endpoint=require_env("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    azure_deployment=require_env("AZURE_GPT_DEPLOYMENT"),
    api_key=require_env("AZURE_OPENAI_API_KEY"),
)

# Prompt template
custom_prompt_template = """
You are BankIslami's virtual banking assistant. Use ONLY the context below.
Maintain a professional, respectful banking tone. Be clear, precise, and concise.
If the request is unclear, ask one short follow-up question.
Use numbered lists (1., 2., 3.) for multiple options, each item on its own line.
After a list, ask a brief follow-up question on a new line.
Reply in the same language as the user's question (English or Urdu).
If the answer is not in the context, say "I don't know" and ask for the specific info you need.
Do not make up facts or go beyond the provided context.

Question: {question}
Context: {context}
Answer:
"""


def get_context(documents):
    return "\n\n".join([doc.page_content for doc in documents])


# Retrieve docs from uploaded PDF
def retrieve_docs(query, vectorstore):
    return vectorstore.similarity_search(query, k=4)


def build_rag_context(query, vectorstore):
    documents = retrieve_docs(query, vectorstore)
    if not documents:
        return ""
    context = get_context(documents)
    if len(context.strip()) < 40:
        return ""
    return context


# Main RAG logic
def answer_query(uploaded_file, query):
    vectorstore = create_faiss_index_from_uploaded_pdf(uploaded_file)
    return answer_with_vectorstore(query, vectorstore)


def build_vectorstore_from_path(file_path):
    index_path = os.getenv("RAG_INDEX_PATH", "faiss_index")
    if os.path.isdir(index_path):
        embeddings = get_embedding_model()
        return FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
    return create_faiss_index_from_path(file_path)


def answer_with_vectorstore(query, vectorstore):
    context = build_rag_context(query, vectorstore)
    if not context:
        return ""
    prompt = ChatPromptTemplate.from_template(custom_prompt_template)
    chain = prompt | llm_model
    result = chain.invoke({"question": query, "context": context})
    text = getattr(result, "content", "") or str(result)
    return format_response(text)


def format_response(text):
    if " - **" in text:
        text = text.replace(" - **", "\n- **")
    text = text.replace("**", "")
    try:
        import re
        text = re.sub(r"(?<!\n)\s+(?=\d+\.\s)", "\n", text)
    except Exception:
        pass
    lines = [line.rstrip() for line in text.splitlines()]
    numbered = []
    idx = 1
    has_numbered = False
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("- "):
            numbered.append(f"{idx}. {stripped[2:].strip()}")
            idx += 1
            has_numbered = True
        else:
            numbered.append(line)

    normalized = "\n".join(numbered)
    if has_numbered:
        return _move_trailing_sentence_to_new_line(normalized)

    inline = normalized
    if "1." in inline:
        import re
        splits = re.split(r"\b(\d+)\.\s*", inline)
        if len(splits) >= 3:
            head = splits[0].strip()
            items = []
            tail = ""
            for i in range(1, len(splits), 2):
                num = splits[i]
                body = splits[i + 1].strip()
                if not body:
                    continue
                items.append(f"{num}. {body}")
            if items:
                # If the last item contains a follow-up question, move it to a new line.
                last = items[-1]
                q_match = re.search(r"([A-Z][^?]*\?)", last)
                if q_match:
                    q_start = q_match.start(1)
                    tail = last[q_start:].strip()
                    items[-1] = last[:q_start].strip()
                normalized = ("\n".join([head] + items)).strip() if head else "\n".join(items)
                if tail:
                    normalized = normalized + "\n\n" + tail
                return _move_trailing_sentence_to_new_line(normalized)
    if ":" in inline:
        prefix, rest = inline.split(":", 1)
        parts = [p.strip() for p in rest.split(".") if p.strip()]
        if len(parts) >= 2:
            numbered_parts = [f"{i + 1}. {p}" for i, p in enumerate(parts)]
            normalized = f"{prefix.strip()}:\n" + "\n".join(numbered_parts)
            return _move_trailing_sentence_to_new_line(normalized)

    return normalized


def _move_trailing_sentence_to_new_line(text):
    lines = [line.rstrip() for line in text.splitlines()]
    stitched = []
    seen_numbered = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped[:2].isdigit() and stripped[1:2] == "." or stripped[:3].isdigit() and stripped[2:3] == ".":
            stitched.append(stripped)
            seen_numbered = True
            continue
        if seen_numbered:
            stitched.append("")
            stitched.append(stripped)
            seen_numbered = False
        else:
            stitched.append(stripped)
    return "\n".join(stitched).strip()


def run_cli():
    try:
        data_path = os.getenv("RAG_DATA_PATH")
        if not data_path:
            raise RuntimeError("Missing RAG_DATA_PATH.")

        print(f"Loading vector data from {data_path}...")
        vectorstore = build_vectorstore_from_path(data_path)
        print("Vectorstore ready.")

        if len(sys.argv) > 1:
            sample_question = " ".join(sys.argv[1:])
        else:
            sample_question = os.getenv("RAG_TEST_QUESTION", "What is BankIslami?")
        print(f"Running test question: {sample_question}")
        answer = answer_with_vectorstore(sample_question, vectorstore)
        print("Answer generated.")
        print(answer)
    except Exception as exc:
        print(f"RAG CLI failed: {exc}")
        raise


if __name__ == "__main__":
    run_cli()
