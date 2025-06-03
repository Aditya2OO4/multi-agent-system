import json
from typing import List, Dict, Any
import sqlite3


class ActionRouter:
    def __init__(self, db_conn_func):
        self.get_db_conn = db_conn_func
        self.action_map = {
            "complaint": {
                "high": "escalate_to_crm",
                "medium": "create_ticket",
                "low": "log_and_close"
            },
            "invoice": {
                "amount_exceeds_10k": "flag_for_review",
                "default": "process_payment"
            },
            "fraud_risk": {
                "default": "alert_security_team"
            },
            "regulation": {
                "GDPR": "notify_compliance_gdpr",
                "FDA": "notify_compliance_fda",
                "default": "log_regulation"
            }
        }

    def determine_actions(self, agent_results: Dict[str, Any], classification: Dict[str, Any]) -> List[str]:
        intent = classification.get('intent', 'unknown')
        actions = []

        if intent in self.action_map:
            intent_actions = self.action_map[intent]

            if intent == "complaint":
                urgency = agent_results.get('urgency', 'medium')
                tone = agent_results.get('tone', 'neutral')

                if tone in ['angry', 'threatening'] or urgency == 'high':
                    actions.append(intent_actions['high'])
                elif urgency == 'medium':
                    actions.append(intent_actions['medium'])
                else:
                    actions.append(intent_actions['low'])

            elif intent == "invoice":
                if agent_results.get('fields', {}).get('total', 0) > 10000:
                    actions.append(intent_actions['amount_exceeds_10k'])
                else:
                    actions.append(intent_actions['default'])

            elif intent == "fraud_risk":
                actions.append(intent_actions['default'])

            elif intent == "regulation":
                regulations = agent_results.get('regulations_mentioned', [])
                if regulations:
                    for reg in regulations:
                        if reg in intent_actions:
                            actions.append(intent_actions[reg])
                        else:
                            actions.append(intent_actions['default'])
                else:
                    actions.append(intent_actions['default'])

        # Log actions to database
        conn = self.get_db_conn()
        try:
            conn.execute(
                "INSERT INTO action_logs (intent, determined_actions) VALUES (?, ?)",
                (intent, json.dumps(actions)))
            conn.commit()
        finally:
            conn.close()

        return actions

    def execute_actions(self, actions: List[str]) -> Dict[str, Any]:
        results = {}
        conn = self.get_db_conn()
        try:
            for action in actions:
                # Simulate action execution
                result = {
                    "status": "success",
                    "action": action,
                    "details": "Simulated execution"
                }
                results[action] = result

                # Log execution to database
                conn.execute(
                    "INSERT INTO action_executions (action_name, result) VALUES (?, ?)",
                    (action, json.dumps(result)))

            conn.commit()
        finally:
            conn.close()

        return results