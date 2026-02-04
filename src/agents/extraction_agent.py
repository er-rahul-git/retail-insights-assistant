
"""
Data Extraction Agent - Executes queries and retrieves data
"""
import logging
import pandas as pd
from typing import Dict, Any, Optional, List
import duckdb

logger = logging.getLogger(__name__)

class DataExtractionAgent:
    """Agent to extract data based on structured query intent"""
    
    def __init__(self, db_conn: duckdb.DuckDBPyConnection, df: pd.DataFrame):
        """Initialize with database connection and DataFrame"""
        self.db_conn = db_conn
        self.df = df
        self.last_query = None
        self.last_result = None
    
    def execute_sql(self, sql_query: str) -> pd.DataFrame:
        """Execute SQL query and return results"""
        logger.info(f"Executing SQL: {sql_query[:100]}...")
        
        try:
            result = self.db_conn.execute(sql_query).fetchdf()
            self.last_query = sql_query
            self.last_result = result
            logger.info(f"Query returned {len(result)} rows")
            return result
            
        except Exception as e:
            logger.error(f"SQL execution error: {e}")
            logger.error(f"Failed query: {sql_query}")
            raise
    
    def extract_by_intent(self, intent: Dict[str, Any]) -> pd.DataFrame:
        """Extract data based on query intent"""
        logger.info(f"Extracting data for intent type: {intent.get('query_type')}")
        
        query_type = intent.get('query_type', 'summary')
        
        if query_type == 'summary':
            return self._extract_summary(intent)
        elif query_type == 'comparison':
            return self._extract_comparison(intent)
        elif query_type == 'trend':
            return self._extract_trend(intent)
        elif query_type == 'filter':
            return self._extract_filtered(intent)
        elif query_type == 'aggregation':
            return self._extract_aggregation(intent)
        else:
            return self.df.head(10)
    
    def _extract_summary(self, intent: Dict[str, Any]) -> pd.DataFrame:
        """Extract summary data"""
        metrics = intent.get('metrics', [])
        
        if not metrics:
            # Return overall summary
            numeric_cols = self.df.select_dtypes(include=['number']).columns
            return self.df[numeric_cols].describe()
        
        # Summary with specific metrics
        result_data = {}
        for metric in metrics:
            if metric in self.df.columns:
                result_data[f'{metric}_total'] = [self.df[metric].sum()]
                result_data[f'{metric}_avg'] = [self.df[metric].mean()]
                result_data[f'{metric}_max'] = [self.df[metric].max()]
                result_data[f'{metric}_min'] = [self.df[metric].min()]
        
        return pd.DataFrame(result_data)
    
    def _extract_comparison(self, intent: Dict[str, Any]) -> pd.DataFrame:
        """Extract comparison data"""
        entities = intent.get('entities', [])
        metrics = intent.get('metrics', [])
        
        if not entities or not metrics:
            return self.df.head(10)
        
        # Try to find entity column
        entity_col = None
        for col in self.df.columns:
            if any(entity.lower() in col.lower() for entity in entities):
                entity_col = col
                break
        
        if not entity_col:
            return self.df.head(10)
        
        # Aggregate by entity
        metric_col = metrics[0] if metrics[0] in self.df.columns else None
        if metric_col:
            result = self.df.groupby(entity_col)[metric_col].sum().reset_index()
            result = result.sort_values(metric_col, ascending=False)
            return result
        
        return self.df.head(10)
    
    def _extract_trend(self, intent: Dict[str, Any]) -> pd.DataFrame:
        """Extract trend data"""
        metrics = intent.get('metrics', [])
        
        # Find date column
        date_col = None
        for col in self.df.columns:
            if self.df[col].dtype == 'datetime64[ns]' or 'date' in col.lower():
                date_col = col
                break
        
        if not date_col or not metrics:
            return self.df.head(10)
        
        metric_col = metrics[0] if metrics[0] in self.df.columns else None
        if metric_col:
            result = self.df.groupby(date_col)[metric_col].sum().reset_index()
            result = result.sort_values(date_col)
            return result
        
        return self.df.head(10)
    
    def _extract_filtered(self, intent: Dict[str, Any]) -> pd.DataFrame:
        """Extract filtered data"""
        filters = intent.get('filters', {})
        result = self.df.copy()
        
        for col, value in filters.items():
            if col in result.columns:
                result = result[result[col] == value]
        
        limit = intent.get('limit', 100)
        return result.head(limit)
    
    def _extract_aggregation(self, intent: Dict[str, Any]) -> pd.DataFrame:
        """Extract aggregated data"""
        entities = intent.get('entities', [])
        metrics = intent.get('metrics', [])
        aggregation = intent.get('aggregation', 'sum')
        
        if not entities or not metrics:
            return self.df.head(10)
        
        # Find entity column
        entity_col = None
        for col in self.df.columns:
            if any(entity.lower() in col.lower() for entity in entities):
                entity_col = col
                break
        
        if not entity_col:
            return self.df.head(10)
        
        # Apply aggregation
        metric_col = metrics[0] if metrics[0] in self.df.columns else None
        if metric_col:
            agg_func = getattr(self.df.groupby(entity_col)[metric_col], aggregation, 'sum')
            result = agg_func().reset_index()
            
            sort_by = intent.get('sort_by')
            if sort_by and sort_by in result.columns:
                result = result.sort_values(sort_by, ascending=False)
            
            limit = intent.get('limit', 100)
            return result.head(limit)
        
        return self.df.head(10)
    
    def get_context(self, max_rows: int = 5) -> str:
        """Get context from last extraction for the next agent"""
        if self.last_result is None or len(self.last_result) == 0:
            return "No data extracted yet."
        
        context_parts = [
            f"Query executed: {self.last_query[:200] if self.last_query else 'N/A'}",
            f"\nResult contains {len(self.last_result)} rows and {len(self.last_result.columns)} columns",
            f"\nColumns: {', '.join(self.last_result.columns)}",
            f"\nFirst {max_rows} rows:",
            self.last_result.head(max_rows).to_string(index=False)
        ]
        
        return '\n'.join(context_parts)