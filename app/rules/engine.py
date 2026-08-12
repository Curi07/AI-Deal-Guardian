from datetime import datetime
from app.schemas.deal import Deal, PreflightStatus, RiskCategory, Severity

class RuleEngine:
    def evaluate(self, deal: Deal) -> Deal:
        """
        Evaluates the extracted deal, applies deterministic rules,
        calculates the risk score, and determines the preflight status.
        """
        risk_score = 0
        blocking_unknowns = 0
        confidence_deductions = 0.0

        # Calculate base risk from explicit risks provided by LLM
        for risk in deal.risks:
            if risk.severity == Severity.CRITICAL:
                risk_score += 30
            elif risk.severity == Severity.HIGH:
                risk_score += 20
            elif risk.severity == Severity.MEDIUM:
                risk_score += 10
            elif risk.severity == Severity.LOW:
                risk_score += 5

        # Evaluate Unknowns
        for unknown in deal.unknowns:
            if unknown.blocks_quote:
                blocking_unknowns += 1
                risk_score += 15
            else:
                risk_score += 5
            confidence_deductions += 0.05

        # Evaluate Dependencies
        for dep in deal.dependencies:
            if dep.status != "available":
                risk_score += 10
                confidence_deductions += 0.05

        # Rule: If deadline is explicitly soon, increase risk (heuristic example)
        # Note: A robust system would parse dates. For MVP, LLM might flag this in `risks` anyway.

        # Cap risk score at 100
        risk_score = min(risk_score, 100)
        
        # Base confidence is 1.0, reduce based on unknowns and dependencies
        confidence = max(0.0, 1.0 - confidence_deductions)

        # Deterministic Status Rules
        if blocking_unknowns > 1 or risk_score >= 80:
            status = PreflightStatus.DO_NOT_QUOTE
        elif blocking_unknowns == 1 or risk_score >= 40 or len(deal.questions) > 0:
            status = PreflightStatus.NEEDS_CLARIFICATION
        else:
            status = PreflightStatus.READY

        # Update the Preflight object
        deal.preflight.status = status
        deal.preflight.risk_score = risk_score
        deal.preflight.confidence = round(confidence, 2)
        deal.preflight.blocking_unknowns = blocking_unknowns
        from datetime import timezone
        deal.preflight.generated_at = datetime.now(timezone.utc).isoformat()

        return deal
