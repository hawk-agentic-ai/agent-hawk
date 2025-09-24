# HAWK Agent Prompt History Fix

## Problem Identified

The HAWK Agent module has two modes:
1. **Template Mode**: Uses form-based prompt templates
2. **Agent Mode**: Uses conversational AI interface

**Issue**: Agent Mode prompts were not appearing in the Prompt History because they were using a separate conversation system that wasn't integrated with the main prompt history tracking.

## Root Cause Analysis

1. **Template Mode** saves prompts to `hawk_agent_sessions` table via `HawkAgentSimpleService`
2. **Agent Mode** saves conversations to `hawk_agent_conversations` table via `HawkAgentConversationsService`  
3. **Prompt History** component only reads from `hawk_agent_sessions` table
4. The `hawk_agent_conversations` table was missing from the database schema

## Solution Implemented

### 1. Database Schema Fix
- Created `hawk-agent-conversations-schema.sql` to add the missing conversations table
- This preserves the conversational context for Agent Mode

### 2. Dual Tracking System
Modified `enhanced-prompt-templates-v2.component.ts` to save Agent Mode prompts to BOTH systems:
- **Conversations table**: For chat history and context (existing functionality)
- **Sessions table**: For unified prompt history tracking (new functionality)

### 3. Code Changes

#### In `sendAgentMessage()` method:
```typescript
// Generate session IDs for prompt history tracking
this.currentMsgUid = this.generateMsgUID();
this.currentInstructionId = this.generateInstructionId();

// Save to sessions table for prompt history tracking
await this.sessions.createSession(
  userPrompt,
  this.currentMsgUid,
  this.currentInstructionId,
  'agent',  // Mark as agent type
  0
);
```

#### Response handling:
```typescript
// Update session for prompt history tracking
await this.sessions.updateSession(this.currentMsgUid, {
  agent_status: 'completed',
  agent_end_time: new Date().toISOString(),
  agent_response: {
    text: fullResponse,
    backend_type: 'unified'
  }
});
```

#### Error handling:
```typescript
// Update session with error status
await this.sessions.updateSession(this.currentMsgUid, {
  agent_status: 'failed',
  agent_end_time: new Date().toISOString(),
  agent_response: {
    text: 'Error processing request',
    error: error.message,
    backend_type: 'unified'
  }
});
```

### 4. Service Updates

Modified `HawkAgentSimpleService.createSession()` to properly handle agent sessions:
```typescript
session_type: templateCategory === 'agent' ? 'agent' : 'template'
```

## Result

Now both Template Mode and Agent Mode prompts will appear in the Prompt History:
- Template Mode prompts: `session_type = 'template'`
- Agent Mode prompts: `session_type = 'agent'`

## Setup Required

1. **Run the database schema**:
   ```sql
   -- Execute the contents of hawk-agent-conversations-schema.sql
   ```

2. **No frontend changes needed** - the modifications are backward compatible

## Verification

After setup:
1. Submit a prompt in Template Mode → Should appear in Prompt History
2. Submit a message in Agent Mode → Should appear in Prompt History  
3. Both should be distinguished by their `session_type` field

The Prompt History component will now show all user interactions across both modes in a unified view.