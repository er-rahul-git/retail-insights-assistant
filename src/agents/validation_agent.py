
"""
Validation Agent - Validates query results and ensures quality
"""
import logging
import pandas as pd
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class ValidationResult(BaseModel):
    """Result of validation"""
    is_valid: bool = Field(description="Whether the result is valid")
    confidence: float = Field(description="Confidence score 0-1")
    issues: List[str] = Field(description="List of issues found", default_factory=list)
    suggestions: List[str] = Field(description="Suggestions for improvement", default_factory=list)
    quality_score: float = Field(description="Overall quality score 0-1")


class ValidationAgent:
    """Agent to validate query results and ensure data quality"""
    
    def __init__(self, llm: ChatOpenAI):
        """Initialize with LLM"""
        self.llm = llm
        
        self.validation_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a data quality expert. Your task is to validate query results 
and ensure they correctly answer the user's question.

Evaluate the following:
1. Does the data actually answer the user's question?
2. Is the data complete and not empty?
3. Are there any obvious data quality issues?
4. Does the result make business sense?
5. Are there any anomalies or outliers that need attention?

Provide a structured validation response with:
- is_valid: true/false
- confidence: 0-1 score
- issues: list of problems found
- suggestions: recommendations for improvement
- quality_score: overall quality 0-1

Be thorough but concise."""),
            ("user", """Original Question: {question}

Query Executed: {query}

Result Summary:
{result_summary}

Sample Data:
{sample_data}

Please validate this result.""")
        ])
    
    def validate_result(self, 
                       question: str, 
                       query: str, 
                       result: pd.DataFrame) -> Dict[str, Any]:
        """Validate query result"""
        logger.info("Validating query result")
        
        # Basic checks
        issues = []
        suggestions = []
        
        # Check if result is empty
        if len(result) == 0:
            issues.append("Result is empty - no data returned")
            suggestions.append("Review query filters or check if data exists for the criteria")
        
        # Check for null values
        null_counts = result.isnull().sum()
        if null_counts.sum() > 0:
            null_cols = null_counts[null_counts > 0].to_dict()
            issues.append(f"Null values found in columns: {null_cols}")
            suggestions.append("Consider handling null values or filtering them out")
        
        # Check for duplicate rows
        if len(result) != len(result.drop_duplicates()):
            duplicates = len(result) - len(result.drop_duplicates())
            issues.append(f"Found {duplicates} duplicate rows")
            suggestions.append("Consider removing duplicates or adding DISTINCT to query")
        
        # Prepare data summary
        result_summary = self._create_summary(result)
        sample_data = result.head(10).to_string(index=False) if len(result) > 0 else "No data"
        
        # LLM-based validation
        try:
            chain = self.validation_prompt | self.llm
            
            response = chain.invoke({
                "question": question,
                "query": query,
                "result_summary": result_summary,
                "sample_data": sample_data
            })
            
            validation_text = response.content
            
            # Parse response (simple parsing, could use structured output)
            is_valid = "is_valid: true" in validation_text.lower() or len(issues) == 0
            
            # Calculate confidence based on issues
            confidence = 1.0 - (len(issues) * 0.2)
            confidence = max(0.0, min(1.0, confidence))
            
            quality_score = confidence
            
        except Exception as e:
            logger.error(f"LLM validation error: {e}")
            is_valid = len(issues) == 0
            confidence = 0.7 if is_valid else 0.3
            quality_score = confidence
        
        return {
            "is_valid": is_valid,
            "confidence": confidence,
            "issues": issues,
            "suggestions": suggestions,
            "quality_score": quality_score,
            "row_count": len(result),
            "column_count": len(result.columns)
        }
    
    def _create_summary(self, df: pd.DataFrame) -> str:
        """Create a summary of the DataFrame"""
        if len(df) == 0:
            return "Empty DataFrame"
        
        summary_parts = [
            f"Rows: {len(df)}, Columns: {len(df.columns)}",
            f"Columns: {', '.join(df.columns)}"
        ]
        
        # Numeric summary
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            summary_parts.append("\nNumeric columns summary:")
            for col in numeric_cols:
                summary_parts.append(
                    f"  {col}: min={df[col].min():.2f}, "
                    f"max={df[col].max():.2f}, "
                    f"mean={df[col].mean():.2f}"
                )
        
        # Categorical summary
        categorical_cols = df.select_dtypes(include=['object']).columns
        if len(categorical_cols) > 0:
            summary_parts.append("\nCategorical columns:")
            for col in categorical_cols[:3]:  # Limit to first 3
                unique_count = df[col].nunique()
                summary_parts.append(f"  {col}: {unique_count} unique values")
        
        return '\n'.join(summary_parts)
    
    def check_anomalies(self, df: pd.DataFrame) -> List[str]:
        """Check for anomalies in numeric data"""
        anomalies = []
        
        numeric_cols = df.select_dtypes(include=['number']).columns
        
        for col in numeric_cols:
            # Check for extreme outliers using IQR method
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 3 * IQR
            upper_bound = Q3 + 3 * IQR
            
            outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
            
            if len(outliers) > 0:
                anomalies.append(
                    f"{col}: {len(outliers)} extreme outliers detected "
                    f"(range: {lower_bound:.2f} to {upper_bound:.2f})"
                )
        
        return anomalies
    
    def validate_business_logic(self, df: pd.DataFrame, 
                               rules: List[Dict[str, Any]]) -> List[str]:
        """Validate business logic rules"""
        violations = []
        
        for rule in rules:
            rule_type = rule.get('type')
            
            if rule_type == 'positive':
                # Check if values are positive
                col = rule.get('column')
                if col in df.columns:
                    negative_count = (df[col] < 0).sum()
                    if negative_count > 0:
                        violations.append(
                            f"{col} has {negative_count} negative values "
                            f"(expected all positive)"
                        )
            
            elif rule_type == 'range':
                # Check if values are within range
                col = rule.get('column')
                min_val = rule.get('min')
                max_val = rule.get('max')
                
                if col in df.columns:
                    out_of_range = df[(df[col] < min_val) | (df[col] > max_val)]
                    if len(out_of_range) > 0:
                        violations.append(
                            f"{col} has {len(out_of_range)} values outside "
                            f"expected range [{min_val}, {max_val}]"
                        )
        
        return violations