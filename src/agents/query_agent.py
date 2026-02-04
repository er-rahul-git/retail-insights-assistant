
"""
Query Resolution Agent - Converts natural language to structured queries
"""
import logging
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class QueryIntent(BaseModel):
    """Structured representation of query intent"""
    query_type: str = Field(description="Type of query: 'summary', 'comparison', 'trend', 'filter', 'aggregation'")
    entities: list[str] = Field(description="Main entities mentioned (products, regions, categories, etc.)")
    metrics: list[str] = Field(description="Metrics to analyze (sales, revenue, profit, growth, etc.)")
    time_period: Optional[str] = Field(description="Time period mentioned (Q1, 2023, YoY, etc.)", default=None)
    filters: Dict[str, Any] = Field(description="Filters to apply", default_factory=dict)
    aggregation: Optional[str] = Field(description="Aggregation method (sum, avg, max, min, count)", default=None)
    sort_by: Optional[str] = Field(description="Sort criteria", default=None)
    limit: Optional[int] = Field(description="Number of results to return", default=None)
    sql_query: Optional[str] = Field(description="Generated SQL query", default=None)


class QueryResolutionAgent:
    """Agent to resolve natural language queries to structured format"""
    
    def __init__(self, llm: ChatOpenAI, schema_description: str):
        """Initialize with LLM and data schema"""
        self.llm = llm
        self.schema_description = schema_description
        self.parser = PydanticOutputParser(pydantic_object=QueryIntent)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert data analyst specialized in converting natural language queries 
into structured query intents for retail sales data analysis.

Data Schema:
{schema_description}

Your task is to analyze the user's question and extract:
1. Query type (summary, comparison, trend, filter, aggregation)
2. Entities mentioned (products, regions, categories, time periods)
3. Metrics to analyze (sales, revenue, profit, growth rates)
4. Time periods and filters
5. Aggregation methods and sorting preferences
6. A SQL query that would answer the question using the available schema

Be precise and thorough in your analysis.

{format_instructions}"""),
            ("user", "{query}")
        ])
    
    def resolve_query(self, query: str) -> QueryIntent:
        """Resolve a natural language query to structured intent"""
        logger.info(f"Resolving query: {query}")
        
        try:
            chain = self.prompt | self.llm | self.parser
            
            result = chain.invoke({
                "query": query,
                "schema_description": self.schema_description,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            logger.info(f"Query resolved: {result.query_type}")
            return result
            
        except Exception as e:
            logger.error(f"Error resolving query: {e}")
            # Return a basic intent
            return QueryIntent(
                query_type="summary",
                entities=[],
                metrics=[],
                filters={}
            )
    
    def generate_sql(self, query: str, table_name: str = "sales_data") -> str:
        """Generate SQL query from natural language"""
        logger.info(f"Generating SQL for: {query}")
        
        sql_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a SQL expert. Generate a valid SQL query to answer the user's question.

Database Schema:
{schema_description}

Table name: {table_name}

Rules:
1. Use only columns that exist in the schema
2. Generate syntactically correct SQL
3. Use appropriate aggregations and filters
4. Include ORDER BY and LIMIT when relevant
5. Return ONLY the SQL query, no explanations"""),
            ("user", "{query}")
        ])
        
        try:
            chain = sql_prompt | self.llm
            
            result = chain.invoke({
                "query": query,
                "schema_description": self.schema_description,
                "table_name": table_name
            })
            
            sql = result.content.strip()
            # Clean up SQL (remove markdown code blocks if present)
            if sql.startswith("```"):
                sql = sql.split("```")[1]
                if sql.startswith("sql"):
                    sql = sql[3:]
                sql = sql.strip()
            
            logger.info(f"Generated SQL: {sql[:100]}...")
            return sql
            
        except Exception as e:
            logger.error(f"Error generating SQL: {e}")
            return f"SELECT * FROM {table_name} LIMIT 10"