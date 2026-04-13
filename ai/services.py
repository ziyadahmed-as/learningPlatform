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

        embeddings = OllamaEmbeddings(model="nomic-embed-text")
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
        """Initializes the vector store with platform information."""
        if cls._vectorstore:
            return cls._vectorstore

        data_path = os.path.join(settings.BASE_DIR, 'ai', 'data', 'platform_info.md')
        if not os.path.exists(data_path):
            # Create a dummy platform info if it doesn't exist
            os.makedirs(os.path.dirname(data_path), exist_ok=True)
            with open(data_path, 'w', encoding='utf-8') as f:
                f.write("# Platform Information\n\nWelcome to our professional learning platform.")

        # Load and split documents
        loader = TextLoader(data_path, encoding='utf-8')
        documents = loader.load()
        text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50, separator="\n")
        docs = text_splitter.split_documents(documents)
        
        if not docs:
            # Fallback if first split failed
            text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=0, separator=" ")
            docs = text_splitter.split_documents(documents)

        # Create or load vectorstore
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
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

        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        vectorstore = FAISS.from_documents(documents, embeddings)
        cls._course_vectorstores[course_id] = vectorstore
        return vectorstore

    @classmethod
    def get_platform_chat_response(cls, query):
        """Answers questions about the platform using RAG."""
        vectorstore = cls.initialize_rag()
        if not vectorstore:
            return "Platform information is currently unavailable."

        llm = ChatOllama(model="llama3", temperature=0.7)
        
        system_prompt = (
            "You are a helpful assistant for this learning platform. "
            "Use the following pieces of context to answer the user's question about the platform. "
            "If you don't know the answer based on the context, say that you don't know. "
            "Keep the answer concise and professional.\n\n"
            "{context}"
        )
        
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", "{input}"),
            ]
        )

        question_answer_chain = create_stuff_documents_chain(llm, prompt)
        rag_chain = create_retrieval_chain(vectorstore.as_retriever(), question_answer_chain)

        result = rag_chain.invoke({"input": query})
        return result['answer']

    @classmethod
    def generate_course_description(cls, title, audience=None, keywords=None):
        """Generates a course description for instructors."""
        llm = ChatOllama(model="llama3", temperature=0.8)
        
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
        llm = ChatOllama(model="llama3", temperature=0.5)
        
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
        llm = ChatOllama(model="llama3", temperature=0.7)
        
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
        llm = ChatOllama(model="llama3", temperature=0.7)
        
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
