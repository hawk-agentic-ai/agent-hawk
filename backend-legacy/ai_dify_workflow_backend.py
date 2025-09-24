"""
AI-First Dify Workflow Backend
Simple data extraction + Dify AI integration for I-U-R-T hedge workflows
Let AI handle ALL business logic, validations, and decisions
"""

import asyncio
import json
import hashlib
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
from supabase import create_client, Client
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI-First Dify Hedge Workflow API",
    description="Raw data extraction + Dify AI for complete I-U-R-T hedge workflows",
    version="4.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
DIFY_API_KEY = os.environ.get("DIFY_API_KEY", "app-sF86KavXxF9u2HwQx5JpM4TK")
DIFY_BASE_URL = "https://api.dify.ai/v1"
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

# Initialize services
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    supabase.table('hedge_instructions').select("instruction_id").limit(1).execute()
    SUPABASE_AVAILABLE = True
except:
    SUPABASE_AVAILABLE = False
    supabase = None

# =============================================================================
# SIMPLE REQUEST MODELS (Just pass data to AI)
# =============================================================================

class AIWorkflowRequest(BaseModel):
    workflow_type: str  # "inception", "utilisation", "rollover", "termination"
    entity_id: str
    user_prompt: str
    additional_context: Optional[Dict] = None

class DifyResponse(BaseModel):
    ai_response: str
    workflow_decisions: Optional[Dict] = None
    suggested_actions: Optional[List[str]] = None

# =============================================================================
# RAW DATA EXTRACTION (No business logic - just fetch data)
# =============================================================================

class HedgeDataExtractor:
    """Extract raw hedge data for AI processing"""
    
    @staticmethod
    async def get_entity_raw_data(entity_id: str) -> Dict:
        """Get all raw data for an entity - let AI decide what to do"""
        if not SUPABASE_AVAILABLE:
            return {"error": "Database unavailable"}
        
        try:
            raw_data = {}
            
            # Entity master data
            entity_result = supabase.table('entity_master').select('*').eq('entity_id', entity_id).execute()
            raw_data['entity_master'] = entity_result.data
            
            # All position data (no filtering - let AI decide)
            positions_result = supabase.table('position_nav_master').select('*').eq('entity_id', entity_id).execute()
            raw_data['positions'] = positions_result.data
            
            # All hedge instructions (past and present)
            instructions_result = supabase.table('hedge_instructions').select('*').execute()
            raw_data['all_hedge_instructions'] = [
                inst for inst in instructions_result.data 
                if any(pos.get('currency_code') == inst.get('exposure_currency') for pos in positions_result.data)
            ]
            
            # Business events history
            events_result = supabase.table('hedge_business_events').select('*').eq('entity_id', entity_id).execute()
            raw_data['business_events'] = events_result.data
            
            # Deal bookings
            deals_result = supabase.table('deal_bookings').select('*').execute()
            raw_data['deal_bookings'] = deals_result.data
            
            # GL entries
            gl_result = supabase.table('gl_entries').select('*').eq('entity_id', entity_id).execute()
            raw_data['gl_entries'] = gl_result.data
            
            return raw_data
            
        except Exception as e:
            logger.error(f"Data extraction failed: {e}")
            return {"error": str(e)}
    
    @staticmethod
    async def get_instruction_history(exposure_currency: str = None) -> Dict:
        """Get instruction history - let AI analyze patterns"""
        if not SUPABASE_AVAILABLE:
            return {"error": "Database unavailable"}
        
        try:
            query = supabase.table('hedge_instructions').select('*')
            if exposure_currency:
                query = query.eq('exposure_currency', exposure_currency)
            
            result = query.execute()
            return {
                "instruction_history": result.data,
                "total_count": len(result.data),
                "extracted_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {"error": str(e)}

# =============================================================================
# DIFY AI INTEGRATION (Send everything to AI)
# =============================================================================

class DifyAIProcessor:
    """Send data to Dify and get AI decisions"""
    
    @staticmethod
    async def send_to_dify(workflow_type: str, raw_data: Dict, user_prompt: str) -> Dict:
        """Send raw hedge data + user prompt to Dify AI"""
        
        # Build AI context with ALL available data
        ai_context = f"""
HEDGE WORKFLOW REQUEST: {workflow_type.upper()}
USER PROMPT: {user_prompt}

RAW HEDGE DATA:
=================

ENTITY MASTER DATA:
{json.dumps(raw_data.get('entity_master', []), indent=2)}

CURRENT POSITIONS:
{json.dumps(raw_data.get('positions', []), indent=2)}

HEDGE INSTRUCTION HISTORY:
{json.dumps(raw_data.get('all_hedge_instructions', []), indent=2)}

BUSINESS EVENTS:
{json.dumps(raw_data.get('business_events', []), indent=2)}

DEAL BOOKINGS:
{json.dumps(raw_data.get('deal_bookings', []), indent=2)}

GL ENTRIES:
{json.dumps(raw_data.get('gl_entries', []), indent=2)}

WORKFLOW CONTEXT:
- Template Type: {workflow_type}
- Request Time: {datetime.now().isoformat()}
- Database Records Available: {len(raw_data.get('positions', []))} positions, {len(raw_data.get('all_hedge_instructions', []))} instructions

INSTRUCTIONS FOR AI:
Please analyze this hedge fund data and provide your response for the {workflow_type} workflow.
Make all business decisions, validations, and recommendations.
Consider risk management, compliance, and operational efficiency.
"""

        try:
            # Send to Dify API
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {DIFY_API_KEY}',
                    'Content-Type': 'application/json'
                }
                
                payload = {
                    'inputs': {
                        'workflow_type': workflow_type,
                        'raw_data': json.dumps(raw_data),
                        'user_prompt': user_prompt,
                        'context': ai_context
                    },
                    'response_mode': 'blocking',
                    'user': f'hedge_trader_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
                }
                
                async with session.post(
                    f'{DIFY_BASE_URL}/chat-messages',
                    headers=headers,
                    json=payload
                ) as response:
                    
                    if response.status == 200:
                        dify_result = await response.json()
                        return {
                            "status": "success",
                            "ai_response": dify_result.get('answer', ''),
                            "conversation_id": dify_result.get('conversation_id'),
                            "message_id": dify_result.get('id'),
                            "dify_metadata": dify_result.get('metadata', {}),
                            "processed_at": datetime.now().isoformat()
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "status": "dify_error",
                            "error": f"Dify API error {response.status}: {error_text}",
                            "raw_response": error_text
                        }
                        
        except Exception as e:
            logger.error(f"Dify API call failed: {e}")
            return {
                "status": "connection_error",
                "error": str(e),
                "fallback_response": f"AI processing failed. Raw data available for manual processing: {len(raw_data)} data points."
            }

# =============================================================================
# AI-FIRST WORKFLOW ENDPOINTS
# =============================================================================

@app.post("/ai-workflow/inception")
async def ai_inception_workflow(request: AIWorkflowRequest):
    """
    AI INCEPTION WORKFLOW
    Extract data → Send to Dify AI → Return AI decisions
    """
    try:
        # Step 1: Extract ALL raw data (no filtering)
        raw_data = await HedgeDataExtractor.get_entity_raw_data(request.entity_id)
        
        if "error" in raw_data:
            raise HTTPException(status_code=503, detail=raw_data["error"])
        
        # Step 2: Send everything to Dify AI
        ai_result = await DifyAIProcessor.send_to_dify("inception", raw_data, request.user_prompt)
        
        # Step 3: Return AI response (no backend logic)
        return {
            "workflow": "AI_INCEPTION",
            "status": ai_result["status"],
            "ai_response": ai_result.get("ai_response", ""),
            "raw_data_summary": {
                "entity_records": len(raw_data.get('entity_master', [])),
                "position_records": len(raw_data.get('positions', [])),
                "instruction_records": len(raw_data.get('all_hedge_instructions', [])),
                "business_event_records": len(raw_data.get('business_events', [])),
                "deal_records": len(raw_data.get('deal_bookings', [])),
                "gl_records": len(raw_data.get('gl_entries', []))
            },
            "dify_metadata": ai_result.get("dify_metadata", {}),
            "user_prompt": request.user_prompt,
            "processing": {
                "backend_logic": "NONE - AI handles everything",
                "data_extraction": "Complete raw data provided to AI",
                "ai_processor": "Dify handles all business logic"
            }
        }
        
    except Exception as e:
        logger.error(f"AI inception workflow failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI workflow failed: {str(e)}")

@app.post("/ai-workflow/utilisation")
async def ai_utilisation_workflow(request: AIWorkflowRequest):
    """
    AI UTILISATION WORKFLOW  
    Let AI decide how to modify hedge utilisation
    """
    try:
        # Extract data + instruction history
        raw_data = await HedgeDataExtractor.get_entity_raw_data(request.entity_id)
        instruction_history = await HedgeDataExtractor.get_instruction_history()
        
        combined_data = {**raw_data, **instruction_history}
        
        # Send to Dify AI
        ai_result = await DifyAIProcessor.send_to_dify("utilisation", combined_data, request.user_prompt)
        
        return {
            "workflow": "AI_UTILISATION",
            "status": ai_result["status"],
            "ai_response": ai_result.get("ai_response", ""),
            "instruction_history_count": len(instruction_history.get("instruction_history", [])),
            "ai_decisions": "Handled by Dify AI agent",
            "user_prompt": request.user_prompt
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI utilisation failed: {str(e)}")

@app.post("/ai-workflow/rollover") 
async def ai_rollover_workflow(request: AIWorkflowRequest):
    """
    AI ROLLOVER WORKFLOW
    AI decides rollover strategy and execution
    """
    try:
        raw_data = await HedgeDataExtractor.get_entity_raw_data(request.entity_id)
        ai_result = await DifyAIProcessor.send_to_dify("rollover", raw_data, request.user_prompt)
        
        return {
            "workflow": "AI_ROLLOVER", 
            "status": ai_result["status"],
            "ai_response": ai_result.get("ai_response", ""),
            "rollover_analysis": "AI-driven maturity extension analysis",
            "user_prompt": request.user_prompt
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI rollover failed: {str(e)}")

@app.post("/ai-workflow/termination")
async def ai_termination_workflow(request: AIWorkflowRequest):
    """
    AI TERMINATION WORKFLOW
    AI handles position closure and P&L calculation
    """
    try:
        raw_data = await HedgeDataExtractor.get_entity_raw_data(request.entity_id)
        ai_result = await DifyAIProcessor.send_to_dify("termination", raw_data, request.user_prompt)
        
        return {
            "workflow": "AI_TERMINATION",
            "status": ai_result["status"], 
            "ai_response": ai_result.get("ai_response", ""),
            "termination_analysis": "AI-driven position closure and P&L analysis",
            "user_prompt": request.user_prompt
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI termination failed: {str(e)}")

@app.post("/ai-workflow/general")
async def ai_general_workflow(request: AIWorkflowRequest):
    """
    GENERAL AI WORKFLOW
    Any hedge-related prompt processed by AI
    """
    try:
        raw_data = await HedgeDataExtractor.get_entity_raw_data(request.entity_id)
        ai_result = await DifyAIProcessor.send_to_dify(request.workflow_type, raw_data, request.user_prompt)
        
        return {
            "workflow": f"AI_{request.workflow_type.upper()}",
            "status": ai_result["status"],
            "ai_response": ai_result.get("ai_response", ""),
            "workflow_type": request.workflow_type,
            "user_prompt": request.user_prompt,
            "ai_processing": "Full workflow handled by Dify AI"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI workflow failed: {str(e)}")

# =============================================================================
# SYSTEM STATUS AND HEALTH
# =============================================================================

@app.get("/ai/status")
def get_ai_system_status():
    """Get AI-first system status"""
    return {
        "version": "4.0.0",
        "system": "AI-First Dify Hedge Workflow System",
        "architecture": "Raw Data Extraction + AI Processing",
        "ai_capabilities": {
            "dify_integration": True,
            "raw_data_extraction": True,
            "ai_driven_workflows": True,
            "business_logic": "Handled by AI",
            "validations": "Handled by AI",
            "decision_making": "Handled by AI"
        },
        "workflow_support": {
            "inception": "AI-driven hedge initiation",
            "utilisation": "AI-driven position adjustments", 
            "rollover": "AI-driven maturity extensions",
            "termination": "AI-driven position closure",
            "general": "Any hedge workflow via AI"
        },
        "data_sources": {
            "supabase": "connected" if SUPABASE_AVAILABLE else "disconnected",
            "dify_api": f"configured with key: {DIFY_API_KEY[:10]}..." if DIFY_API_KEY else "not configured"
        },
        "processing_model": {
            "backend_logic": "MINIMAL - Just data extraction",
            "ai_processor": "Dify handles ALL business logic",
            "validations": "AI-driven validation",
            "workflows": "AI-driven execution"
        }
    }

@app.get("/health")
def health_check():
    """Health check for AI-first system"""
    return {
        "status": "healthy",
        "system_type": "ai_first_dify_workflows",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "fastapi": "online",
            "supabase": "connected" if SUPABASE_AVAILABLE else "disconnected", 
            "dify_api": "configured" if DIFY_API_KEY else "not_configured"
        },
        "ai_readiness": {
            "data_extraction": "ready",
            "dify_integration": "ready",
            "all_workflows": "AI-driven"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)