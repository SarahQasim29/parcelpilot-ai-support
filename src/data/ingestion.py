# src/data/ingestion.py
import os
import sys
import pandas as pd
from typing import List, Dict, Any
import logging

# ============================================
# WINDOWS PATCH - Fix for pwd module
# ============================================
if sys.platform == 'win32':
    class MockPwd:
        def getpwuid(self, uid):
            class User:
                pw_name = 'windows_user'
                pw_uid = uid
                pw_gid = 1000
                pw_dir = 'C:\\Users\\user'
                pw_shell = 'cmd.exe'
                pw_gecos = 'Windows User'
                pw_passwd = 'x'
            return User()
        def getpwnam(self, name):
            return self.getpwuid(1000)
        def getpwall(self):
            return []
    sys.modules['pwd'] = MockPwd()
    print("✅ Windows pwd module patched")
# ============================================

# LangChain imports - FIXED PATHS
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter  # ← FIXED
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

logger = logging.getLogger(__name__)

class DataIngestion:
    def __init__(self, config: Dict):
        self.config = config
        
        # Use FREE local embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        self.vector_store = Chroma(
            embedding_function=self.embeddings,
            persist_directory=config.get('CHROMA_PERSIST_DIRECTORY', './chroma_db'),
            collection_name="parcelpilot_docs"
        )
        self.structured_data = {}
    
    def load_documents(self, doc_path: str) -> List:
        """Load all PDF documents"""
        documents = []
        pdf_files = [
            "01_Support_Policy_v3_CURRENT.pdf",
            "02_Support_Policy_v2_DEPRECATED.pdf",
            "03_Cancellation_and_Service_Credit_SOP_v4.pdf",
            "04_Product_Operations_Guide_and_Known_Issues.pdf",
            "05_Northstar_Logistics_Enterprise_Agreement.pdf",
            "06_LumenWorks_Service_Agreement.pdf"
        ]
        
        reliability_scores = {
            "01_Support_Policy_v3_CURRENT.pdf": 1.0,
            "02_Support_Policy_v2_DEPRECATED.pdf": 0.3,
            "03_Cancellation_and_Service_Credit_SOP_v4.pdf": 0.9,
            "04_Product_Operations_Guide_and_Known_Issues.pdf": 0.8,
            "05_Northstar_Logistics_Enterprise_Agreement.pdf": 1.0,
            "06_LumenWorks_Service_Agreement.pdf": 1.0
        }
        
        for pdf_file in pdf_files:
            file_path = os.path.join(doc_path, pdf_file)
            if os.path.exists(file_path):
                try:
                    loader = PyPDFLoader(file_path)
                    docs = loader.load()
                    for doc in docs:
                        doc.metadata['source'] = pdf_file
                        doc.metadata['reliability'] = reliability_scores.get(pdf_file, 0.5)
                    documents.extend(docs)
                    logger.info(f"✅ Loaded {pdf_file}")
                except Exception as e:
                    logger.error(f"❌ Error loading {pdf_file}: {e}")
            else:
                logger.warning(f"⚠️ File not found: {file_path}")
        
        return documents
    
    def process_documents(self, documents: List):
        """Process and store documents in vector DB"""
        if not documents:
            logger.warning("No documents to process")
            return []
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        
        split_docs = text_splitter.split_documents(documents)
        logger.info(f"📄 Split into {len(split_docs)} chunks")
        
        # Add to vector store in batches
        batch_size = 10
        for i in range(0, len(split_docs), batch_size):
            batch = split_docs[i:i+batch_size]
            try:
                self.vector_store.add_documents(batch)
                logger.info(f"✅ Added {min(i+batch_size, len(split_docs))}/{len(split_docs)} chunks")
            except Exception as e:
                logger.error(f"❌ Error adding batch: {e}")
        
        self.vector_store.persist()
        logger.info("✅ Documents stored in ChromaDB")
        return split_docs
    
    def load_structured_data(self, data_path: str) -> Dict:
        """Load Excel data"""
        try:
            excel_file = os.path.join(data_path, "ParcelPilot_Assessment_Data.xlsx")
            if os.path.exists(excel_file):
                xls = pd.ExcelFile(excel_file)
                sheets = {}
                for sheet_name in xls.sheet_names:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    sheets[sheet_name] = df
                    logger.info(f"✅ Loaded sheet '{sheet_name}' with {len(df)} rows")
                self.structured_data = sheets
                return sheets
            else:
                logger.warning(f"⚠️ Excel file not found: {excel_file}")
        except Exception as e:
            logger.error(f"❌ Error loading Excel: {e}")
        return {}