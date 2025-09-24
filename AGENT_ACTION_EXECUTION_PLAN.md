# HAWK Agent Action Execution Plan
Agent-Driven Database Update Architecture for Full Operational Hedge Fund System

## PROJECT OVERVIEW

Transform HAWK Agent from read-only analysis to full operational system capable of executing database operations including hedge instructions, deal bookings, allocation engine updates, and configuration changes.

### Current Challenge
- System performs 47-51 database operations per complete hedge workflow
- 30-34 INSERT operations (hedge_instructions, deal_bookings, allocation_engine, audit_trail, gl_entries, etc.)
- 8 UPDATE operations (status tracking, booking confirmations)  
- 9 READ operations (validation, configuration)
- 3 Processing Stages: 1A (Instruction Processing), 1B (Business Events), 2 (Murex Booking)

### Proposed Solution: AI-Agent-Database Bridge
User Intent  AI Analysis  Action Recommendations  Approval Workflow  Database Execution  Confirmation

## ARCHITECTURAL DESIGN

### 1. Action Parsing Engine
Transform AI responses into structured database operations:

```python
# New Component: ActionExecutionEngine
class ActionExecutionEngine:
    def parse_ai_response(self, dify_response: str) -> List[DatabaseAction]:
        # Parse AI text into structured actions
        actions = []
        if "create hedge instruction" in response:
            actions.append(DatabaseAction(
                type="INSERT",
                table="hedge_instructions", 
                data={
                    "instruction_type": "INCEPTION",
                    "exposure_currency": "USD",
                    "hedge_amount_order": 25000000,
                    "entity_id": "extracted_entity"
                }
            ))
        return actions
```

### 2. Approval Workflow System
Multi-level approval for financial operations:

```python
class ApprovalWorkflow:
    def requires_approval(self, action: DatabaseAction) -> ApprovalLevel:
        if action.table == "deal_bookings" and action.data["notional_amount"] > 50000000:
            return ApprovalLevel.SENIOR_TRADER
        if action.table == "hedge_instructions":
            return ApprovalLevel.RISK_MANAGER
        return ApprovalLevel.AUTO_APPROVE
```

### 3. Transaction Management
Ensure atomicity across all 47-51 operations:

```python
class HedgeTransactionManager:
    async def execute_hedge_workflow(self, actions: List[DatabaseAction]):
        async with supabase.transaction():
            # Stage 1A: Process instruction (8 operations)
            await self.execute_stage_1a(actions.filter(stage="1A"))
            
            # Stage 1B: Business events (12 operations) 
            await self.execute_stage_1b(actions.filter(stage="1B"))
            
            # Stage 2: Murex booking (27-31 operations)
            await self.execute_stage_2(actions.filter(stage="2"))
```

## IMPLEMENTATION PLAN

### PHASE 1: Action Intelligence Layer (Week 1)

#### 1.1 Enhance Dify Prompt for Action Generation
Current: "Analyze CNY hedge capacity"  Analysis text
New: "Analyze CNY hedge capacity"  Analysis + Structured Actions JSON

Expected AI Response Format:
```json
{
  "analysis": "CNY hedge capacity is 150M based on...",
  "recommended_actions": [
    {
      "action_type": "CREATE_HEDGE_INSTRUCTION",
      "table": "hedge_instructions",
      "data": {
        "instruction_type": "INCEPTION",
        "exposure_currency": "CNY", 
        "hedge_amount_order": 150000000,
        "entity_id": "ENTITY001"
      },
      "approval_required": true,
      "risk_score": "MEDIUM"
    }
  ]
}
```

#### 1.2 Build Action Parser Component
```python
# New file: action_execution_engine.py
class ActionExecutionEngine:
    def parse_ai_actions(self, dify_response: dict) -> List[ExecutableAction]:
        actions = []
        for action in dify_response.get('recommended_actions', []):
            actions.append(ExecutableAction(
                type=action['action_type'],
                table=action['table'],
                operation=action.get('operation', 'INSERT'),
                data=action['data'],
                approval_level=self.get_approval_level(action),
                dependencies=action.get('dependencies', [])
            ))
        return actions
```

### PHASE 2: Approval Workflow Integration (Week 2)

#### 2.1 Multi-Level Approval System
```python
class ApprovalMatrix:
    APPROVAL_RULES = {
        "hedge_instructions": {
            "amount_threshold_1": (10_000_000, "TRADER_APPROVAL"),
            "amount_threshold_2": (50_000_000, "SENIOR_TRADER_APPROVAL"), 
            "amount_threshold_3": (100_000_000, "RISK_MANAGER_APPROVAL")
        },
        "deal_bookings": {
            "murex_booking": "AUTO_APPROVE",
            "manual_override": "OPERATIONS_APPROVAL"
        }
    }
```

#### 2.2 Frontend Approval Interface
```typescript
// Enhanced template-results.component.ts
interface ActionApproval {
  action_id: string;
  description: string;
  risk_assessment: string;
  approval_status: 'PENDING' | 'APPROVED' | 'REJECTED';
  approver_required: string;
}

// UI Component
<div *ngFor="let action of recommended_actions" class="action-approval-card">
  <h4>{{ action.description }}</h4>
  <p class="risk-level">Risk: {{ action.risk_assessment }}</p>
  <button (click)="approveAction(action)" [disabled]="!userCanApprove(action)">
    Approve & Execute
  </button>
  <button (click)="rejectAction(action)">Reject</button>
</div>
```

### PHASE 3: Database Execution Engine (Week 3)

#### 3.1 Transaction Management
```python
class HedgeTransactionManager:
    async def execute_approved_actions(self, actions: List[ExecutableAction]):
        transaction_id = generate_transaction_id()
        
        try:
            async with self.supabase.transaction():
                # Stage 1A: Hedge instruction processing
                if self.has_stage("1A", actions):
                    await self.execute_stage_1a(actions, transaction_id)
                
                # Stage 1B: Business events  
                if self.has_stage("1B", actions):
                    await self.execute_stage_1b(actions, transaction_id)
                    
                # Stage 2: Murex booking
                if self.has_stage("2", actions):
                    await self.execute_stage_2(actions, transaction_id)
                    
                # Create audit trail
                await self.create_audit_trail(transaction_id, actions)
                
        except Exception as e:
            await self.rollback_transaction(transaction_id)
            raise HedgeExecutionError(f"Failed to execute: {str(e)}")
```

#### 3.2 Specific Operation Handlers
```python
class DatabaseOperationHandler:
    async def create_hedge_instruction(self, action: ExecutableAction):
        result = await self.supabase.table('hedge_instructions').insert({
            'msg_uid': generate_msg_uid(),
            'instruction_type': action.data['instruction_type'],
            'exposure_currency': action.data['exposure_currency'],
            'hedge_amount_order': action.data['hedge_amount_order'],
            'entity_id': action.data['entity_id'],
            'check_status': 'PENDING',
            'created_by': 'HAWK_AGENT',
            'created_date': datetime.utcnow()
        }).execute()
        return result

    async def create_deal_booking(self, action: ExecutableAction):
        # Handle 6-10 deal booking operations per currency model
        deals = []
        for deal_config in action.data['deals']:
            deal = await self.supabase.table('deal_bookings').insert({
                'deal_id': generate_deal_id(),
                'event_id': action.data['event_id'],
                'deal_type': deal_config['deal_type'],
                'portfolio_from': deal_config['portfolio_from'],
                'portfolio_to': deal_config['portfolio_to'],
                'currency_pair': deal_config['currency_pair'],
                'notional_amount': deal_config['notional_amount'],
                'booking_status': 'PENDING'
            }).execute()
            deals.append(deal)
        return deals
```

### PHASE 4: Monitoring & Rollback (Week 4)

#### 4.1 Real-time Execution Monitoring
```python
class ExecutionMonitor:
    async def track_hedge_workflow(self, transaction_id: str):
        status = await self.supabase.table('execution_status').insert({
            'transaction_id': transaction_id,
            'total_operations': 47,  # or 51 depending on currency model
            'completed_operations': 0,
            'status': 'IN_PROGRESS',
            'stage_1a_status': 'PENDING',
            'stage_1b_status': 'PENDING', 
            'stage_2_status': 'PENDING'
        }).execute()
        
        # Stream progress to frontend
        yield f"data: {json.dumps({'progress': 0, 'status': 'Starting Stage 1A'})}\n\n"
```

#### 4.2 Intelligent Rollback System
```python
class RollbackManager:
    async def rollback_hedge_transaction(self, transaction_id: str):
        # Get all operations performed in this transaction
        operations = await self.get_transaction_operations(transaction_id)
        
        # Reverse operations in correct order
        for operation in reversed(operations):
            if operation.type == "INSERT":
                await self.delete_record(operation.table, operation.record_id)
            elif operation.type == "UPDATE":
                await self.restore_previous_value(operation.table, operation.record_id, operation.previous_value)
        
        # Mark transaction as rolled back
        await self.mark_transaction_rolled_back(transaction_id)
```

### PHASE 5: Full Integration (Week 5)

#### 5.1 Enhanced Backend Integration
```python
# Enhanced unified_smart_backend.py
@app.post("/hawk-agent/execute-actions")
async def execute_hedge_actions(request: ExecutableActionsRequest):
    try:
        # 1. Parse AI-recommended actions
        actions = action_engine.parse_ai_actions(request.ai_response)
        
        # 2. Apply approval workflow
        approved_actions = await approval_workflow.process_approvals(actions, request.user_id)
        
        # 3. Execute database operations with monitoring
        transaction_id = await transaction_manager.execute_approved_actions(approved_actions)
        
        # 4. Stream execution progress
        return StreamingResponse(execution_monitor.stream_progress(transaction_id))
        
    except Exception as e:
        await rollback_manager.rollback_hedge_transaction(transaction_id)
        raise HTTPException(status_code=500, detail=str(e))
```

#### 5.2 Frontend Action Execution Interface
```typescript
// New component: action-execution.component.ts
class ActionExecutionComponent {
    executeHedgeWorkflow(approvedActions: any[]) {
        const eventSource = new EventSource(`/hawk-agent/execute-actions`);
        
        eventSource.onmessage = (event) => {
            const progress = JSON.parse(event.data);
            this.updateExecutionProgress(progress);
            
            if (progress.completed) {
                this.showSuccessMessage(`Successfully executed ${progress.total_operations} operations`);
                eventSource.close();
            }
        };
        
        eventSource.onerror = (error) => {
            this.showErrorMessage('Execution failed. Transaction rolled back.');
            eventSource.close();
        };
    }
}
```

## TRANSFORMATION ROADMAP: Read-Only to Full Operational Agent

| Phase | Scope | Key Deliverables | Database Impact |
|-------|-------|------------------|----------------|
| Phase 1 | Action Intelligence | AI Action Parser, Enhanced Dify Prompt | READ-ONLY (analysis + action planning) |
| Phase 2 | Approval Workflows | Multi-level approval matrix, Frontend interface | READ-ONLY (approval tracking) |
| Phase 3 | Database Execution | Transaction manager, Operation handlers | FULL WRITE ACCESS |
| Phase 4 | Monitoring & Safety | Progress tracking, Rollback system | Write + Audit |
| Phase 5 | Integration | Complete end-to-end workflows | Production Ready |

## EXPECTED USER EXPERIENCE TRANSFORMATION

### BEFORE:
```
User: "Create USD 25M COI hedge"
Agent: "Analysis shows you can hedge 25M USD. Here's the capacity breakdown..."
User: [Has to manually create hedge instruction in separate system]
```

### AFTER:
```
User: "Create USD 25M COI hedge"  
Agent: "Analysis complete. Ready to execute:
        - Create hedge instruction (USD 25M)
        - Book 6 Murex deals (Model A-COI)
        - Generate GL entries (8 transactions)
        - Update allocation engine
        
        [Approve & Execute] [Review Details] [Cancel]"
User: [Clicks Approve & Execute]
Agent: "Successfully executed 47 database operations. 
        Hedge ORD-789 created and booked in Murex."
```

## RECOMMENDED IMPLEMENTATION SEQUENCE

### Week 1-2: Quick Win - Action Planning
- Enhance Dify prompt to include action recommendations
- Build action parser (no database writes yet)
- Show users "what would be executed" with approval interface

### Week 3-4: Core Execution Engine  
- Implement transaction management and database writers
- Build rollback capability
- Test with single-operation workflows first

### Week 5: Full Integration
- Complete multi-stage hedge workflows (47-51 operations)
- Real-time progress monitoring 
- Production deployment and testing

## RISK MITIGATION

1. **Approval Gates**: All financial operations require explicit approval
2. **Transaction Atomicity**: All-or-nothing execution across 47-51 operations
3. **Audit Trail**: Complete tracking of who approved what and when
4. **Rollback Capability**: Intelligent reversal of partial executions
5. **Graduated Rollout**: Start with low-risk operations, gradually increase scope

## KEY SUCCESS FACTORS

1. **Preserve Current Functionality**: All existing read-only analysis continues working
2. **Incremental Enhancement**: Add execution capability without breaking current system  
3. **User Control**: Clear approval workflows, never execute without explicit consent
4. **Comprehensive Testing**: Full end-to-end validation before production deployment
5. **Monitoring**: Real-time visibility into execution progress and system health

## CONCLUSION

This approach transforms HAWK Agent from a 6-10 minute analysis tool into a complete hedge fund operations platform capable of executing complex multi-stage workflows in under 2 seconds with full audit trails and approval controls.

The system maintains all current functionality while adding comprehensive operational capabilities through a phased implementation approach that minimizes risk and ensures user control over all financial operations.