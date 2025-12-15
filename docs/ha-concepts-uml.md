```mermaid
classDiagram
    %% Core Entity Model
    class Entity {
        +string entity_id
        +string name
        +State state
        +Map attributes
        +string domain
        +Device device
        +Area area
        +List~Label~ labels
        +update_state()
        +get_attribute()
    }
    
    class State {
        +string value
        +datetime last_changed
        +datetime last_updated
        +Map attributes
    }
    
    class Domain {
        +string name
        +List~Service~ services
        +register_entity()
    }
    
    class Attributes {
        +Map~string,any~ values
        +get()
        +set()
    }

    %% Organization
    class Device {
        +string id
        +string name
        +string manufacturer
        +string model
        +Area area
        +List~Entity~ entities
        +Integration via
    }
    
    class Area {
        +string id
        +string name
        +Floor floor
        +List~Device~ devices
        +List~Entity~ entities
    }
    
    class Floor {
        +string id
        +string name
        +int level
        +List~Area~ areas
    }
    
    class Zone {
        +string name
        +float latitude
        +float longitude
        +float radius
        +bool passive
    }
    
    class Label {
        +string id
        +string name
        +string color
    }

    %% Integration Layer
    class Integration {
        +string domain
        +string name
        +Map config
        +List~Entity~ entities
        +List~Service~ services
        +setup()
        +reload()
    }
    
    class Service {
        +string name
        +string domain
        +Map schema
        +call(params)
    }

    %% Automation System
    class Automation {
        +string id
        +string name
        +List~Trigger~ triggers
        +List~Condition~ conditions
        +List~Action~ actions
        +string mode
        +execute()
    }
    
    class Trigger {
        +string platform
        +Map config
        +Entity entity
        +evaluate()
    }
    
    class Condition {
        +string type
        +Map config
        +Entity entity
        +check()
    }
    
    class Action {
        +string type
        +Service service
        +Map data
        +execute()
    }
    
    class Script {
        +string id
        +string name
        +List~Action~ actions
        +string mode
        +run()
    }
    
    class Scene {
        +string id
        +string name
        +Map~Entity,State~ entity_states
        +activate()
    }
    
    class Blueprint {
        +string name
        +string domain
        +Map inputs
        +Map blueprint
        +instantiate()
    }

    %% UI and Display
    class Dashboard {
        +string id
        +string title
        +List~Card~ cards
        +render()
    }
    
    class Card {
        +string type
        +List~Entity~ entities
        +Map config
    }

    %% User and Security
    class User {
        +string id
        +string name
        +bool is_admin
        +List~string~ permissions
        +authenticate()
    }
    
    class Person {
        +string id
        +string name
        +User user
        +List~Entity~ device_trackers
        +Zone current_zone
        +get_location()
    }

    %% Data Storage
    class Recorder {
        +record_state()
        +record_event()
        +purge_old_data()
    }
    
    class History {
        +get_states(entity, period)
        +get_history(period)
    }
    
    class Event {
        +string event_type
        +datetime time_fired
        +Map data
        +string origin
    }
    
    class Logbook {
        +log_entry()
        +get_entries(period)
    }

    %% Template System
    class Template {
        +string template_string
        +render(context)
        +is_valid()
    }

    %% Notifications
    class Notification {
        +string title
        +string message
        +string target
        +send()
    }

    %% Relationships - Core
    Entity "1" --> "1" State : has current
    Entity "1" --> "1" Attributes : has
    Entity "*" --> "1" Domain : belongs to
    Entity "*" --> "0..1" Device : part of
    Entity "*" --> "0..1" Area : located in
    Entity "*" --> "*" Label : tagged with
    
    %% Relationships - Organization
    Device "*" --> "0..1" Area : located in
    Area "*" --> "0..1" Floor : on
    Device "1" --> "*" Entity : contains
    
    %% Relationships - Integration
    Integration "1" --> "*" Entity : provides
    Integration "1" --> "*" Service : exposes
    Domain "1" --> "*" Service : has
    Device "*" --> "1" Integration : created by
    
    %% Relationships - Automation
    Automation "1" --> "*" Trigger : activated by
    Automation "1" --> "*" Condition : checks
    Automation "1" --> "*" Action : executes
    Trigger "*" --> "0..1" Entity : monitors
    Condition "*" --> "0..1" Entity : evaluates
    Action "*" --> "1" Service : calls
    Service "*" --> "*" Entity : operates on
    
    Script "1" --> "*" Action : contains
    Scene "1" --> "*" Entity : captures state of
    Blueprint "1" --> "*" Automation : generates
    Blueprint "1" --> "*" Script : generates
    
    %% Relationships - UI
    Dashboard "1" --> "*" Card : contains
    Card "*" --> "*" Entity : displays
    
    %% Relationships - User
    User "1" --> "0..1" Person : linked to
    Person "*" --> "*" Entity : tracked by
    Person "*" --> "0..1" Zone : in
    
    %% Relationships - Data
    Recorder "1" --> "*" State : stores
    Recorder "1" --> "*" Event : stores
    History "1" --> "*" State : queries
    Logbook "1" --> "*" Event : logs
    Entity "1" --> "*" Event : generates
    
    %% Relationships - Template
    Template "*" --> "*" Entity : references
    Action "*" --> "*" Template : uses
    
    %% Relationships - Notification
    Action "*" --> "*" Notification : sends
    Notification "*" --> "1" Service : via
    ```