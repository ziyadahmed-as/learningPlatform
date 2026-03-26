import os
from django.conf import settings
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

class AIService:
    _vectorstore = None

    @classmethod
    def initialize_rag(cls):
        """Initializes the vector store with platform information."""
        if cls._vectorstore:
            return cls._vectorstore

        data_path = os.path.join(settings.BASE_DIR, 'ai', 'data', 'platform_info.md')
        if not os.path.exists(data_path):
            return None

        # Load and split documents
        loader = TextLoader(data_path, encoding='utf-8')
        documents = loader.load()
        text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        docs = text_splitter.split_documents(documents)

        # Create or load vectorstore
        embeddings = OpenAIEmbeddings(openai_api_key=os.getenv('OPENAI_API_KEY'))
        cls._vectorstore = FAISS.from_documents(docs, embeddings)
        return cls._vectorstore

    @classmethod
    def get_platform_chat_response(cls, query):
        """Answers questions about the platform using RAG."""
        vectorstore = cls.initialize_rag()
        if not vectorstore:
            return "Platform information is currently unavailable."

        llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.7, openai_api_key=os.getenv('OPENAI_API_KEY'))
        
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
        llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.8, openai_api_key=os.getenv('OPENAI_API_KEY'))
        
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
