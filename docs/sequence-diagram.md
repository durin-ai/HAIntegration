# Home Assistant Cloud Integration - Sequence Diagrams

This document contains detailed sequence diagrams for the major flows in the Home Assistant Cloud Integration system.

## 1. Installation Registration Flow

```mermaid
sequenceDiagram
    participant U as User
    participant HA as Home Assistant UI
    participant INT as Cloud Integration
    participant API as API Gateway
    participant REG as Register Lambda
    participant DB as DynamoDB
    participant EB as EventBridge

    U->>HA: Add Integration
    HA->>U: Show config form
    U->>HA: Enter API key & URL
    HA->>INT: Start config flow
    
    INT->>API: POST /ha/register
    Note over INT,API: {"api_key": "user-key"}
    
    API->>REG: Invoke function
    REG->>REG: Validate API key format
    REG->>REG: Hash API key (SHA-256)
    REG->>REG: Generate installation_id (UUID)
    REG->>REG: Generate webhook_id (UUID)
    
    REG->>DB: Store installation
    Note over REG,DB: PK: INSTALL#{id}, SK: METADATA
    
    REG->>EB: Emit registration event
    Note over REG,EB: InstallationRegistered
    
    REG->>API: Return success
    Note over REG,API: {installation_id, webhook_id, webhook_url}
    
    API->>INT: 200 OK
    INT->>HA: Config entry created
    HA->>U: Integration configured
    
    INT->>INT: Schedule initial sync
```

## 2. Device Synchronization Flow

```mermaid
sequenceDiagram
    participant INT as Cloud Integration
    participant DR as Device Registry
    participant ER as Entity Registry
    participant STATE as State Machine
    participant API as API Gateway
    participant SYNC as Sync Lambda
    participant DB as DynamoDB
    participant EB as EventBridge

    Note over INT: Periodic sync timer (5 min)
    INT->>DR: Get all devices
    DR->>INT: Return device list
    
    INT->>ER: Get entities for devices
    ER->>INT: Return entity registry
    
    loop For each entity
        INT->>STATE: Get current state
        STATE->>INT: Return entity state & attributes
    end
    
    INT->>INT: Build device payload
    Note over INT: Group entities by device
    
    INT->>API: POST /ha/sync
    Note over INT,API: Authorization: Bearer {api_key}
    Note over INT,API: {installation_id, devices[]}
    
    API->>SYNC: Invoke function
    SYNC->>DB: Verify installation
    Note over SYNC,DB: Check installation_id exists
    
    SYNC->>SYNC: Validate API key hash
    
    loop For each device
        SYNC->>DB: Store device data
        Note over SYNC,DB: PK: INSTALL#{id}, SK: DEVICE#{device_id}
        
        loop For each entity
            SYNC->>DB: Store entity state
            Note over SYNC,DB: PK: INSTALL#{id}, SK: ENTITY#{entity_id}
        end
    end
    
    SYNC->>DB: Update sync timestamp
    Note over SYNC,DB: Update last_sync in METADATA
    
    SYNC->>EB: Emit sync event
    Note over SYNC,EB: DevicesSynced with entity list
    
    SYNC->>API: Return summary
    Note over SYNC,API: {synced_devices, synced_entities, timestamp}
    
    API->>INT: 200 OK
    INT->>INT: Log sync success
```

## 3. Command Execution Flow (Cloud to Home Assistant)

```mermaid
sequenceDiagram
    participant EXT as External Service
    participant API as API Gateway
    participant WH as Webhook Lambda
    participant DB as DynamoDB
    participant EB as EventBridge
    participant INT as Cloud Integration
    participant HA as Home Assistant

    EXT->>API: POST /webhook/{webhook_id}
    Note over EXT,API: {"type": "command", "action": "turn_on", "entity_id": "light.living_room"}
    
    API->>WH: Invoke function
    WH->>DB: Verify webhook_id
    Note over WH,DB: Find installation by webhook_id
    
    alt Webhook found
        WH->>WH: Process command
        WH->>EB: Emit command event
        Note over WH,EB: CommandSent event
        
        WH->>API: Return success
        Note over WH,API: {"status": "ok", "command_received": true}
        
        API->>EXT: 200 OK
        
        Note over INT: Integration polling for commands (future enhancement)
        Note over HA: Command would be executed locally
        
    else Webhook not found
        WH->>API: Return error
        API->>EXT: 404 Not Found
    end
```

## 4. Status Update Flow (Home Assistant to Cloud)

```mermaid
sequenceDiagram
    participant HA as Home Assistant
    participant INT as Cloud Integration
    participant API as API Gateway
    participant WH as Webhook Lambda
    participant DB as DynamoDB
    participant EB as EventBridge

    Note over HA: Entity state changes
    HA->>INT: State change event
    INT->>INT: Check if entity should sync
    
    alt Entity in sync list
        INT->>INT: Prepare status update
        
        INT->>API: POST /webhook/{webhook_id}
        Note over INT,API: {"type": "status", "entities": [...]}
        
        API->>WH: Invoke function
        WH->>DB: Verify webhook_id
        
        WH->>WH: Process status update
        WH->>EB: Emit status event
        Note over WH,EB: StatusUpdate event
        
        WH->>API: Return acknowledgment
        API->>INT: 200 OK
        INT->>INT: Log status update sent
        
    else Entity not in sync list
        INT->>INT: Ignore change
    end
```

## 5. Event Processing and Automation Flow

```mermaid
sequenceDiagram
    participant EB as EventBridge
    participant EP as Event Processor
    participant DB as DynamoDB
    participant SNS as SNS Topic
    participant ALERT as Alert Systems

    EB->>EP: DevicesSynced event
    EP->>EP: Process entity list
    
    loop For each entity
        alt Security device detected
            EP->>EP: Check security conditions
            Note over EP: door/window sensors, alarms, etc.
            
            alt Alert condition met
                EP->>SNS: Send security alert
                SNS->>ALERT: Notify alert systems
                
                EP->>EB: Emit security alert event
                Note over EP,EB: SecurityAlert event type
            end
            
        else Environmental sensor
            EP->>EP: Check thresholds
            Note over EP: temperature, humidity, power
            
            alt Threshold exceeded
                EP->>SNS: Send environmental alert
                EP->>EB: Emit environmental event
            end
        end
    end
    
    EP->>DB: Update metrics
    Note over EP,DB: Increment counters, update timestamps
```

## 6. Health Check and Monitoring Flow

```mermaid
sequenceDiagram
    participant INT as Cloud Integration
    participant API as API Gateway
    participant WH as Webhook Lambda
    participant CW as CloudWatch
    participant ALARM as CloudWatch Alarms

    Note over INT: Health check timer (1 min)
    INT->>API: POST /webhook/{webhook_id}
    Note over INT,API: {"type": "ping"}
    
    API->>WH: Invoke function
    WH->>WH: Process ping
    WH->>API: Return pong
    Note over WH,API: {"status": "ok", "webhook_active": true}
    
    alt Ping successful
        API->>INT: 200 OK
        INT->>CW: Log health metric
        Note over INT,CW: Custom metric: CloudConnectionHealthy = 1
        
    else Ping failed
        API->>INT: Error response
        INT->>CW: Log failure metric
        Note over INT,CW: Custom metric: CloudConnectionHealthy = 0
        
        CW->>ALARM: Trigger alarm
        ALARM->>ALARM: Send notifications
    end
```

## 7. Error Handling and Retry Flow

```mermaid
sequenceDiagram
    participant INT as Cloud Integration
    participant API as API Gateway
    participant LAMBDA as Lambda Function
    participant DLQ as Dead Letter Queue
    participant CW as CloudWatch

    INT->>API: API Request
    API->>LAMBDA: Invoke function
    
    alt Function succeeds
        LAMBDA->>API: Success response
        API->>INT: 200 OK
        
    else Function fails (retryable)
        LAMBDA->>CW: Log error
        LAMBDA->>API: 5xx Error
        API->>INT: Error response
        
        INT->>INT: Exponential backoff wait
        INT->>API: Retry request
        
    else Function fails (non-retryable)
        LAMBDA->>CW: Log error
        LAMBDA->>API: 4xx Error
        API->>INT: Client error
        INT->>INT: Log error, no retry
        
    else Function timeout
        LAMBDA->>DLQ: Send to DLQ
        LAMBDA->>CW: Log timeout
        API->>INT: 504 Timeout
        INT->>INT: Retry with backoff
    end
```

## 8. Configuration Update Flow

```mermaid
sequenceDiagram
    participant U as User
    participant HA as Home Assistant UI
    participant INT as Cloud Integration
    participant API as API Gateway
    participant REG as Register Lambda

    U->>HA: Reconfigure integration
    HA->>U: Show options form
    U->>HA: Update API URL
    HA->>INT: Update configuration
    
    INT->>INT: Validate new configuration
    
    alt New API key provided
        INT->>API: POST /ha/register (new endpoint)
        API->>REG: Re-register installation
        REG->>REG: Update installation record
        REG->>API: Return updated webhook URL
        API->>INT: New configuration confirmed
        
    else Only URL changed
        INT->>INT: Update internal configuration
        INT->>API: Test connection (ping)
        API->>INT: Connection confirmed
    end
    
    INT->>HA: Configuration updated
    HA->>U: Success message
    INT->>INT: Restart sync with new config
```

## 9. Installation Removal Flow

```mermaid
sequenceDiagram
    participant U as User
    participant HA as Home Assistant
    participant INT as Cloud Integration
    participant API as API Gateway
    participant DEL as Delete Lambda
    participant DB as DynamoDB
    participant EB as EventBridge

    U->>HA: Remove integration
    HA->>INT: Unload integration
    
    opt Cleanup cloud data
        INT->>API: DELETE /ha/installation/{id}
        API->>DEL: Invoke cleanup function
        
        DEL->>DB: Delete installation data
        Note over DEL,DB: Remove all INSTALL#{id} records
        
        DEL->>EB: Emit removal event
        Note over DEL,EB: InstallationRemoved event
        
        DEL->>API: Confirm deletion
        API->>INT: 200 OK
    end
    
    INT->>HA: Integration unloaded
    HA->>U: Integration removed
```

## 10. Bulk Operations Flow

```mermaid
sequenceDiagram
    participant INT as Cloud Integration
    participant API as API Gateway
    participant SYNC as Sync Lambda
    participant DB as DynamoDB

    Note over INT: Large installation with 1000+ entities
    INT->>INT: Prepare bulk sync data
    INT->>INT: Split into batches (100 entities each)
    
    loop For each batch
        INT->>API: POST /ha/sync (batch N)
        API->>SYNC: Invoke function
        
        SYNC->>DB: Batch write items (25 at a time)
        Note over SYNC,DB: DynamoDB batch limit
        
        loop While batch not complete
            SYNC->>DB: Write next 25 items
        end
        
        SYNC->>API: Return batch success
        API->>INT: Batch N completed
        
        INT->>INT: Brief delay between batches
    end
    
    INT->>INT: All batches completed
    INT->>INT: Log total sync summary
```

## Error Scenarios and Recovery

### Authentication Failures
- Invalid API key → Return 401, trigger re-authentication flow
- Expired installation → Return 403, trigger re-registration
- Missing webhook → Return 404, log error for investigation

### Network and Service Failures
- API Gateway timeout → Retry with exponential backoff
- DynamoDB throttling → Retry with jitter and backoff
- Lambda cold start → Accept higher initial latency

### Data Consistency Issues
- Partial sync failure → Resume from last successful batch
- State drift → Trigger full re-sync on next cycle
- Webhook delivery failure → Queue for retry with DLQ

These sequence diagrams provide a comprehensive view of all major flows within the Home Assistant Cloud Integration system, including normal operations, error conditions, and recovery scenarios.