
"""
Synthesis Agent - Generates natural language insights from data
"""
import logging
import pandas as pd
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

class SynthesisAgent:
    """Agent to synthesize insights and generate natural language responses"""
    
    def __init__(self, llm: ChatOpenAI):
        """Initialize with LLM"""
        self.llm = llm
        
        self.summary_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior business analyst providing insights from retail sales data.
Your task is to generate clear, actionable insights in natural language.

Guidelines:
1. Be concise but comprehensive
2. Highlight key findings and trends
3. Use business language, not technical jargon
4. Provide context and comparisons when relevant
5. Structure your response with clear sections
6. Include specific numbers and percentages
7. End with actionable recommendations when appropriate

Format your response in a professional, readable manner."""),
            ("user", """Question: {question}

Data Analysis Results:
{data_summary}

Validation Status:
{validation_status}

Please provide a comprehensive analysis and insights.""")
        ])
        
        self.conversational_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful data assistant for retail analytics. 
Answer questions naturally and conversationally while being accurate and informative.

Keep responses:
- Clear and direct
- Focused on the question asked
- Supported by the data
- Professional but friendly"""),
            ("user", """Question: {question}

Data Results:
{data_summary}

Please answer the question based on this data.""")
        ])
    
    def generate_summary(self, 
                        question: str, 
                        data: pd.DataFrame,
                        validation: Dict[str, Any]) -> str:
        """Generate comprehensive summary with insights"""
        logger.info("Generating comprehensive summary")
        
        # Create data summary
        data_summary = self._create_data_summary(data)
        
        # Validation status
        validation_status = self._format_validation(validation)
        
        try:
            chain = self.summary_prompt | self.llm
            
            response = chain.invoke({
                "question": question,
                "data_summary": data_summary,
                "validation_status": validation_status
            })
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return self._fallback_summary(question, data, validation)
    
    def generate_answer(self, 
                       question: str, 
                       data: pd.DataFrame) -> str:
        """Generate conversational answer to a question"""
        logger.info("Generating conversational answer")
        
        data_summary = self._create_data_summary(data)
        
        try:
            chain = self.conversational_prompt | self.llm
            
            response = chain.invoke({
                "question": question,
                "data_summary": data_summary
            })
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return self._fallback_answer(question, data)
    
    def _create_data_summary(self, df: pd.DataFrame, max_rows: int = 20) -> str:
        """Create a summary of the DataFrame"""
        if len(df) == 0:
            return "No data available"
        
        summary_parts = [
            f"Total Records: {len(df)}",
            f"Columns: {', '.join(df.columns)}",
            ""
        ]
        
        # Show sample data
        if len(df) <= max_rows:
            summary_parts.append("Complete Data:")
            summary_parts.append(df.to_string(index=False))
        else:
            summary_parts.append(f"Sample Data (first {max_rows} rows):")
            summary_parts.append(df.head(max_rows).to_string(index=False))
        
        summary_parts.append("")
        
        # Statistical summary for numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            summary_parts.append("Statistical Summary:")
            summary_parts.append(df[numeric_cols].describe().to_string())
        
        return '\n'.join(summary_parts)
    
    def _format_validation(self, validation: Dict[str, Any]) -> str:
        """Format validation results"""
        if not validation:
            return "Validation not performed"
        
        parts = [
            f"Valid: {validation.get('is_valid', False)}",
            f"Confidence: {validation.get('confidence', 0):.2%}",
            f"Quality Score: {validation.get('quality_score', 0):.2%}",
            f"Rows: {validation.get('row_count', 0)}",
            f"Columns: {validation.get('column_count', 0)}"
        ]
        
        issues = validation.get('issues', [])
        if issues:
            parts.append("\nIssues:")
            for issue in issues:
                parts.append(f"  - {issue}")
        
        suggestions = validation.get('suggestions', [])
        if suggestions:
            parts.append("\nSuggestions:")
            for suggestion in suggestions:
                parts.append(f"  - {suggestion}")
        
        return '\n'.join(parts)
    
    def _fallback_summary(self, question: str, data: pd.DataFrame, 
                         validation: Dict[str, Any]) -> str:
        """Fallback summary when LLM fails"""
        parts = [
            f"Analysis Results for: {question}",
            "",
            f"Data Summary:",
            f"  - Total records: {len(data)}",
            f"  - Columns: {', '.join(data.columns)}",
            ""
        ]
        
        if len(data) > 0:
            parts.append("Sample Data:")
            parts.append(data.head(5).to_string(index=False))
            parts.append("")
            
            numeric_cols = data.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                parts.append("Key Statistics:")
                for col in numeric_cols:
                    parts.append(
                        f"  {col}: Total = {data[col].sum():.2f}, "
                        f"Average = {data[col].mean():.2f}"
                    )
        
        return '\n'.join(parts)
    
    def _fallback_answer(self, question: str, data: pd.DataFrame) -> str:
        """Fallback answer when LLM fails"""
        if len(data) == 0:
            return f"I couldn't find any data to answer: {question}"
        
        return f"""Based on the data analysis:

{data.head(10).to_string(index=False)}

Total records found: {len(data)}

Please note: This is a simplified response. The system encountered an issue generating a detailed analysis."""