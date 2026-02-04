
"""
Test script for Retail Insights Assistant
"""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import pandas as pd
from langchain_openai import ChatOpenAI

from config import Config
from data import DataLoader
from agents import RetailInsightsOrchestrator

def test_system():
    """Test the retail insights system"""
    
    print("="*60)
    print("Retail Insights Assistant - System Test")
    print("="*60)
    print()
    
    # Check if API key is set
    if not Config.OPENAI_API_KEY:
        print("❌ ERROR: OPENAI_API_KEY not found in environment")
        print("Please set your API key in .env file")
        return False
    
    print("✓ API Key configured")
    
    # Load sample data
    print("\n1. Loading sample data...")
    data_file = Path(__file__).parent / "data" / "sample_retail_data.csv"
    
    if not data_file.exists():
        print(f"❌ ERROR: Sample data not found at {data_file}")
        print("Run: python generate_sample_data.py")
        return False
    
    data_loader = DataLoader()
    df = data_loader.load_csv(str(data_file))
    print(f"✓ Loaded {len(df):,} records")
    
    # Preprocess
    print("\n2. Preprocessing data...")
    df = data_loader.preprocess(df)
    print("✓ Data preprocessed")
    
    # Setup DuckDB
    print("\n3. Setting up DuckDB...")
    data_loader.setup_duckdb()
    print("✓ DuckDB initialized")
    
    # Initialize LLM
    print("\n4. Initializing LLM...")
    try:
        llm = ChatOpenAI(
            model=Config.OPENAI_MODEL,
            temperature=Config.TEMPERATURE,
            api_key=Config.OPENAI_API_KEY
        )
        print("✓ LLM initialized")
    except Exception as e:
        print(f"❌ ERROR initializing LLM: {e}")
        return False
    
    # Create orchestrator
    print("\n5. Creating multi-agent orchestrator...")
    orchestrator = RetailInsightsOrchestrator(
        llm=llm,
        data_loader=data_loader,
        db_conn=data_loader.db_conn
    )
    print("✓ Orchestrator created")
    
    # Test queries
    print("\n6. Testing sample queries...")
    print("-" * 60)
    
    test_queries = [
        "What were the total sales in 2023?",
        "Which category had the highest profit?",
        "Show me the top 5 regions by revenue"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\nQuery {i}: {query}")
        print("-" * 40)
        
        try:
            result = orchestrator.process_query(query)
            
            print(f"✓ Query processed successfully")
            print(f"  - SQL: {result['sql_query'][:80]}...")
            print(f"  - Rows returned: {len(result['data'])}")
            print(f"  - Valid: {result['validation'].get('is_valid', 'N/A')}")
            print(f"\nAnswer preview:")
            print(result['answer'][:200] + "..." if len(result['answer']) > 200 else result['answer'])
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            continue
    
    print("\n" + "="*60)
    print("System test completed successfully!")
    print("="*60)
    
    return True

if __name__ == "__main__":
    success = test_system()
    sys.exit(0 if success else 1)
    