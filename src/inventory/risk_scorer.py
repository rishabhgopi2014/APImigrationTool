"""
Risk Scorer Module

Calculates migration risk based on traffic patterns and API characteristics:
- Traffic volume (requests/day)
- Error rates and latency
- Authentication complexity
- Business criticality
- Dependencies

Provides risk scores to prioritize migration order.
"""

from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass


class RiskLevel(str, Enum):
    """Risk level for API migration"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class BusinessCriticality(str, Enum):
    """Business criticality level"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class TrafficPattern:
    """Traffic pattern metrics for an API"""
    avg_requests_per_day: Optional[int] = None
    peak_requests_per_sec: Optional[int] = None
    avg_latency_ms: Optional[int] = None
    p95_latency_ms: Optional[int] = None
    p99_latency_ms: Optional[int] = None
    error_rate: Optional[float] = None  # 0.0 to 1.0
    
    # Time-based patterns
    has_traffic_spikes: bool = False
    peak_hours: Optional[str] = None  # e.g., "9-17" for business hours


@dataclass
class RiskScore:
    """Calculated risk score for an API"""
    overall_score: float  # 0.0 to 1.0
    risk_level: RiskLevel
    business_criticality: BusinessCriticality
    
    # Component scores
    traffic_risk: float  # Based on volume
    performance_risk: float  # Based on latency/errors
    auth_risk: float  # Based on auth complexity
    
    # Reasoning
    risk_factors: list[str]
    recommendations: list[str]


class RiskScorer:
    """
    Risk scoring engine for API migration prioritization.
    
    Scores are calculated based on:
    1. Traffic volume (higher volume = higher risk)
    2. Performance metrics (errors, latency)
    3. Auth complexity (OAuth, mTLS more complex)
    4. Business criticality (impact of downtime)
    """
    
    # Traffic volume thresholds (requests/day)
    LOW_TRAFFIC = 10_000
    MEDIUM_TRAFFIC = 100_000
    HIGH_TRAFFIC = 1_000_000
    CRITICAL_TRAFFIC = 10_000_000
    
    # Error rate thresholds
    LOW_ERROR_RATE = 0.001  # 0.1%
    MEDIUM_ERROR_RATE = 0.01  # 1%
    HIGH_ERROR_RATE = 0.05  # 5%
    
    # Latency thresholds (ms)
    LOW_LATENCY = 100
    MEDIUM_LATENCY = 500
    HIGH_LATENCY = 2000
    
    def calculate_risk(
        self,
        api_name: str,
        traffic_pattern: Optional[TrafficPattern] = None,
        auth_methods: Optional[list[str]] = None,
        business_criticality: Optional[BusinessCriticality] = None,
        num_dependencies: int = 0,
        has_custom_middleware: bool = False
    ) -> RiskScore:
        """
        Calculate overall risk score for an API.
        
        Args:
            api_name: API identifier
            traffic_pattern: Traffic metrics
            auth_methods: Authentication methods used
            business_criticality: Business impact level
            num_dependencies: Number of downstream dependencies
            has_custom_middleware: Uses custom middleware/policies
            
        Returns:
            RiskScore object with overall score and breakdown
        """
        risk_factors = []
        recommendations = []
        
        # 1. Traffic risk (40% weight)
        traffic_risk = self._calculate_traffic_risk(traffic_pattern, risk_factors)
        
        # 2. Performance risk (30% weight)
        performance_risk = self._calculate_performance_risk(traffic_pattern, risk_factors)
        
        # 3. Auth complexity risk (20% weight)
        auth_risk = self._calculate_auth_risk(auth_methods, risk_factors)
        
        # 4. Complexity risk (10% weight)
        complexity_risk = self._calculate_complexity_risk(
            num_dependencies,
            has_custom_middleware,
            risk_factors
        )
        
        # Weighted overall score
        overall_score = (
            traffic_risk * 0.4 +
            performance_risk * 0.3 +
            auth_risk * 0.2 +
            complexity_risk * 0.1
        )
        
        # Apply business criticality multiplier
        if business_criticality:
            criticality_multiplier = {
                BusinessCriticality.LOW: 0.8,
                BusinessCriticality.MEDIUM: 1.0,
                BusinessCriticality.HIGH: 1.2,
                BusinessCriticality.CRITICAL: 1.5
            }
            overall_score *= criticality_multiplier[business_criticality]
            overall_score = min(overall_score, 1.0)  # Cap at 1.0
        
        # Determine risk level
        risk_level = self._score_to_risk_level(overall_score)
        
        # Generate recommendations
        self._generate_recommendations(
            risk_level,
            traffic_pattern,
            auth_methods,
            recommendations
        )
        
        return RiskScore(
            overall_score=round(overall_score, 2),
            risk_level=risk_level,
            business_criticality=business_criticality or BusinessCriticality.MEDIUM,
            traffic_risk=round(traffic_risk, 2),
            performance_risk=round(performance_risk, 2),
            auth_risk=round(auth_risk, 2),
            risk_factors=risk_factors,
            recommendations=recommendations
        )
    
    def _calculate_traffic_risk(
        self,
        traffic_pattern: Optional[TrafficPattern],
        risk_factors: list[str]
    ) -> float:
        """Calculate risk based on traffic volume"""
        if not traffic_pattern or not traffic_pattern.avg_requests_per_day:
            # Unknown traffic = medium risk
            risk_factors.append("Traffic volume unknown")
            return 0.5
        
        req_per_day = traffic_pattern.avg_requests_per_day
        
        if req_per_day >= self.CRITICAL_TRAFFIC:
            risk_factors.append(f"Very high traffic: {req_per_day:,} req/day")
            return 1.0
        elif req_per_day >= self.HIGH_TRAFFIC:
            risk_factors.append(f"High traffic: {req_per_day:,} req/day")
            return 0.8
        elif req_per_day >= self.MEDIUM_TRAFFIC:
            risk_factors.append(f"Moderate traffic: {req_per_day:,} req/day")
            return 0.5
        elif req_per_day >= self.LOW_TRAFFIC:
            return 0.3
        else:
            return 0.1
    
    def _calculate_performance_risk(
        self,
        traffic_pattern: Optional[TrafficPattern],
        risk_factors: list[str]
    ) -> float:
        """Calculate risk based on error rates and latency"""
        if not traffic_pattern:
            return 0.3
        
        risk = 0.0
        
        # Error rate component (50% of performance risk)
        if traffic_pattern.error_rate is not None:
            if traffic_pattern.error_rate >= self.HIGH_ERROR_RATE:
                risk_factors.append(f"High error rate: {traffic_pattern.error_rate*100:.2f}%")
                risk += 0.5
            elif traffic_pattern.error_rate >= self.MEDIUM_ERROR_RATE:
                risk_factors.append(f"Elevated error rate: {traffic_pattern.error_rate*100:.2f}%")
                risk += 0.25
            elif traffic_pattern.error_rate >= self.LOW_ERROR_RATE:
                risk += 0.1
        else:
            risk += 0.15  # Unknown error rate = moderate risk
        
        # Latency component (50% of performance risk)
        if traffic_pattern.p95_latency_ms is not None:
            if traffic_pattern.p95_latency_ms >= self.HIGH_LATENCY:
                risk_factors.append(f"High latency: p95={traffic_pattern.p95_latency_ms}ms")
                risk += 0.5
            elif traffic_pattern.p95_latency_ms >= self.MEDIUM_LATENCY:
                risk += 0.25
            elif traffic_pattern.p95_latency_ms >= self.LOW_LATENCY:
                risk += 0.1
        else:
            risk += 0.15  # Unknown latency = moderate risk
        
        return min(risk, 1.0)
    
    def _calculate_auth_risk(
        self,
        auth_methods: Optional[list[str]],
        risk_factors: list[str]
    ) -> float:
        """Calculate risk based on authentication complexity"""
        if not auth_methods:
            risk_factors.append("No authentication (easy migration)")
            return 0.1
        
        # Auth complexity scores
        auth_complexity = {
            "none": 0.1,
            "api-key": 0.2,
            "http-basic": 0.2,
            "jwt": 0.5,
            "oauth": 0.7,
            "oauth2": 0.7,
            "mtls": 0.9,
            "saml": 0.8,
            "custom": 1.0
        }
        
        max_complexity = 0.0
        for method in auth_methods:
            method_lower = method.lower()
            complexity = auth_complexity.get(method_lower, 0.5)
            max_complexity = max(max_complexity, complexity)
        
        if max_complexity >= 0.7:
            risk_factors.append(f"Complex auth: {', '.join(auth_methods)}")
        
        return max_complexity
    
    def _calculate_complexity_risk(
        self,
        num_dependencies: int,
        has_custom_middleware: bool,
        risk_factors: list[str]
    ) -> float:
        """Calculate risk based on API complexity"""
        risk = 0.0
        
        # Dependencies
        if num_dependencies > 10:
            risk_factors.append(f"Many dependencies: {num_dependencies}")
            risk += 0.8
        elif num_dependencies > 5:
            risk += 0.5
        elif num_dependencies > 0:
            risk += 0.2
        
        # Custom middleware/policies
        if has_custom_middleware:
            risk_factors.append("Custom middleware/policies")
            risk += 0.5
        
        return min(risk, 1.0)
    
    def _score_to_risk_level(self, score: float) -> RiskLevel:
        """Convert numeric score to risk level"""
        if score >= 0.75:
            return RiskLevel.CRITICAL
        elif score >= 0.5:
            return RiskLevel.HIGH
        elif score >= 0.25:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_recommendations(
        self,
        risk_level: RiskLevel,
        traffic_pattern: Optional[TrafficPattern],
        auth_methods: Optional[list[str]],
        recommendations: list[str]
    ):
        """Generate migration recommendations based on risk"""
        if risk_level == RiskLevel.CRITICAL:
            recommendations.append("Deploy with extended traffic mirroring (7+ days)")
            recommendations.append("Use smallest canary increments (1%, 3%, 5%)")
            recommendations.append("Require multiple approvers")
            recommendations.append("Schedule during low-traffic window")
        elif risk_level == RiskLevel.HIGH:
            recommendations.append("Extended mirroring period (3-5 days)")
            recommendations.append("Conservative canary rollout")
            recommendations.append("Monitor closely during migration")
        elif risk_level == RiskLevel.MEDIUM:
            recommendations.append("Standard mirroring (24 hours)")
            recommendations.append("Standard canary phases (5%, 25%, 50%, 100%)")
        else:  # LOW
            recommendations.append("Fast-track migration candidate")
            recommendations.append("Standard or accelerated rollout")
        
        # Auth-specific recommendations
        if auth_methods and any(m.lower() in ["oauth", "mtls", "saml"] for m in auth_methods):
            recommendations.append("Thoroughly test auth flows in staging")
            recommendations.append("Validate token handling and expiration")
        
        # Performance recommendations
        if traffic_pattern and traffic_pattern.has_traffic_spikes:
            recommendations.append("Monitor during expected traffic spikes")


def analyze_batch_risk(apis_with_traffic: list[Dict[str, Any]]) -> Dict[str, RiskScore]:
    """
    Batch risk analysis for multiple APIs.
    
    Args:
        apis_with_traffic: List of dicts with api_name, traffic_pattern, etc.
        
    Returns:
        Dict of api_name -> RiskScore
    """
    scorer = RiskScorer()
    results = {}
    
    for api_data in apis_with_traffic:
        risk_score = scorer.calculate_risk(
            api_name=api_data.get("api_name"),
            traffic_pattern=api_data.get("traffic_pattern"),
            auth_methods=api_data.get("auth_methods"),
            business_criticality=api_data.get("business_criticality"),
            num_dependencies=api_data.get("num_dependencies", 0),
            has_custom_middleware=api_data.get("has_custom_middleware", False)
        )
        results[api_data["api_name"]] = risk_score
    
    return results
