
"""
Vector store module for semantic search and retrieval
"""
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)

class VectorStore:
    """Vector store for semantic search using FAISS"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize vector store with embedding model"""
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatL2(self.dimension)
        self.documents = []
        self.metadata = []
    
    def add_documents(self, documents: List[str], metadata: Optional[List[Dict]] = None):
        """Add documents to the vector store"""
        logger.info(f"Adding {len(documents)} documents to vector store")
        
        # Generate embeddings
        embeddings = self.model.encode(documents, show_progress_bar=True)
        
        # Add to FAISS index
        self.index.add(np.array(embeddings).astype('float32'))
        
        # Store documents and metadata
        self.documents.extend(documents)
        if metadata:
            self.metadata.extend(metadata)
        else:
            self.metadata.extend([{}] * len(documents))
        
        logger.info(f"Total documents in store: {len(self.documents)}")
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        if len(self.documents) == 0:
            logger.warning("No documents in vector store")
            return []
        
        # Generate query embedding
        query_embedding = self.model.encode([query])
        
        # Search
        distances, indices = self.index.search(
            np.array(query_embedding).astype('float32'), 
            min(k, len(self.documents))
        )
        
        # Prepare results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.documents):
                results.append({
                    'document': self.documents[idx],
                    'metadata': self.metadata[idx],
                    'distance': float(dist),
                    'similarity': float(1 / (1 + dist))  # Convert distance to similarity
                })
        
        return results
    
    def save(self, path: str):
        """Save vector store to disk"""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.index, str(path / "faiss.index"))
        
        # Save documents and metadata
        with open(path / "documents.pkl", 'wb') as f:
            pickle.dump({
                'documents': self.documents,
                'metadata': self.metadata,
                'dimension': self.dimension
            }, f)
        
        logger.info(f"Vector store saved to {path}")
    
    def load(self, path: str):
        """Load vector store from disk"""
        path = Path(path)
        
        if not path.exists():
            raise ValueError(f"Path {path} does not exist")
        
        # Load FAISS index
        self.index = faiss.read_index(str(path / "faiss.index"))
        
        # Load documents and metadata
        with open(path / "documents.pkl", 'rb') as f:
            data = pickle.load(f)
            self.documents = data['documents']
            self.metadata = data['metadata']
            self.dimension = data['dimension']
        
        logger.info(f"Vector store loaded from {path}")
    
    def clear(self):
        """Clear all documents from the vector store"""
        self.index = faiss.IndexFlatL2(self.dimension)
        self.documents = []
        self.metadata = []
        logger.info("Vector store cleared")


class DocumentChunker:
    """Split documents into chunks for vector storage"""
    
    @staticmethod
    def chunk_dataframe_rows(df, chunk_size: int = 100) -> List[Dict[str, Any]]:
        """Convert DataFrame rows to text chunks"""
        chunks = []
        
        for i in range(0, len(df), chunk_size):
            chunk_df = df.iloc[i:i+chunk_size]
            
            # Create text representation
            text_parts = [
                f"Data summary for rows {i} to {i+len(chunk_df)}:",
                chunk_df.to_string(index=False)
            ]
            
            # Add summary statistics
            numeric_cols = chunk_df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                text_parts.append("\nNumeric summary:")
                text_parts.append(chunk_df[numeric_cols].describe().to_string())
            
            chunks.append({
                'text': '\n'.join(text_parts),
                'metadata': {
                    'start_row': i,
                    'end_row': i + len(chunk_df),
                    'num_records': len(chunk_df)
                }
            })
        
        return chunks
    
    @staticmethod
    def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap
        
        return chunks