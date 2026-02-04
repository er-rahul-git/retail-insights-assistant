
"""
Data loading and processing module for retail sales data
"""
import pandas as pd
import duckdb
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class DataLoader:
    """Load and preprocess retail sales data"""
    
    def __init__(self):
        self.df = None
        self.db_conn = None
        
    def load_csv(self, filepath: str) -> pd.DataFrame:
        """Load CSV file"""
        try:
            logger.info(f"Loading CSV from {filepath}")
            self.df = pd.read_csv(filepath)
            logger.info(f"Loaded {len(self.df)} records with {len(self.df.columns)} columns")
            return self.df
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            raise
    
    def load_excel(self, filepath: str) -> pd.DataFrame:
        """Load Excel file"""
        try:
            logger.info(f"Loading Excel from {filepath}")
            self.df = pd.read_excel(filepath)
            logger.info(f"Loaded {len(self.df)} records with {len(self.df.columns)} columns")
            return self.df
        except Exception as e:
            logger.error(f"Error loading Excel: {e}")
            raise
    
    def load_json(self, filepath: str) -> pd.DataFrame:
        """Load JSON file"""
        try:
            logger.info(f"Loading JSON from {filepath}")
            with open(filepath, 'r') as f:
                data = json.load(f)
            self.df = pd.DataFrame(data)
            logger.info(f"Loaded {len(self.df)} records with {len(self.df.columns)} columns")
            return self.df
        except Exception as e:
            logger.error(f"Error loading JSON: {e}")
            raise
    
    def auto_load(self, filepath: str) -> pd.DataFrame:
        """Auto-detect file type and load"""
        path = Path(filepath)
        suffix = path.suffix.lower()
        
        if suffix == '.csv':
            return self.load_csv(filepath)
        elif suffix in ['.xlsx', '.xls']:
            return self.load_excel(filepath)
        elif suffix == '.json':
            return self.load_json(filepath)
        else:
            raise ValueError(f"Unsupported file type: {suffix}")
    
    def preprocess(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Preprocess the data"""
        if df is None:
            df = self.df
        
        if df is None:
            raise ValueError("No data loaded")
        
        logger.info("Starting preprocessing")
        
        # Make a copy
        df = df.copy()
        
        # Convert date columns
        date_columns = df.select_dtypes(include=['object']).columns
        for col in date_columns:
            if 'date' in col.lower():
                try:
                    df[col] = pd.to_datetime(df[col])
                    logger.info(f"Converted {col} to datetime")
                except:
                    pass
        
        # Handle missing values
        numeric_cols = df.select_dtypes(include=['number']).columns
        df[numeric_cols] = df[numeric_cols].fillna(0)
        
        categorical_cols = df.select_dtypes(include=['object']).columns
        df[categorical_cols] = df[categorical_cols].fillna('Unknown')
        
        self.df = df
        logger.info("Preprocessing complete")
        return df
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics of the dataset"""
        if self.df is None:
            raise ValueError("No data loaded")
        
        stats = {
            'total_records': len(self.df),
            'columns': list(self.df.columns),
            'numeric_columns': list(self.df.select_dtypes(include=['number']).columns),
            'categorical_columns': list(self.df.select_dtypes(include=['object']).columns),
            'date_columns': list(self.df.select_dtypes(include=['datetime']).columns),
            'missing_values': self.df.isnull().sum().to_dict(),
            'memory_usage_mb': self.df.memory_usage(deep=True).sum() / 1024 / 1024
        }
        
        return stats
    
    def setup_duckdb(self, table_name: str = "sales_data") -> duckdb.DuckDBPyConnection:
        """Setup DuckDB for efficient querying"""
        if self.df is None:
            raise ValueError("No data loaded")
        
        logger.info("Setting up DuckDB")
        self.db_conn = duckdb.connect(':memory:')
        self.db_conn.register(table_name, self.df)
        logger.info(f"Registered DataFrame as '{table_name}' in DuckDB")
        
        return self.db_conn
    
    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute SQL query using DuckDB"""
        if self.db_conn is None:
            self.setup_duckdb()
        
        try:
            result = self.db_conn.execute(query).fetchdf()
            logger.info(f"Query executed successfully, returned {len(result)} rows")
            return result
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise
    
    def get_schema_description(self) -> str:
        """Get a natural language description of the schema"""
        if self.df is None:
            raise ValueError("No data loaded")
        
        description_parts = [
            f"Dataset contains {len(self.df):,} records with {len(self.df.columns)} columns.",
            "\nColumns and their types:"
        ]
        
        for col in self.df.columns:
            dtype = str(self.df[col].dtype)
            sample_values = self.df[col].dropna().head(3).tolist()
            description_parts.append(
                f"- {col} ({dtype}): Sample values: {sample_values}"
            )
        
        return "\n".join(description_parts)


class DataAggregator:
    """Aggregate and summarize retail data"""
    
    @staticmethod
    def aggregate_by_dimension(df: pd.DataFrame, dimension: str, 
                               metrics: List[str]) -> pd.DataFrame:
        """Aggregate data by a dimension"""
        if dimension not in df.columns:
            raise ValueError(f"Dimension '{dimension}' not found in data")
        
        agg_dict = {metric: 'sum' for metric in metrics if metric in df.columns}
        
        if not agg_dict:
            raise ValueError("No valid metrics found")
        
        result = df.groupby(dimension).agg(agg_dict).reset_index()
        return result
    
    @staticmethod
    def calculate_growth(df: pd.DataFrame, time_col: str, 
                        value_col: str, dimension: Optional[str] = None) -> pd.DataFrame:
        """Calculate period-over-period growth"""
        df = df.sort_values(time_col)
        
        if dimension:
            df['growth_rate'] = df.groupby(dimension)[value_col].pct_change() * 100
        else:
            df['growth_rate'] = df[value_col].pct_change() * 100
        
        return df
    
    @staticmethod
    def get_top_n(df: pd.DataFrame, column: str, n: int = 10, 
                  ascending: bool = False) -> pd.DataFrame:
        """Get top N records by a column"""
        return df.nlargest(n, column) if not ascending else df.nsmallest(n, column)