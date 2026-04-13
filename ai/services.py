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
import json

class AIService:
    _vectorstore = None

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
    def generate_quiz(cls, topic, count=5, difficulty='medium'):
        """Generates a quiz based on a topic."""
        llm = ChatOllama(model="llama3", temperature=0.7)
        
        prompt_text = (
            f"Generate a quiz with {count} multiple-choice questions on the topic: '{topic}'. "
            f"Difficulty level: {difficulty}. "
            "Format the response as a JSON list of objects, each having: "
            "'question', 'options' (a list of 4 strings), and 'correct_answer' (one of the options)."
        )
        
        messages = [
            SystemMessage(content="You are an expert educational assessment creator."),
            HumanMessage(content=prompt_text)
        ]
        
        response = llm.invoke(messages)
        try:
            # Clean response if it contains markdown formatting
            content = response.content.replace('```json', '').replace('```', '').strip()
            return json.loads(content)
        except:
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
    def get_learning_assistant_response(cls, query, context=""):
        """Contextual learning assistant for students enrolled in courses."""
        llm = ChatOllama(model="llama3", temperature=0.7)
        
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
