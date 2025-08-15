from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class MemberProfile(BaseModel):
    name: str
    age: int
    goals: List[str]
    personality: str
    health_conditions: List[str]

class HealthData(BaseModel):
    wearable_stream: Dict[str, Any] = Field(default_factory=dict)
    lab_results: Dict[str, Any] = Field(default_factory=dict)
    subjective_reports: List[str] = Field(default_factory=list)

class InterventionPlan(BaseModel):
    nutrition: Dict[str, Any] = Field(default_factory=dict)
    exercise: Dict[str, Any] = Field(default_factory=dict)
    adherence_status: str = "ON_TRACK"
    last_exercise_update_day: int = 0

class Logistics(BaseModel):
    location: str = "Singapore"
    is_traveling: bool = False

class SimulationState(BaseModel):
    current_day: float = 0.0
    member_profile: MemberProfile
    health_data: HealthData = Field(default_factory=HealthData)
    intervention_plan: InterventionPlan = Field(default_factory=InterventionPlan)
    logistics: Logistics = Field(default_factory=Logistics)
    event_log: List = Field(default_factory=list)
    # A simple key-value store for tracking narrative state
    narrative_flags: Dict[str, Any] = Field(default_factory=dict)