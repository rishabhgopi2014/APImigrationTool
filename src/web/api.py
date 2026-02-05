"""
Web Dashboard API Backend

FastAPI backend providing REST endpoints for the web UI:
- API discovery
- Risk analysis
- Migration planning
- Status monitoring
- Log streaming
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import asyncio
from datetime import datetime

from ..connectors import APICConnector
from ..inventory import RiskScorer, TrafficPattern, BusinessCriticality
from ..translator import GlooConfigGenerator
from ..config import ConfigLoader

app = FastAPI(title="API Migration Orchestrator", version="1.0.0")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state (replace with Redis/DB in production)
discovered_apis = []
migration_status = {}
active_logs = []


# === Request/Response Models ===

class DiscoveryRequest(BaseModel):
    platform: Optional[str] = None
    filters: Optional[List[str]] = None


class MigrationPlanRequest(BaseModel):
    api_name: str
    backend_host: Optional[str] = "apic-gateway.company.com"


class TrafficShiftRequest(BaseModel):
    api_name: str
    percentage: int  # 0-100


# === API Endpoints ===

@app.get("/")
async def root():
    """Serve the web UI"""
    try:
        with open("src/web/static/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Dashboard not found</h1>", status_code=404)



@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/api/discover")
async def discover_apis(request: DiscoveryRequest):
    """
    Discover APIs from configured platforms.
    Returns list of APIs with risk scores.
    """
    global discovered_apis
    
    try:
        # Load credentials from environment variables
        import os
        credentials = {
            "url": os.getenv("APIC_BASE_URL", ""),
            "username": os.getenv("APIC_USERNAME", ""),
            "password": os.getenv("APIC_PASSWORD", ""),
            "token": os.getenv("APIC_TOKEN", "")
        }
        
        # Create connector
        # If no credentials provided → uses MOCK DATA (24 APIs)
        # If credentials provided → connects to REAL APIC
        connector = APICConnector(credentials=credentials, rate_limit=10)
        
        # Discover APIs
        apis = connector.discover_apis(filters=request.filters)
        
        # Calculate risk scores
        scorer = RiskScorer()
        api_risks = []
        
        for api in apis:
            traffic_pattern = TrafficPattern(
                avg_requests_per_day=api.avg_requests_per_day,
                avg_latency_ms=api.avg_latency_ms,
                error_rate=api.error_rate
            )
            
            risk_score = scorer.calculate_risk(
                api_name=api.name,
                traffic_pattern=traffic_pattern,
                auth_methods=api.auth_methods,
                business_criticality=BusinessCriticality.MEDIUM
            )
            
            api_risks.append({
                "name": api.name,
                "platform": api.platform,
                "base_path": api.base_path,
                "version": api.version,
                "description": api.description,
                "traffic": {
                    "requests_per_day": api.avg_requests_per_day,
                    "latency_ms": api.avg_latency_ms,
                    "error_rate": api.error_rate * 100 if api.error_rate else None
                },
                "auth_methods": api.auth_methods,
                "tags": api.tags,
                "risk": {
                    "score": risk_score.overall_score,
                    "level": risk_score.risk_level.value,
                    "factors": risk_score.risk_factors,
                    "recommendations": risk_score.recommendations
                },
                "legacy_metadata": api.legacy_metadata
            })
        
        # Sort by risk score (highest first)
        api_risks.sort(key=lambda x: x["risk"]["score"], reverse=True)
        
        # Store in memory
        discovered_apis = api_risks
        
        # Calculate risk distribution
        risk_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for api in api_risks:
            risk_counts[api["risk"]["level"]] += 1
        
        return {
            "success": True,
            "total_apis": len(api_risks),
            "apis": api_risks,
            "risk_distribution": risk_counts
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/apis")
async def list_apis(risk_level: Optional[str] = None):
    """Get list of discovered APIs, optionally filtered by risk level"""
    if risk_level:
        filtered = [api for api in discovered_apis if api["risk"]["level"] == risk_level]
        return {"apis": filtered, "count": len(filtered)}
    
    return {"apis": discovered_apis, "count": len(discovered_apis)}


@app.get("/api/apis/{api_name}")
async def get_api_details(api_name: str):
    """Get details for a specific API"""
    for api in discovered_apis:
        if api["name"] == api_name:
            return api
    
    raise HTTPException(status_code=404, detail=f"API '{api_name}' not found")


@app.post("/api/plan")
async def generate_migration_plan(request: MigrationPlanRequest):
    """Generate Gloo Gateway configuration for an API"""
    try:
        # Find the API
        api_data = None
        for api in discovered_apis:
            if api["name"] == request.api_name:
                api_data = api
                break
        
        if not api_data:
            raise HTTPException(status_code=404, detail=f"API '{request.api_name}' not found")
        
        # Create DiscoveredAPI object (simplified for demo)
        from ..connectors.base import DiscoveredAPI
        api = DiscoveredAPI(
            name=api_data["name"],
            platform=api_data["platform"],
            base_path=api_data["base_path"],
            version=api_data["version"],
            description=api_data["description"],
            auth_methods=api_data["auth_methods"],
            tags=api_data["tags"],
            legacy_metadata=api_data["legacy_metadata"]
        )
        
        # Generate Gloo configs
        generator = GlooConfigGenerator(namespace="gloo-system")
        gloo_config = generator.generate(api, backend_host=request.backend_host)
        
        # Convert to YAML strings
        yaml_files = gloo_config.to_yaml_files()
        
        return {
            "success": True,
            "api_name": request.api_name,
            "risk_level": api_data["risk"]["level"],
            "recommendations": api_data["risk"]["recommendations"],
            "configs": yaml_files
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/migrate/{api_name}/mirror")
async def start_mirroring(api_name: str, duration_hours: int = 24):
    """Start traffic mirroring for an API"""
    migration_status[api_name] = {
        "status": "MIRRORING",
        "started_at": datetime.now().isoformat(),
        "duration_hours": duration_hours,
        "progress": 0
    }
    
    active_logs.append({
        "timestamp": datetime.now().isoformat(),
        "api": api_name,
        "action": "START_MIRROR",
        "message": f"Started traffic mirroring for {duration_hours} hours"
    })
    
    return {"success": True, "status": migration_status[api_name]}


@app.post("/api/migrate/{api_name}/shift")
async def shift_traffic(api_name: str, request: TrafficShiftRequest):
    """Shift traffic to Gloo Gateway (canary rollout)"""
    if request.percentage < 0 or request.percentage > 100:
        raise HTTPException(status_code=400, detail="Percentage must be 0-100")
    
    migration_status[api_name] = {
        "status": f"CANARY_{request.percentage}",
        "traffic_percentage": request.percentage,
        "shifted_at": datetime.now().isoformat()
    }
    
    active_logs.append({
        "timestamp": datetime.now().isoformat(),
        "api": api_name,
        "action": "TRAFFIC_SHIFT",
        "message": f"Shifted {request.percentage}% traffic to Gloo Gateway"
    })
    
    return {"success": True, "status": migration_status[api_name]}


@app.post("/api/migrate/{api_name}/rollback")
async def rollback_migration(api_name: str):
    """Emergency rollback to legacy platform"""
    migration_status[api_name] = {
        "status": "ROLLED_BACK",
        "rolled_back_at": datetime.now().isoformat(),
        "traffic_percentage": 0
    }
    
    active_logs.append({
        "timestamp": datetime.now().isoformat(),
        "api": api_name,
        "action": "ROLLBACK",
        "message": "Emergency rollback - 100% traffic back to legacy platform",
        "level": "WARNING"
    })
    
    return {"success": True, "status": migration_status[api_name]}


@app.get("/api/status")
async def get_all_status():
    """Get migration status for all APIs"""
    return {"migrations": migration_status}


@app.get("/api/status/{api_name}")
async def get_api_status(api_name: str):
    """Get migration status for specific API"""
    if api_name not in migration_status:
        return {"api": api_name, "status": "NOT_STARTED"}
    
    return {"api": api_name, **migration_status[api_name]}


@app.get("/api/logs")
async def get_logs(limit: int = 100):
    """Get recent activity logs"""
    return {"logs": active_logs[-limit:]}


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket for real-time log streaming"""
    await websocket.accept()
    
    try:
        while True:
            # Send new logs every 2 seconds
            if active_logs:
                await websocket.send_json({"logs": active_logs[-10:]})
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass


@app.get("/api/stats")
async def get_statistics():
    """Get overall statistics"""
    total_apis = len(discovered_apis)
    
    risk_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for api in discovered_apis:
        risk_counts[api["risk"]["level"]] += 1
    
    status_counts = {}
    for status_info in migration_status.values():
        status = status_info["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
    
    return {
        "total_apis": total_apis,
        "risk_distribution": risk_counts,
        "migration_status": status_counts
    }


# Mount static files
try:
    app.mount("/static", StaticFiles(directory="src/web/static"), name="static")
except:
    pass  # Static directory doesn't exist yet


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
