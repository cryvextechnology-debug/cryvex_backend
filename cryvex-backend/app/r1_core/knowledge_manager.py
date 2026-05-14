import os
from typing import List
from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader, CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

import threading

class KnowledgeManager:
    def __init__(self, data_dir: str = "data", index_path: str = "data/faiss_index"):
        self.data_dir = data_dir
        self.index_path = index_path
        self.embeddings = None
        self.vector_store = None
        self._is_loading = False
        self._model_loaded = False

    def start_background_loading(self):
        """Called by FastAPI startup event to ensure Uvicorn is already serving."""
        if not self._is_loading and not self._model_loaded:
            threading.Thread(target=self._load_model, daemon=True).start()

    def _load_model(self):
        self._is_loading = True
        try:
            import time
            time.sleep(3) # Give ASGI server time to accept client connections before GIL locks
            print("KnowledgeManager: Loading HuggingFace embeddings in background...")
            self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            if os.path.exists(self.index_path):
                self.vector_store = FAISS.load_local(self.index_path, self.embeddings, allow_dangerous_deserialization=True)
            self._model_loaded = True
            print("KnowledgeManager: Model loaded successfully.")
        except Exception as e:
            print(f"Error loading model: {e}")
        finally:
            self._is_loading = False

    def vectorize_documents(self):
        """Processes files in data directory and updates the vector store."""
        if not self._model_loaded:
            print("KnowledgeManager: Engine is still warming up, cannot vectorize documents yet.")
            return

        documents = []
        
        # Define loaders for different file types
        loaders = {
            ".txt": DirectoryLoader(self.data_dir, glob="**/*.txt", loader_cls=TextLoader),
            ".pdf": DirectoryLoader(self.data_dir, glob="**/*.pdf", loader_cls=PyPDFLoader),
            ".csv": DirectoryLoader(self.data_dir, glob="**/*.csv", loader_cls=CSVLoader),
        }
        
        for ext, loader in loaders.items():
            try:
                documents.extend(loader.load())
            except Exception as e:
                print(f"Error loading {ext} files: {e}")

        if not documents:
            print("No documents found to vectorize.")
            return

        # Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = text_splitter.split_documents(documents)

        # Create or update vector store
        if self.vector_store is None:
            self.vector_store = FAISS.from_documents(chunks, self.embeddings)
        else:
            self.vector_store.add_documents(chunks)
            
        # Save index locally
        self.vector_store.save_local(self.index_path)
        print(f"Vectorized {len(chunks)} chunks from {len(documents)} documents.")

    def search_context(self, query: str, top_k: int = 3) -> str:
        """Retrieves relevant context for a given query."""
        if not self._model_loaded:
            return "Note: The knowledge engine is still warming up. Trying to load your response..."

        if self.vector_store is None:
            return "No context available (Vector store not initialized)."
            
        docs = self.vector_store.similarity_search(query, k=top_k)
        context = "\n\n".join([doc.page_content for doc in docs])
        return context

# Singleton instance
knowledge_manager = KnowledgeManager()
