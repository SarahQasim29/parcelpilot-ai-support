# src/tools/document_tools.py
from typing import List, Dict, Any
from langchain.tools import tool
from src.data.ingestion import DataIngestion
from src.auth.auth_manager import User
import logging

logger = logging.getLogger(__name__)

class DocumentTools:
    def __init__(self, data_ingestion: DataIngestion):
        self.data_ingestion = data_ingestion
    
    @tool
    def search_policies(self, query: str) -> str:
        """
        Search through policies, agreements, and documentation.
        Use this tool when you need to find information about:
        - Support policies
        - Cancellation procedures
        - Service credits
        - Customer agreements
        - Product operations
        
        Args:
            query: The search query string
        """
        try:
            # Search vector store
            results = self.data_ingestion.vector_store.similarity_search_with_score(
                query, k=5
            )
            
            if not results:
                return "No relevant documents found."
            
            # Format results with reliability scores
            formatted_results = []
            for doc, score in results:
                reliability = doc.metadata.get('reliability', 0.5)
                source = doc.metadata.get('source', 'Unknown')
                doc_type = doc.metadata.get('doc_type', 'unknown')
                
                # Only include high confidence results
                if score > 0.5:
                    formatted_results.append({
                        'content': doc.page_content[:500],
                        'source': source,
                        'doc_type': doc_type,
                        'reliability': reliability,
                        'relevance_score': score
                    })
            
            if not formatted_results:
                return "No relevant documents found with sufficient confidence."
            
            # Sort by reliability and relevance
            formatted_results.sort(
                key=lambda x: (x['reliability'], x['relevance_score']),
                reverse=True
            )
            
            # Build response
            response = "I found the following relevant information:\n\n"
            for i, result in enumerate(formatted_results[:3], 1):
                response += f"{i}. From {result['source']} "
                response += f"(Reliability: {result['reliability']:.1%}):\n"
                response += f"{result['content']}...\n\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error in search_policies: {str(e)}")
            return f"An error occurred while searching: {str(e)}"