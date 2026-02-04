"""
Streamlit UI for Retail Insights Assistant
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from data import DataLoader
from agents import RetailInsightsOrchestrator
from langchain_openai import ChatOpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Retail Insights Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #555;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .stButton>button {
        background-color: #1f77b4;
        color: white;
        border-radius: 0.5rem;
        padding: 0.5rem 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'data_loader' not in st.session_state:
    st.session_state.data_loader = None
if 'orchestrator' not in st.session_state:
    st.session_state.orchestrator = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False


def initialize_system():
    """Initialize the LLM and orchestrator"""
    try:
        llm = ChatOpenAI(
            model=Config.OPENAI_MODEL,
            temperature=Config.TEMPERATURE,
            api_key=Config.OPENAI_API_KEY
        )
        return llm
    except Exception as e:
        st.error(f"Error initializing LLM: {e}")
        return None


def load_data(file):
    """Load data from uploaded file"""
    try:
        # Save uploaded file
        upload_path = Config.UPLOAD_DIR / file.name
        with open(upload_path, 'wb') as f:
            f.write(file.getbuffer())
        
        # Load data
        data_loader = DataLoader()
        df = data_loader.auto_load(str(upload_path))
        df = data_loader.preprocess(df)
        
        # Setup DuckDB
        data_loader.setup_duckdb()
        
        return data_loader
    
    except Exception as e:
        st.error(f"Error loading data: {e}")
        logger.error(f"Data loading error: {e}", exc_info=True)
        return None


def display_data_overview(data_loader):
    """Display overview of loaded data"""
    if data_loader is None or data_loader.df is None:
        return
    
    df = data_loader.df
    
    st.subheader("📊 Data Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Records", f"{len(df):,}")
    
    with col2:
        st.metric("Columns", len(df.columns))
    
    with col3:
        numeric_cols = len(df.select_dtypes(include=['number']).columns)
        st.metric("Numeric Columns", numeric_cols)
    
    with col4:
        memory_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
        st.metric("Memory Usage", f"{memory_mb:.2f} MB")
    
    # Show sample data
    with st.expander("📋 View Sample Data"):
        st.dataframe(df.head(20), use_container_width=True)
    
    # Show column information
    with st.expander("📑 Column Information"):
        col_info = pd.DataFrame({
            'Column': df.columns,
            'Type': df.dtypes.astype(str),
            'Non-Null Count': df.count(),
            'Null Count': df.isnull().sum(),
            'Unique Values': df.nunique()
        })
        st.dataframe(col_info, use_container_width=True)


def display_visualizations(df):
    """Display basic visualizations"""
    if df is None or len(df) == 0:
        return
    
    st.subheader("📈 Quick Visualizations")
    
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    
    if len(numeric_cols) >= 2:
        col1, col2 = st.columns(2)
        
        with col1:
            # Bar chart for top values
            if len(numeric_cols) > 0:
                selected_col = st.selectbox("Select metric for bar chart", numeric_cols, key="bar")
                
                # Get categorical columns
                cat_cols = df.select_dtypes(include=['object']).columns.tolist()
                if cat_cols:
                    group_col = st.selectbox("Group by", cat_cols, key="group_bar")
                    
                    chart_data = df.groupby(group_col)[selected_col].sum().reset_index()
                    chart_data = chart_data.nlargest(10, selected_col)
                    
                    fig = px.bar(
                        chart_data,
                        x=group_col,
                        y=selected_col,
                        title=f"Top 10 {group_col} by {selected_col}"
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Histogram
            hist_col = st.selectbox("Select metric for distribution", numeric_cols, key="hist")
            
            fig = px.histogram(
                df,
                x=hist_col,
                title=f"Distribution of {hist_col}",
                nbins=30
            )
            st.plotly_chart(fig, use_container_width=True)


def chat_interface(orchestrator):
    """Chat interface for Q&A"""
    st.subheader("💬 Ask Questions About Your Data")
    
    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            
            if message["role"] == "assistant" and "data" in message:
                data = message["data"]
                if isinstance(data, pd.DataFrame) and len(data) > 0:
                    with st.expander("📊 View Data"):
                        st.dataframe(data, use_container_width=True)
    
    # Chat input
    user_question = st.chat_input("Ask a question about your retail data...")
    
    if user_question:
        # Add user message
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_question
        })
        
        with st.chat_message("user"):
            st.write(user_question)
        
        # Process query
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                try:
                    result = orchestrator.process_query(user_question)
                    
                    # Display answer
                    st.write(result["answer"])
                    
                    # Display data if available
                    if isinstance(result["data"], pd.DataFrame) and len(result["data"]) > 0:
                        with st.expander("📊 View Data"):
                            st.dataframe(result["data"], use_container_width=True)
                    
                    # Display SQL query
                    if result.get("sql_query"):
                        with st.expander("🔍 SQL Query"):
                            st.code(result["sql_query"], language="sql")
                    
                    # Display validation info
                    if result.get("validation"):
                        validation = result["validation"]
                        if not validation.get("is_valid"):
                            st.warning("⚠️ Query validation detected some issues")
                            if validation.get("issues"):
                                for issue in validation["issues"]:
                                    st.write(f"- {issue}")
                    
                    # Add to chat history
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": result["answer"],
                        "data": result["data"]
                    })
                    
                except Exception as e:
                    error_msg = f"Error processing query: {str(e)}"
                    st.error(error_msg)
                    logger.error(error_msg, exc_info=True)


def summary_mode(orchestrator):
    """Generate summary report"""
    st.subheader("📝 Generate Summary Report")
    
    if st.button("Generate Comprehensive Summary", type="primary"):
        with st.spinner("Generating summary report..."):
            try:
                summary = orchestrator.generate_summary()
                st.markdown(summary)
                
                # Option to download summary
                st.download_button(
                    label="Download Summary",
                    data=summary,
                    file_name="retail_insights_summary.txt",
                    mime="text/plain"
                )
                
            except Exception as e:
                st.error(f"Error generating summary: {e}")
                logger.error(f"Summary generation error: {e}", exc_info=True)


def main():
    """Main application"""
    
    # Header
    st.markdown('<p class="main-header">🏪 Retail Insights Assistant</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-Powered Analytics for Retail Sales Data</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Key check
        if not Config.OPENAI_API_KEY:
            st.error("⚠️ OpenAI API Key not found!")
            st.info("Please set OPENAI_API_KEY in your .env file")
            return
        
        st.success("✅ API Key configured")
        
        # File upload
        st.header("📁 Data Upload")
        uploaded_file = st.file_uploader(
            "Upload your sales data",
            type=['csv', 'xlsx', 'xls', 'json'],
            help="Supported formats: CSV, Excel, JSON"
        )
        
        if uploaded_file:
            if st.button("Load Data", type="primary"):
                with st.spinner("Loading and processing data..."):
                    data_loader = load_data(uploaded_file)
                    
                    if data_loader:
                        st.session_state.data_loader = data_loader
                        st.session_state.data_loaded = True
                        
                        # Initialize orchestrator
                        llm = initialize_system()
                        if llm:
                            st.session_state.orchestrator = RetailInsightsOrchestrator(
                                llm=llm,
                                data_loader=data_loader,
                                db_conn=data_loader.db_conn
                            )
                            st.success("✅ Data loaded successfully!")
                        else:
                            st.error("Failed to initialize LLM")
        
        # Mode selection
        if st.session_state.data_loaded:
            st.header("🎯 Mode")
            mode = st.radio(
                "Select mode",
                ["Q&A Mode", "Summary Mode"],
                help="Q&A for specific questions, Summary for comprehensive report"
            )
        
        # Clear chat history
        if st.button("Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()
    
    # Main content
    if not st.session_state.data_loaded:
        st.info("👈 Please upload your sales data to get started")
        
        # Example queries
        st.subheader("📚 Example Questions You Can Ask")
        
        examples = [
            "What were the total sales for Q3 2023?",
            "Which product category had the highest growth rate?",
            "Show me the top 10 performing regions by revenue",
            "What's the average order value by customer segment?",
            "Compare sales performance across different quarters",
            "Which products are underperforming?",
            "Show me sales trends over time",
            "What's the profit margin by product line?"
        ]
        
        for example in examples:
            st.markdown(f"- {example}")
    
    else:
        # Display data overview
        display_data_overview(st.session_state.data_loader)
        
        # Visualizations
        if st.session_state.data_loader.df is not None:
            display_visualizations(st.session_state.data_loader.df)
        
        st.divider()
        
        # Mode-specific interface
        if 'mode' in locals():
            if mode == "Q&A Mode":
                chat_interface(st.session_state.orchestrator)
            else:
                summary_mode(st.session_state.orchestrator)


if __name__ == "__main__":
    main()