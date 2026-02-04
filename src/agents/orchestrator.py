
"""
Multi-Agent Orchestrator using LangGraph
"""
import logging
from typing import TypedDict, Annotated, Sequence
import operator
import pandas as pd
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from .query_agent import QueryResolutionAgent
from .extraction_agent import DataExtractionAgent
from .validation_agent import ValidationAgent
from .synthesis_agent import SynthesisAgent

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    """State shared between agents"""
    question: str
    query_intent: dict
    sql_query: str
    extracted_data: pd.DataFrame
    validation_result: dict
    final_answer: str
    messages: Annotated[Sequence[str], operator.add]
    error: str


class RetailInsightsOrchestrator:
    """Orchestrator for multi-agent retail insights system"""
    
    def __init__(self, 
                 llm: ChatOpenAI,
                 data_loader,
                 db_conn):
        """Initialize orchestrator with agents"""
        self.llm = llm
        self.data_loader = data_loader
        self.db_conn = db_conn
        
        # Initialize agents
        schema_description = data_loader.get_schema_description()
        
        self.query_agent = QueryResolutionAgent(llm, schema_description)
        self.extraction_agent = DataExtractionAgent(db_conn, data_loader.df)
        self.validation_agent = ValidationAgent(llm)
        self.synthesis_agent = SynthesisAgent(llm)
        
        # Build workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the agent workflow graph"""
        workflow = StateGraph(AgentState)
        
        # Add nodes for each agent
        workflow.add_node("query_resolution", self._query_resolution_node)
        workflow.add_node("data_extraction", self._data_extraction_node)
        workflow.add_node("validation", self._validation_node)
        workflow.add_node("synthesis", self._synthesis_node)
        
        # Define edges
        workflow.set_entry_point("query_resolution")
        workflow.add_edge("query_resolution", "data_extraction")
        workflow.add_edge("data_extraction", "validation")
        workflow.add_edge("validation", "synthesis")
        workflow.add_edge("synthesis", END)
        
        return workflow.compile()
    
    def _query_resolution_node(self, state: AgentState) -> AgentState:
        """Query resolution agent node"""
        logger.info("=== Query Resolution Agent ===")
        
        try:
            question = state["question"]
            
            # Resolve query intent
            intent = self.query_agent.resolve_query(question)
            
            # Generate SQL
            sql_query = self.query_agent.generate_sql(question)
            
            state["query_intent"] = intent.dict()
            state["sql_query"] = sql_query
            state["messages"] = [f"Query resolved: {intent.query_type}"]
            
            logger.info(f"Query type: {intent.query_type}")
            logger.info(f"SQL generated: {sql_query[:100]}...")
            
        except Exception as e:
            logger.error(f"Query resolution error: {e}")
            state["error"] = f"Query resolution failed: {str(e)}"
            state["messages"] = [f"Error in query resolution: {str(e)}"]
        
        return state
    
    def _data_extraction_node(self, state: AgentState) -> AgentState:
        """Data extraction agent node"""
        logger.info("=== Data Extraction Agent ===")
        
        try:
            sql_query = state.get("sql_query")
            
            if not sql_query:
                raise ValueError("No SQL query generated")
            
            # Execute query
            result = self.extraction_agent.execute_sql(sql_query)
            
            state["extracted_data"] = result
            state["messages"] = [f"Extracted {len(result)} rows"]
            
            logger.info(f"Extracted {len(result)} rows, {len(result.columns)} columns")
            
        except Exception as e:
            logger.error(f"Data extraction error: {e}")
            state["error"] = f"Data extraction failed: {str(e)}"
            state["messages"] = [f"Error in data extraction: {str(e)}"]
            # Provide empty DataFrame as fallback
            state["extracted_data"] = pd.DataFrame()
        
        return state
    
    def _validation_node(self, state: AgentState) -> AgentState:
        """Validation agent node"""
        logger.info("=== Validation Agent ===")
        
        try:
            question = state["question"]
            sql_query = state.get("sql_query", "")
            data = state.get("extracted_data", pd.DataFrame())
            
            # Validate result
            validation = self.validation_agent.validate_result(
                question, sql_query, data
            )
            
            state["validation_result"] = validation
            state["messages"] = [
                f"Validation complete: "
                f"Valid={validation['is_valid']}, "
                f"Quality={validation['quality_score']:.2%}"
            ]
            
            logger.info(f"Validation: {validation['is_valid']}, "
                       f"Confidence: {validation['confidence']:.2%}")
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            state["error"] = f"Validation failed: {str(e)}"
            state["messages"] = [f"Error in validation: {str(e)}"]
            state["validation_result"] = {
                "is_valid": False,
                "confidence": 0.0,
                "quality_score": 0.0,
                "issues": [str(e)]
            }
        
        return state
    
    def _synthesis_node(self, state: AgentState) -> AgentState:
        """Synthesis agent node"""
        logger.info("=== Synthesis Agent ===")
        
        try:
            question = state["question"]
            data = state.get("extracted_data", pd.DataFrame())
            validation = state.get("validation_result", {})
            
            # Generate final answer
            if len(data) > 0:
                answer = self.synthesis_agent.generate_summary(
                    question, data, validation
                )
            else:
                answer = "I couldn't find any data to answer your question. Please try rephrasing or check if the data exists."
            
            state["final_answer"] = answer
            state["messages"] = ["Answer generated successfully"]
            
            logger.info("Synthesis complete")
            
        except Exception as e:
            logger.error(f"Synthesis error: {e}")
            state["error"] = f"Synthesis failed: {str(e)}"
            state["messages"] = [f"Error in synthesis: {str(e)}"]
            state["final_answer"] = f"I encountered an error while generating the answer: {str(e)}"
        
        return state
    
    def process_query(self, question: str) -> dict:
        """Process a user query through the agent workflow"""
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing query: {question}")
        logger.info(f"{'='*60}\n")
        
        # Initialize state
        initial_state = {
            "question": question,
            "query_intent": {},
            "sql_query": "",
            "extracted_data": pd.DataFrame(),
            "validation_result": {},
            "final_answer": "",
            "messages": [],
            "error": ""
        }
        
        try:
            # Run workflow
            final_state = self.workflow.invoke(initial_state)
            
            return {
                "question": question,
                "answer": final_state.get("final_answer", "No answer generated"),
                "data": final_state.get("extracted_data", pd.DataFrame()),
                "validation": final_state.get("validation_result", {}),
                "sql_query": final_state.get("sql_query", ""),
                "messages": final_state.get("messages", []),
                "error": final_state.get("error", "")
            }
            
        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            return {
                "question": question,
                "answer": f"An error occurred while processing your question: {str(e)}",
                "data": pd.DataFrame(),
                "validation": {},
                "sql_query": "",
                "messages": [],
                "error": str(e)
            }
    
    def generate_summary(self) -> str:
        """Generate overall data summary"""
        logger.info("Generating overall summary")
        
        try:
            # Get summary statistics
            stats = self.data_loader.get_summary_stats()
            
            summary_question = (
                "Provide a comprehensive summary of the retail sales data, "
                "including key metrics, trends, and insights."
            )
            
            result = self.process_query(summary_question)
            return result["answer"]
            
        except Exception as e:
            logger.error(f"Summary generation error: {e}")
            return f"Error generating summary: {str(e)}"