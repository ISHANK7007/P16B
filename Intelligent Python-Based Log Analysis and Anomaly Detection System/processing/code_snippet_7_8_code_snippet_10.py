class EscalationRuleDSLParser:
    def parse(self, rule_text):
        """Parse DSL text into abstract syntax tree"""
        # Implement parsing logic (use ANTLR, Lark, or custom parser)
        ast = self._build_ast(rule_text)
        return ast
    
    def validate(self, ast):
        """Validate rule structure and semantics"""
        validation_result = self._check_semantics(ast)
        if not validation_result.is_valid:
            raise DSLValidationError(validation_result.errors)
        return validation_result

class EscalationRuleCompiler:
    def compile(self, ast):
        """Compile validated AST into executable rule object"""
        condition_evaluator = self._compile_conditions(ast.conditions)
        action_executor = self._compile_actions(ast.actions)
        exception_evaluator = self._compile_conditions(ast.exceptions)
        
        return CompiledEscalationRule(
            id=ast.rule_id,
            name=ast.rule_name,
            condition_evaluator=condition_evaluator,
            action_executor=action_executor,
            exception_evaluator=exception_evaluator
        )