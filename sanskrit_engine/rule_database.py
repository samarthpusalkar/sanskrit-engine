import json
from typing import Dict, List, Any, Callable

class PaniniRule:
    def __init__(self, data: Dict[str, Any]):
        self.rule_id = data.get("rule_id")
        self.name = data.get("name")
        self.category = data.get("category", "vidhi")
        self.priority = data.get("priority", 0)
        self.domain = data.get("domain", [])
        self.conditions = data.get("conditions", {})
        self.operation_data = data.get("operation", {})
        
        self.operation_func = self._compile_operation()

    def _compile_operation(self) -> Callable:
        """
        Compiles the stringified Python lambda into an executable function.
        If it's a DSL operation (type: dsl), maps it to standard methods.
        """
        op_type = self.operation_data.get("type")
        if op_type == "lambda":
            # SAFETY WARNING: In a strict production environment, evaluate AST or use strict sandboxing.
            # We use eval here to allow dynamically generated Paninian transformations.
            exec_str = self.operation_data.get("executable")
            try:
                # Expecting a string like "lambda token, env: token.replace('a', 'A')"
                return eval(exec_str)
            except Exception as e:
                raise RuntimeError(f"Failed to compile lambda for rule {self.rule_id}: {e}")
        elif op_type == "dsl":
            # Map standard DSL operations (e.g. rewrite_boundary)
            pass
        return lambda *args, **kwargs: args[0] # No-op

    def validate_conditions(self, token: Dict[str, Any], env: Dict[str, Any]) -> bool:
        """
        Validates if the conditions of this rule are met by the current token and environment.
        """
        # Complex JSON logic validator goes here.
        # For prototype, we assume true if domain matches.
        pos = token.get("pos")
        if self.domain and pos not in self.domain:
            return False
        return True

    def apply(self, token: Dict[str, Any], env: Dict[str, Any]) -> Any:
        """
        Executes the compiled lambda transformation on the token.
        """
        if not self.validate_conditions(token, env):
            return token
        return self.operation_func(token, env)

class RuleDatabase:
    """
    A NoSQL-style Document DB wrapper for Paninian Rules.
    Loads rules, compiles lambdas, and handles querying by priority.
    """
    def __init__(self, db_filepath: str):
        self.db_filepath = db_filepath
        self.rules: List[PaniniRule] = []
        self._load_db()

    def _load_db(self):
        try:
            with open(self.db_filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.rules = [PaniniRule(r) for r in data.get("rules", [])]
                # Sort descending by priority (Apavada before Utsarga)
                self.rules.sort(key=lambda x: x.priority, reverse=True)
        except FileNotFoundError:
            self.rules = []

    def save_db(self):
        data = {
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "name": r.name,
                    "category": r.category,
                    "priority": r.priority,
                    "domain": r.domain,
                    "conditions": r.conditions,
                    "operation": r.operation_data
                } for r in self.rules
            ]
        }
        with open(self.db_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def insert_rule(self, rule_data: Dict[str, Any]):
        rule = PaniniRule(rule_data)
        self.rules.append(rule)
        self.rules.sort(key=lambda x: x.priority, reverse=True)
        self.save_db()

    def get_applicable_rules(self, token: Dict[str, Any], env: Dict[str, Any]) -> List[PaniniRule]:
        """Returns all rules whose conditions evaluate to True, ordered by priority."""
        return [r for r in self.rules if r.validate_conditions(token, env)]
