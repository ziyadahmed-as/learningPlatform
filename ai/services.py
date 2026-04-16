import os
from django.conf import settings
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.docstore.document import Document
import json

# For dynamic RAG indexing
from django.apps import apps


class AIService:
    _vectorstore = None
    _course_vectorstores = {}       # Cache for course-specific RAG
    _recommendation_index = None    # Global catalog index for recommendations
    _recommendation_id_map = []     # Maps FAISS doc index → course id

    # ------------------------------------------------------------------
    # Recommendation helpers
    # ------------------------------------------------------------------

    @classmethod
    def initialize_recommendation_index(cls, force_refresh=False):
        """
        Builds (or returns cached) a FAISS index over all approved courses.
        Each document encodes the course title, category, and description so
        that semantic nearest-neighbour search reflects topical similarity.
        """
        if cls._recommendation_index and not force_refresh:
            return cls._recommendation_index

        Course = apps.get_model('courses', 'Course')
        courses = Course.objects.filter(is_approved=True).select_related('category')

        if not courses.exists():
            return None

        documents = []
        id_map = []

        for course in courses:
            category_name = course.category.name if course.category else 'General'
            text = (
                f"Title: {course.title}\n"
                f"Category: {category_name}\n"
                f"Description: {course.description}"
            )
            documents.append(Document(
                page_content=text,
                metadata={"course_id": course.id}
            ))
            id_map.append(course.id)

        embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url=settings.OLLAMA_BASE_URL)
        cls._recommendation_index = FAISS.from_documents(documents, embeddings)
        cls._recommendation_id_map = id_map
        return cls._recommendation_index

    @classmethod
    def get_course_recommendations(cls, user, limit=5):
        """
        Returns a list of Course objects semantically similar to the courses
        the student is already enrolled in, excluding those already enrolled.

        Falls back to the most recently approved courses when the student has
        no enrollments or the Ollama service is unavailable.
        """
        Course = apps.get_model('courses', 'Course')
        Enrollment = apps.get_model('interactions', 'Enrollment')

        enrolled_qs = Enrollment.objects.filter(student=user).select_related('course__category')
        enrolled_ids = list(enrolled_qs.values_list('course_id', flat=True))

        # Cold-start: student has no enrollments → return latest approved courses
        if not enrolled_ids:
            return list(
                Course.objects.filter(is_approved=True)
                .exclude(id__in=enrolled_ids)
                .order_by('-created_at')[:limit]
            )

        try:
            index = cls.initialize_recommendation_index()
        except Exception:
            # Ollama unreachable – graceful degradation
            index = None

        if not index:
            return list(
                Course.objects.filter(is_approved=True)
                .exclude(id__in=enrolled_ids)
                .order_by('-created_at')[:limit]
            )

        # Build a combined query from all enrolled courses
        query_parts = []
        for enr in enrolled_qs:
            c = enr.course
            cat = c.category.name if c.category else ''
            query_parts.append(f"{c.title} {cat} {c.description[:300]}")
        query_text = " ".join(query_parts)

        # Retrieve more than needed so we can filter out enrolled ones
        fetch_k = limit + len(enrolled_ids) + 5
        similar_docs = index.similarity_search(query_text, k=fetch_k)

        # Collect recommended course ids (preserve relevance order)
        seen = set()
        recommended_ids = []
        for doc in similar_docs:
            cid = doc.metadata.get('course_id')
            if cid and cid not in enrolled_ids and cid not in seen:
                seen.add(cid)
                recommended_ids.append(cid)
            if len(recommended_ids) >= limit:
                break

        if not recommended_ids:
            return list(
                Course.objects.filter(is_approved=True)
                .exclude(id__in=enrolled_ids)
                .order_by('-created_at')[:limit]
            )

        # Preserve relevance ordering using a Case/When expression
        from django.db.models import Case, When, IntegerField
        preserved_order = Case(
            *[When(id=cid, then=pos) for pos, cid in enumerate(recommended_ids)],
            output_field=IntegerField()
        )
        return list(
            Course.objects.filter(id__in=recommended_ids)
            .order_by(preserved_order)
        )


    @classmethod
    def initialize_rag(cls):
        """Initializes the vector store with all platform documents (md, txt, pdf)
        from the filesystem AND admin-uploaded KnowledgeDocuments from the DB."""
        if cls._vectorstore:
            return cls._vectorstore

        data_dir = os.path.join(settings.BASE_DIR, 'ai', 'data')
        os.makedirs(data_dir, exist_ok=True)

        # Ensure at least one file exists
        default_file = os.path.join(data_dir, 'platform_info.md')
        if not os.path.exists(default_file):
            with open(default_file, 'w', encoding='utf-8') as f:
                f.write("# Platform Information\n\nWelcome to Fatra Academy.")

        # Load all supported files from the data directory
        all_documents = []

        for filename in os.listdir(data_dir):
            filepath = os.path.join(data_dir, filename)
            if not os.path.isfile(filepath):
                continue

            try:
                if filename.endswith(('.md', '.txt')):
                    loader = TextLoader(filepath, encoding='utf-8')
                    all_documents.extend(loader.load())
                elif filename.endswith('.pdf'):
                    from langchain_community.document_loaders import PyPDFLoader
                    loader = PyPDFLoader(filepath)
                    all_documents.extend(loader.load())
            except Exception as e:
                print(f"[AIService] Warning: Could not load {filename}: {e}")

        # ----- Load admin-uploaded KnowledgeDocuments from DB -----
        try:
            KnowledgeDocument = apps.get_model('ai', 'KnowledgeDocument')
            for doc in KnowledgeDocument.objects.filter(is_active=True):
                try:
                    filepath = doc.file.path
                    ext = doc.file_extension
                    if ext in ('md', 'txt'):
                        loader = TextLoader(filepath, encoding='utf-8')
                        loaded = loader.load()
                    elif ext == 'pdf':
                        from langchain_community.document_loaders import PyPDFLoader
                        loader = PyPDFLoader(filepath)
                        loaded = loader.load()
                    else:
                        print(f"[AIService] Skipping unsupported format: {doc.filename}")
                        continue

                    # Tag each chunk with the document title for reference
                    for page in loaded:
                        page.metadata['knowledge_doc_id'] = doc.id
                        page.metadata['knowledge_doc_title'] = doc.title
                    all_documents.extend(loaded)
                except Exception as e:
                    print(f"[AIService] Warning: Could not load DB document '{doc.title}': {e}")
        except Exception as e:
            print(f"[AIService] Warning: Could not query KnowledgeDocument table: {e}")

        if not all_documents:
            return None

        # Split into chunks
        text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50, separator="\n")
        docs = text_splitter.split_documents(all_documents)

        if not docs:
            text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=0, separator=" ")
            docs = text_splitter.split_documents(all_documents)

        # Create vectorstore
        embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url=settings.OLLAMA_BASE_URL)
        cls._vectorstore = FAISS.from_documents(docs, embeddings)
        return cls._vectorstore

    @classmethod
    def initialize_course_rag(cls, course_id):
        """Initializes a specific vector store for a course."""
        if course_id in cls._course_vectorstores:
            return cls._course_vectorstores[course_id]

        Course = apps.get_model('courses', 'Course')
        Lesson = apps.get_model('courses', 'Lesson')
        ContentBlock = apps.get_model('courses', 'ContentBlock')

        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return None

        documents = []
        
        # Add course description
        documents.append(Document(
            page_content=f"Course: {course.title}\nDescription: {course.description}",
            metadata={"source": "course_description", "course_id": course_id}
        ))

        # Add chapter and lesson titles/descriptions
        lessons = Lesson.objects.filter(chapter__course_id=course_id)
        for lesson in lessons:
            content = f"Chapter: {lesson.chapter.title}\nLesson: {lesson.title}\nDescription: {lesson.description}"
            documents.append(Document(
                page_content=content,
                metadata={"source": "lesson_info", "lesson_id": lesson.id}
            ))
            
            # Add text content blocks
            blocks = ContentBlock.objects.filter(lesson=lesson, type='text')
            for block in blocks:
                if block.text_content:
                    # Clean simple HTML tags if present
                    import re
                    clean_text = re.sub('<[^<]+?>', '', block.text_content)
                    documents.append(Document(
                        page_content=f"Content from Lesson '{lesson.title}':\n{clean_text}",
                        metadata={"source": "content_block", "block_id": block.id}
                    ))

        if not documents:
            return None

        embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url=settings.OLLAMA_BASE_URL)
        vectorstore = FAISS.from_documents(documents, embeddings)
        cls._course_vectorstores[course_id] = vectorstore
        return vectorstore

    @classmethod
    def get_platform_chat_response(cls, query):
        """Answers questions about the platform using RAG."""
        # Force re-index so new platform_info.md content is always picked up
        cls._vectorstore = None
        vectorstore = cls.initialize_rag()
        if not vectorstore:
            return "Platform information is currently unavailable."

        llm = ChatOllama(model="llama3", temperature=0.7, base_url=settings.OLLAMA_BASE_URL)
        
        system_prompt = (
            "You are the Fatra Academy Assistant — a friendly, professional AI "
            "representative for the Fatra Academy online learning platform. "
            "Your job is to help anyone who visits the platform by answering "
            "questions about our services, courses, pricing, enrollment process, "
            "instructor onboarding, live streaming sessions, AI features, "
            "payments, and anything else related to the platform.\n\n"
            "Guidelines:\n"
            "- Be warm, welcoming, and helpful.\n"
            "- Use the provided context to give accurate answers.\n"
            "- If the user asks about a specific course or category, encourage "
            "them to browse our catalog or sign up.\n"
            "- If you don't know something, say so honestly and suggest they "
            "contact support.\n"
            "- Keep answers concise but informative.\n"
            "- Always end with an invitation to ask more questions.\n\n"
            "Platform context:\n{context}"
        )
        
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", "{input}"),
            ]
        )

        question_answer_chain = create_stuff_documents_chain(llm, prompt)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 6})
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)

        result = rag_chain.invoke({"input": query})
        return result['answer']

    @classmethod
    def generate_course_description(cls, title, audience=None, keywords=None):
        """Generates a course description for instructors."""
        llm = ChatOllama(model="llama3", temperature=0.8, base_url=settings.OLLAMA_BASE_URL)
        
        prompt_text = f"Help me write a professional and engaging course description for a course titled '{title}'."
        if audience:
            prompt_text += f" The target audience is {audience}."
        if keywords:
            prompt_text += f" Please include these keywords: {keywords}."
        
        prompt_text += "\n\nThe description should include an overview, what students will learn, and why they should take this course."
        
        messages = [
            SystemMessage(content="You are a professional educational content writer."),
            HumanMessage(content=prompt_text)
        ]
        
        response = llm.invoke(messages)
        return response.content


    @classmethod
    def summarize_content(cls, content):
        """Summarizes educational content for learners."""
        llm = ChatOllama(model="llama3", temperature=0.5, base_url=settings.OLLAMA_BASE_URL)
        
        prompt_text = (
            "Summarize the following educational content in a structured way using bullet points. "
            "Focus on the most important learning objectives and key takeaways.\n\n"
            f"Content:\n{content}"
        )
        
        messages = [
            SystemMessage(content="You are a concise educational content summarizer."),
            HumanMessage(content=prompt_text)
        ]
        
        response = llm.invoke(messages)
        return response.content

    @classmethod
    def get_learning_assistant_response(cls, query, context="", course_id=None):
        """Contextual learning assistant for students enrolled in courses."""
        llm = ChatOllama(model="llama3", temperature=0.7, base_url=settings.OLLAMA_BASE_URL)
        
        # Try RAG if course_id is provided
        if course_id:
            vectorstore = cls.initialize_course_rag(course_id)
            if vectorstore:
                system_prompt = (
                    "You are a dedicated Learning Assistant for a student. "
                    "Use the following pieces of context from the course to answer the student's question. "
                    "If you don't know the answer based on the context, answer using your general knowledge "
                    "but stay within the domain of the course material.\n\n"
                    "{context}"
                )
                
                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    ("human", "{input}"),
                ])

                question_answer_chain = create_stuff_documents_chain(llm, prompt)
                rag_chain = create_retrieval_chain(vectorstore.as_retriever(), question_answer_chain)
                
                # Combine manual context if provided
                input_data = {"input": query}
                if context:
                    input_data["input"] = f"Context: {context}\n\nQuestion: {query}"
                
                result = rag_chain.invoke(input_data)
                return result['answer']

        # Fallback to simple zero-shot if no RAG or it failed
        prompt_text = (
            "You are a dedicated Learning Assistant for a student. "
            f"Given this specific context from the course: '{context}', "
            f"please answer the student's question/query: '{query}'. "
            "If the question isn't directly related to the context, answer it using your general knowledge "
            "but try to stay within the domain of the course material."
        )
        
        messages = [
            SystemMessage(content="You are a professional tutor and learning mentor."),
            HumanMessage(content=prompt_text)
        ]
        
        response = llm.invoke(messages)
        return response.content

    @classmethod
    def generate_course_curriculum(cls, title):
        """Generates a suggested chapter and lesson structure for a course."""
        llm = ChatOllama(model="llama3", temperature=0.7, base_url=settings.OLLAMA_BASE_URL)
        
        prompt_text = (
            f"Generate a suggested curriculum for a course titled '{title}'. "
            "The curriculum should have 3-5 chapters, and each chapter should have 3-5 lessons. "
            "Format the response exactly as a JSON list of objects, where each object has: "
            "'chapter_title' and 'lessons' (a list of lesson titles)."
        )
        
        messages = [
            SystemMessage(content="You are a professional curriculum designer."),
            HumanMessage(content=prompt_text)
        ]
        
        response = llm.invoke(messages)
        try:
            content = response.content.replace('```json', '').replace('```', '').strip()
            return json.loads(content)
        except:
            return response.content
