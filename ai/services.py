import os
from django.conf import settings
from django.apps import apps
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_milvus import Milvus
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_text_splitters import CharacterTextSplitter

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
MILVUS_URI = os.environ.get("MILVUS_URI", "http://localhost:19530")

class AIService:
    @classmethod
    def _get_embeddings(cls):
        return OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_BASE_URL)

    @classmethod
    def _get_llm(cls, temperature=0.7):
        return ChatOllama(model="llama3", temperature=temperature, base_url=OLLAMA_BASE_URL)

    @classmethod
    def _get_vectorstore(cls, collection_name: str):
        return Milvus(
            embedding_function=cls._get_embeddings(),
            connection_args={"uri": MILVUS_URI},
            collection_name=collection_name,
            auto_id=True
        )

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------
    @classmethod
    def index_documents(cls, collection_name, text_contents):
        try:
            docs = [Document(page_content=t) for t in text_contents if t]
            if not docs: return
            text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50, separator="\n")
            split_docs = text_splitter.split_documents(docs)
            vectorstore = cls._get_vectorstore(collection_name)
            vectorstore.add_documents(split_docs)
        except Exception as e:
            print(f"Error indexing to Milvus: {e}")

    @classmethod
    def initialize_rag(cls):
        """Initializes the vector store with all platform documents."""
        KnowledgeDocument = apps.get_model('ai', 'KnowledgeDocument')
        docs = list(KnowledgeDocument.objects.filter(is_active=True).values_list('content', flat=True))
        if docs:
            cls.index_documents("platform_info", docs)

    @classmethod
    def initialize_course_rag(cls, course_id):
        """Initializes a specific vector store for a course."""
        Lesson = apps.get_model('courses', 'Lesson')
        ContentBlock = apps.get_model('courses', 'ContentBlock')
        blocks = ContentBlock.objects.filter(lesson__chapter__course_id=course_id, type='text')
        texts = [b.text_content for b in blocks if b.text_content]
        if texts:
            cls.index_documents(f"course_{course_id}", texts)

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    @classmethod
    def get_course_recommendations(cls, user, limit=5, force_refresh=False):
        """Semantic course recommendations based on user enrollments."""
        Course = apps.get_model('courses', 'Course')
        Enrollment = apps.get_model('interactions', 'Enrollment')
        enrolled_ids = list(Enrollment.objects.filter(student=user).values_list('course_id', flat=True))
        return list(Course.objects.filter(is_approved=True).exclude(id__in=enrolled_ids).order_by('-created_at')[:limit])

    @classmethod
    def get_platform_chat_response(cls, query):
        """Answers questions about the platform using RAG."""
        try:
            vectorstore = cls._get_vectorstore("platform_info")
            llm = cls._get_llm(0.7)
            system_prompt = (
                "You are the Fatra Academy Assistant. Use the following context to answer.\n"
                "If you don't know something, suggest they contact support.\n\n"
                "Context:\n{context}"
            )
            prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])
            question_answer_chain = create_stuff_documents_chain(llm, prompt)
            rag_chain = create_retrieval_chain(vectorstore.as_retriever(search_kwargs={"k": 6}), question_answer_chain)
            return rag_chain.invoke({"input": query})['answer']
        except Exception as e:
            print(f"Platform chat fallback triggered (Ollama might be offline): {e}")
            try:
                llm = cls._get_llm()
                return llm.invoke([SystemMessage(content="You are the Fatra Academy Assistant."), HumanMessage(content=query)]).content
            except Exception:
                return "I'm currently undergoing maintenance and can't access my full knowledge base. Please check back shortly or contact our support team!"

    @classmethod
    def get_learning_assistant_response(cls, query, context="", course_id=None):
        """Contextual learning assistant for students enrolled in courses."""
        try:
            llm = cls._get_llm(0.7)
            if course_id:
                try:
                    vectorstore = cls._get_vectorstore(f"course_{course_id}")
                    system_prompt = "You are a Learning Assistant. Use context:\n{context}"
                    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{input}")])
                    question_answer_chain = create_stuff_documents_chain(llm, prompt)
                    rag_chain = create_retrieval_chain(vectorstore.as_retriever(), question_answer_chain)
                    
                    input_data = f"Context: {context}\n\nQuestion: {query}" if context else query
                    return rag_chain.invoke({"input": input_data})['answer']
                except Exception as e:
                    print(f"Course RAG fallback: {e}")
            
            # Zero-shot fallback
            msg = f"Context: '{context}', Question: '{query}'" if context else query
            return llm.invoke([SystemMessage(content="You are a tutor."), HumanMessage(content=msg)]).content
        except Exception as e:
            print(f"Learning assistant critical failure (Ollama offline): {e}")
            return "I'm currently resting my circuits. Please try again in a few minutes when I'm back online!"

    @classmethod
    def generate_course_description(cls, title, audience=None, keywords=None):
        """Generates a course description for instructors."""
        llm = cls._get_llm(0.8)
        pt = f"Write a course description for '{title}'."
        if audience: pt += f" Target audience: {audience}."
        if keywords: pt += f" Include keywords: {keywords}."
        return llm.invoke([SystemMessage(content="You are a professional educational writer."), HumanMessage(content=pt)]).content

    @classmethod
    def summarize_content(cls, content):
        """Summarizes educational content for learners."""
        llm = cls._get_llm(0.5)
        pt = f"Summarize the following content in bullet points.\n\n{content}"
        return llm.invoke([SystemMessage(content="You summarize content concisely."), HumanMessage(content=pt)]).content

    @classmethod
    def generate_course_curriculum(cls, title):
        """Generates a suggested chapter and lesson structure for a course."""
        llm = cls._get_llm(0.7)
        pt = f"Suggest a curriculum with chapters and lessons for '{title}'. Format as clean text."
        return llm.invoke([SystemMessage(content="You are a curriculum designer."), HumanMessage(content=pt)]).content
