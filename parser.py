# Analizador sintáctico y semántico para la P3 de Lava utilizando PLY, que define:
# - La gramática final del lenguaje Lava
# - Las reglas de precedencia y asociatividad de los operadores
# - La construcción de un AST para representar el programa
# - El análisis semántico completo (variables, records, funciones y tipos)
# - La generación de los ficheros de salida (.symbols, .records, .functions)
# - Opcionalmente, la generación de cuartetos (.quartets)

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import ply.yacc as yacc
import lexer as lava_lexer


# ===== Tokens =====

tokens = lava_lexer.tokens
start = 'program'


# ===== Precedencia =====

precedence = (
    ('nonassoc', 'IFX'),
    ('nonassoc', 'ELSE'),
    ('left', 'OR'),
    ('left', 'AND'),
    ('nonassoc', 'EQ'),
    ('nonassoc', 'GT', 'GE', 'LT', 'LE'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE'),
    ('right', 'NOT', 'UPLUS', 'UMINUS'),
)


# ===== AST =====
# Se definen las estructuras del árbol sintáctico abstracto (AST)
# que se construye durante el parseo y que luego usa el análisis semántico.

@dataclass
class Program:
    items: list[Any]


@dataclass
class RecordDecl:
    name: str
    fields: list[tuple[str, str]]


@dataclass
class FunctionDecl:
    return_type: str
    name: str
    params: list[tuple[str, str]]
    body: Any


@dataclass
class VarDecl:
    type_name: str
    names: list[str]
    init: Optional[Any] = None


@dataclass
class AssignStmt:
    target: Any
    expr: Any


@dataclass
class ExprStmt:
    expr: Any


@dataclass
class PrintStmt:
    args: list[Any]


@dataclass
class ReturnStmt:
    expr: Optional[Any]


@dataclass
class BreakStmt:
    pass


@dataclass
class Block:
    items: list[Any]


@dataclass
class IfStmt:
    cond: Any
    then_block: Any
    else_block: Optional[Any]


@dataclass
class WhileStmt:
    cond: Any
    body: Any


@dataclass
class DoWhileStmt:
    body: Any
    cond: Any


@dataclass
class Literal:
    value: Any
    type_name: str


@dataclass
class VarRef:
    name: str


@dataclass
class FieldAccess:
    obj: Any
    field: str


@dataclass
class CallExpr:
    callee: Any
    args: list[Any]


@dataclass
class NewExpr:
    type_name: str
    args: list[Any]


@dataclass
class UnaryExpr:
    op: str
    expr: Any


@dataclass
class BinaryExpr:
    op: str
    left: Any
    right: Any


# ===== Reglas auxiliares =====

BASIC_TYPES = {'int', 'float', 'char', 'boolean'}
NUMERIC_TYPES = {'int', 'float', 'char'}
TAIL_FUNC = 'func'
TAIL_INIT = 'init'
TAIL_LIST = 'list'
TAIL_CALL = 'call'


def _append(left: list[Any], item: Any) -> list[Any]:
    if item is not None:
        left.append(item)
    return left


def _typed_tail(kind: str, **kwargs):
    out = {'kind': kind}
    out.update(kwargs)
    return out


def _literal_from_token(tok_type: str, value: Any) -> Literal:
    return Literal(value, {
        'INT_VALUE': 'int',
        'FLOAT_VALUE': 'float',
        'CHAR_VALUE': 'char',
        'TRUE': 'boolean',
        'FALSE': 'boolean',
    }[tok_type])


def p_empty(p):
    'empty :'
    p[0] = None


# ===== Estructura global del programa =====

def p_program(p):
    'program : top_list'
    p[0] = Program(p[1])


def p_top_list_recursive(p):
    'top_list : top_list top_item'
    p[0] = _append(p[1], p[2])


def p_top_list_empty(p):
    'top_list : empty'
    p[0] = []


def p_top_item_empty_stmt(p):
    'top_item : SEMICOLON'
    p[0] = None


def p_top_item_basic_typed(p):
    'top_item : basic_type ID top_basic_typed_tail'
    tail = p[3]
    if tail['kind'] == TAIL_FUNC:
        p[0] = FunctionDecl(p[1], p[2], tail['params'], tail['body'])
    elif tail['kind'] == TAIL_INIT:
        p[0] = VarDecl(p[1], [p[2]], tail['expr'])
    else:
        p[0] = VarDecl(p[1], [p[2]] + tail['ids'])


def p_top_item_record_typed(p):
    'top_item : ID ID top_record_typed_tail'
    tail = p[3]
    if tail['kind'] == TAIL_FUNC:
        p[0] = FunctionDecl(p[1], p[2], tail['params'], tail['body'])
    elif tail['kind'] == TAIL_INIT:
        p[0] = VarDecl(p[1], [p[2]], tail['expr'])
    else:
        p[0] = VarDecl(p[1], [p[2]])


def p_top_item_void_function(p):
    'top_item : VOID ID LPAREN parameter_list_opt RPAREN block'
    p[0] = FunctionDecl('void', p[2], p[4], p[6])


def p_top_item_non_typed_stmt(p):
    'top_item : non_typed_simple_statement SEMICOLON'
    p[0] = p[1]


def p_top_item_compound_stmt(p):
    'top_item : compound_statement'
    p[0] = p[1]


def p_top_item_record_decl(p):
    'top_item : record_declaration SEMICOLON'
    p[0] = p[1]


def p_top_basic_typed_tail_function(p):
    'top_basic_typed_tail : LPAREN parameter_list_opt RPAREN block'
    p[0] = _typed_tail(TAIL_FUNC, params=p[2], body=p[4])


def p_top_basic_typed_tail_decl_init(p):
    'top_basic_typed_tail : ASSIGN expression SEMICOLON'
    p[0] = _typed_tail(TAIL_INIT, expr=p[2])


def p_top_basic_typed_tail_decl_list(p):
    'top_basic_typed_tail : id_list_tail SEMICOLON'
    p[0] = _typed_tail(TAIL_LIST, ids=p[1])


def p_top_record_typed_tail_function(p):
    'top_record_typed_tail : LPAREN parameter_list_opt RPAREN block'
    p[0] = _typed_tail(TAIL_FUNC, params=p[2], body=p[4])


def p_top_record_typed_tail_decl_init(p):
    'top_record_typed_tail : ASSIGN expression SEMICOLON'
    p[0] = _typed_tail(TAIL_INIT, expr=p[2])


def p_top_record_typed_tail_decl_plain(p):
    'top_record_typed_tail : SEMICOLON'
    p[0] = _typed_tail('plain')


# ===== Bloques =====

def p_block(p):
    'block : LBRACE block_item_list RBRACE'
    p[0] = Block(p[2])


def p_block_item_list_recursive(p):
    'block_item_list : block_item_list block_item'
    p[0] = _append(p[1], p[2])


def p_block_item_list_empty(p):
    'block_item_list : empty'
    p[0] = []


def p_block_item_empty_stmt(p):
    'block_item : SEMICOLON'
    p[0] = None


def p_block_item_simple_stmt(p):
    'block_item : simple_statement SEMICOLON'
    p[0] = p[1]


def p_block_item_compound_stmt(p):
    'block_item : compound_statement'
    p[0] = p[1]


# ===== Tipos =====

def p_basic_type(p):
    '''basic_type : INT
                  | FLOAT
                  | CHAR
                  | BOOLEAN'''
    p[0] = p[1]


def p_type_spec_basic(p):
    'type_spec : basic_type'
    p[0] = p[1]


def p_type_spec_id(p):
    'type_spec : ID'
    p[0] = p[1]


# ===== Sentencias =====

def p_simple_statement(p):
    '''simple_statement : declaration_statement
                        | non_typed_simple_statement'''
    p[0] = p[1]


def p_non_typed_simple_statement(p):
    '''non_typed_simple_statement : id_started_statement
                                  | print_statement
                                  | return_statement
                                  | break_statement'''
    p[0] = p[1]


def p_id_started_statement(p):
    'id_started_statement : ID id_statement_tail'
    tail = p[2]
    if tail['kind'] == TAIL_CALL:
        p[0] = ExprStmt(CallExpr(VarRef(p[1]), tail['args']))
        return

    target = VarRef(p[1])
    for field in tail['fields']:
        target = FieldAccess(target, field)
    p[0] = AssignStmt(target, tail['expr'])


def p_id_statement_tail_call(p):
    'id_statement_tail : LPAREN argument_list_opt RPAREN'
    p[0] = _typed_tail(TAIL_CALL, args=p[2])


def p_id_statement_tail_assign(p):
    'id_statement_tail : assignable_tail ASSIGN expression'
    p[0] = _typed_tail('assign', fields=p[1], expr=p[3])


def p_assignable_tail_empty(p):
    'assignable_tail : empty'
    p[0] = []


def p_assignable_tail_dot(p):
    'assignable_tail : DOT ID assignable_tail'
    p[0] = [p[2]] + p[3]


def p_compound_statement(p):
    '''compound_statement : block
                          | if_statement
                          | while_statement
                          | do_while_statement'''
    p[0] = p[1]


# ===== Declaraciones =====

def p_declaration_statement_basic(p):
    'declaration_statement : basic_type ID declaration_suffix'
    suffix = p[3]
    p[0] = VarDecl(p[1], [p[2]], suffix.get('expr')) if suffix['kind'] == TAIL_INIT else VarDecl(p[1], [p[2]] + suffix['ids'])


def p_declaration_statement_record_init(p):
    'declaration_statement : ID ID ASSIGN expression'
    p[0] = VarDecl(p[1], [p[2]], p[4])


def p_declaration_statement_record_plain(p):
    'declaration_statement : ID ID'
    p[0] = VarDecl(p[1], [p[2]])


def p_declaration_suffix_init(p):
    'declaration_suffix : ASSIGN expression'
    p[0] = _typed_tail(TAIL_INIT, expr=p[2])


def p_declaration_suffix_list(p):
    'declaration_suffix : id_list_tail'
    p[0] = _typed_tail(TAIL_LIST, ids=p[1])


def p_id_list_tail_empty(p):
    'id_list_tail : empty'
    p[0] = []


def p_id_list_tail_recursive(p):
    'id_list_tail : COMMA ID id_list_tail'
    p[0] = [p[2]] + p[3]


# ===== Print / return / break =====

def p_print_statement(p):
    'print_statement : PRINT LPAREN argument_list_opt RPAREN'
    p[0] = PrintStmt(p[3])


def p_return_statement_expr(p):
    'return_statement : RETURN expression'
    p[0] = ReturnStmt(p[2])


def p_return_statement_void(p):
    'return_statement : RETURN'
    p[0] = ReturnStmt(None)


def p_break_statement(p):
    'break_statement : BREAK'
    p[0] = BreakStmt()


# ===== If / while / do-while =====

def p_if_statement_if(p):
    'if_statement : IF LPAREN expression RPAREN block %prec IFX'
    p[0] = IfStmt(p[3], p[5], None)


def p_if_statement_if_else(p):
    'if_statement : IF LPAREN expression RPAREN block ELSE block'
    p[0] = IfStmt(p[3], p[5], p[7])


def p_while_statement(p):
    'while_statement : WHILE LPAREN expression RPAREN block'
    p[0] = WhileStmt(p[3], p[5])


def p_do_while_statement(p):
    'do_while_statement : DO block WHILE LPAREN expression RPAREN SEMICOLON'
    p[0] = DoWhileStmt(p[2], p[5])


# ===== Registros, parámetros y argumentos =====

def p_record_declaration(p):
    'record_declaration : RECORD ID LPAREN field_list_opt RPAREN'
    p[0] = RecordDecl(p[2], p[4])


def p_parameter_list_opt_list(p):
    'parameter_list_opt : parameter_list'
    p[0] = p[1]


def p_parameter_list_opt_empty(p):
    'parameter_list_opt : empty'
    p[0] = []


def p_parameter_list_single(p):
    'parameter_list : parameter'
    p[0] = [p[1]]


def p_parameter_list_multiple(p):
    'parameter_list : parameter_list COMMA parameter'
    p[0] = p[1] + [p[3]]


def p_parameter(p):
    'parameter : type_spec ID'
    p[0] = (p[2], p[1])


def p_field_list_opt_list(p):
    'field_list_opt : field_list'
    p[0] = p[1]


def p_field_list_opt_empty(p):
    'field_list_opt : empty'
    p[0] = []


def p_field_list_single(p):
    'field_list : field'
    p[0] = [p[1]]


def p_field_list_multiple(p):
    'field_list : field_list COMMA field'
    p[0] = p[1] + [p[3]]


def p_field(p):
    'field : type_spec ID'
    p[0] = (p[2], p[1])


def p_argument_list_opt_list(p):
    'argument_list_opt : argument_list'
    p[0] = p[1]


def p_argument_list_opt_empty(p):
    'argument_list_opt : empty'
    p[0] = []


def p_argument_list_single(p):
    'argument_list : expression'
    p[0] = [p[1]]


def p_argument_list_multiple(p):
    'argument_list : argument_list COMMA expression'
    p[0] = p[1] + [p[3]]


# ===== Expresiones =====

def p_expression_binary(p):
    '''expression : expression OR expression
                  | expression AND expression
                  | expression EQ expression
                  | expression GT expression
                  | expression GE expression
                  | expression LT expression
                  | expression LE expression
                  | expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression DIVIDE expression'''
    p[0] = BinaryExpr(p[2], p[1], p[3])


def p_expression_unary_not(p):
    'expression : NOT expression'
    p[0] = UnaryExpr('!', p[2])


def p_expression_unary_plus(p):
    'expression : PLUS expression %prec UPLUS'
    p[0] = UnaryExpr('+', p[2])


def p_expression_unary_minus(p):
    'expression : MINUS expression %prec UMINUS'
    p[0] = UnaryExpr('-', p[2])


def p_expression_postfix(p):
    'expression : postfix_expression'
    p[0] = p[1]


def p_postfix_expression_primary(p):
    'postfix_expression : primary_expression'
    p[0] = p[1]


def p_postfix_expression_call(p):
    'postfix_expression : postfix_expression LPAREN argument_list_opt RPAREN'
    p[0] = CallExpr(p[1], p[3])


def p_postfix_expression_dot(p):
    'postfix_expression : postfix_expression DOT ID'
    p[0] = FieldAccess(p[1], p[3])


def p_primary_expression_group(p):
    'primary_expression : LPAREN expression RPAREN'
    p[0] = p[2]


def p_primary_expression_literal(p):
    '''primary_expression : INT_VALUE
                          | FLOAT_VALUE
                          | CHAR_VALUE
                          | TRUE
                          | FALSE'''
    p[0] = _literal_from_token(p.slice[1].type, p[1])


def p_primary_expression_id(p):
    'primary_expression : ID'
    p[0] = VarRef(p[1])


def p_primary_expression_new(p):
    'primary_expression : NEW ID LPAREN argument_list_opt RPAREN'
    p[0] = NewExpr(p[2], p[4])


# ===== Manejo de errores =====

def p_error(p):
    if p is None:
        raise SyntaxError('[ERROR] Fin de fichero inesperado')
    raise SyntaxError(f"[ERROR] Token '{p.type}' inesperado en la línea {p.lineno}")


# ===== Análisis semántico =====

class SemanticError(Exception):
    pass


class Scope:
    def __init__(self, parent: Optional['Scope'] = None):
        self.parent = parent
        self.symbols: dict[str, dict[str, Any]] = {}

    def declare(self, name: str, typ: str, value: Any = None):
        if name in self.symbols:
            raise SemanticError(f"[ERROR] Variable '{name}' ya declarada")
        self.symbols[name] = {'type': typ, 'value': value}

    def resolve(self, name: str):
        scope = self
        while scope is not None:
            if name in scope.symbols:
                return scope.symbols[name]
            scope = scope.parent
        return None


class Analyzer:
    def __init__(self, program: Program):
        self.program = program
        self.records: dict[str, list[tuple[str, str]]] = {}
        self.functions: dict[str, list[dict[str, Any]]] = {}
        self.global_scope = Scope()
        self.global_order: list[str] = []
        self.has_control_or_functions = False
        self.quartets: list[str] = []
        self.temp_counter = 0
        self.label_counter = 0
        self.break_stack: list[str] = []

    # ===== Entrada principal =====

    def analyze(self):
        self._pre_scan_records()
        self._analyze_top_level()

    # ===== Recorrido principal =====

    def _pre_scan_records(self):
        reserved = BASIC_TYPES | {'void'}
        for item in self.program.items:
            if not isinstance(item, RecordDecl):
                continue
            if item.name in self.records or item.name in reserved:
                raise SemanticError(f"[ERROR] Record '{item.name}' ya declarado")
            seen, checked = set(), []
            for field_name, field_type in item.fields:
                if field_name in seen:
                    raise SemanticError(f"[ERROR] Campo '{field_name}' duplicado en record '{item.name}'")
                seen.add(field_name)
                self._ensure_type_exists(field_type)
                checked.append((field_name, field_type))
            self.records[item.name] = checked

    def _analyze_top_level(self):
        for item in self.program.items:
            if item is None or isinstance(item, RecordDecl):
                continue
            if isinstance(item, FunctionDecl):
                self.has_control_or_functions = True
                self._analyze_function_decl(item)
            elif isinstance(item, VarDecl):
                self._analyze_vardecl(item, self.global_scope, is_global=True)
            elif isinstance(item, AssignStmt):
                self._analyze_assign(item, self.global_scope)
                self._emit_assign_if_supported(item, self.global_scope)
            elif isinstance(item, ExprStmt):
                self._infer_expr(item.expr, self.global_scope)
            elif isinstance(item, PrintStmt):
                self._analyze_print(item, self.global_scope, allow_codegen=True)
            elif isinstance(item, ReturnStmt):
                raise SemanticError('[ERROR] return fuera de una función')
            elif isinstance(item, BreakStmt):
                raise SemanticError('[ERROR] break fuera de un bucle')
            elif isinstance(item, (IfStmt, WhileStmt, DoWhileStmt, Block)):
                self.has_control_or_functions = True
                self._analyze_statement(item, self.global_scope, None, False, True)
            else:
                raise SemanticError('[ERROR] Elemento de programa no soportado')

    def _analyze_function_decl(self, func: FunctionDecl):
        self._ensure_type_exists(func.return_type)
        param_types = tuple(t for _, t in func.params)
        for overload in self.functions.get(func.name, []):
            if overload['param_types'] == param_types:
                raise SemanticError(f"[ERROR] Función '{func.name}' ya declarada con la misma firma")

        local_scope = Scope(self.global_scope)
        seen = set()
        for pname, ptype in func.params:
            self._ensure_type_exists(ptype)
            if pname in seen:
                raise SemanticError(f"[ERROR] Parámetro '{pname}' duplicado en función '{func.name}'")
            seen.add(pname)
            local_scope.declare(pname, ptype, self._default_value(ptype))

        found_return = self._analyze_block(func.body, local_scope, func.return_type, False, False)
        if func.return_type == 'void':
            if found_return:
                raise SemanticError(f"[ERROR] La función void '{func.name}' no puede tener return con valor")
        elif not found_return:
            raise SemanticError(f"[ERROR] La función '{func.name}' debe devolver un valor de tipo '{func.return_type}'")

        self.functions.setdefault(func.name, []).append({
            'name': func.name,
            'params': list(func.params),
            'param_types': param_types,
            'return_type': func.return_type,
        })

    # ===== Sentencias =====

    def _analyze_block(self, block: Block, scope: Scope, current_return_type: Optional[str], in_loop: bool, allow_codegen: bool) -> bool:
        found_return = False
        for item in block.items:
            if item is None:
                continue
            found_return = self._analyze_statement(item, scope, current_return_type, in_loop, allow_codegen) or found_return
        return found_return

    def _analyze_statement(self, stmt, scope: Scope, current_return_type: Optional[str], in_loop: bool, allow_codegen: bool) -> bool:
        if isinstance(stmt, Block):
            return self._analyze_block(stmt, Scope(scope), current_return_type, in_loop, allow_codegen)
        if isinstance(stmt, VarDecl):
            self._analyze_vardecl(stmt, scope)
            return False
        if isinstance(stmt, AssignStmt):
            self._analyze_assign(stmt, scope)
            if allow_codegen:
                self._emit_assign_if_supported(stmt, scope)
            return False
        if isinstance(stmt, ExprStmt):
            self._infer_expr(stmt.expr, scope)
            return False
        if isinstance(stmt, PrintStmt):
            self._analyze_print(stmt, scope, allow_codegen)
            return False
        if isinstance(stmt, ReturnStmt):
            return self._analyze_return(stmt, scope, current_return_type)
        if isinstance(stmt, BreakStmt):
            if not in_loop:
                raise SemanticError('[ERROR] break fuera de un bucle')
            if allow_codegen:
                self.quartets.append(f'JUMP,{self.break_stack[-1]},_,_')
            return False
        if isinstance(stmt, IfStmt):
            return self._analyze_if(stmt, scope, current_return_type, in_loop, allow_codegen)
        if isinstance(stmt, WhileStmt):
            self._analyze_while(stmt, scope, current_return_type, allow_codegen)
            return False
        if isinstance(stmt, DoWhileStmt):
            self._analyze_do_while(stmt, scope, current_return_type, allow_codegen)
            return False
        raise SemanticError('[ERROR] Sentencia no soportada')

    def _analyze_print(self, stmt: PrintStmt, scope: Scope, allow_codegen: bool):
        for arg in stmt.args:
            self._infer_expr(arg, scope)
            if allow_codegen:
                self._emit_expr_if_supported(arg, scope)
                self.quartets.append(f'PRINT,{self._expr_ref(arg, scope)},_,_')

    def _analyze_return(self, stmt: ReturnStmt, scope: Scope, current_return_type: Optional[str]) -> bool:
        if current_return_type is None:
            raise SemanticError('[ERROR] return fuera de una función')
        if current_return_type == 'void':
            if stmt.expr is not None:
                raise SemanticError('[ERROR] Una función void no puede devolver valor')
            return False
        if stmt.expr is None:
            raise SemanticError(f"[ERROR] La función debe devolver '{current_return_type}'")
        expr_type, _ = self._infer_expr(stmt.expr, scope)
        if not self._can_assign(expr_type, current_return_type):
            raise SemanticError(f"[ERROR] return incompatible: se esperaba '{current_return_type}' y se obtuvo '{expr_type}'")
        return True

    def _check_boolean_condition(self, expr, scope: Scope, label: str):
        expr_type, _ = self._infer_expr(expr, scope)
        if expr_type != 'boolean':
            raise SemanticError(f'[ERROR] La condición del {label} debe ser boolean')

    def _analyze_if(self, stmt: IfStmt, scope: Scope, current_return_type: Optional[str], in_loop: bool, allow_codegen: bool) -> bool:
        self._check_boolean_condition(stmt.cond, scope, 'if')
        if not allow_codegen:
            r1 = self._analyze_statement(stmt.then_block, scope, current_return_type, in_loop, False)
            r2 = self._analyze_statement(stmt.else_block, scope, current_return_type, in_loop, False) if stmt.else_block else False
            return r1 or r2

        false_label = self._new_label()
        end_label = self._new_label() if stmt.else_block else None
        self._emit_expr_if_supported(stmt.cond, scope)
        self.quartets.append(f'JUMPF,{self._expr_ref(stmt.cond, scope)},{false_label},_')
        self._analyze_statement(stmt.then_block, scope, current_return_type, in_loop, True)
        if stmt.else_block:
            self.quartets.append(f'JUMP,{end_label},_,_')
        self.quartets.append(f'LABEL,{false_label},_,_')
        if stmt.else_block:
            self._analyze_statement(stmt.else_block, scope, current_return_type, in_loop, True)
            self.quartets.append(f'LABEL,{end_label},_,_')
        return False

    def _analyze_while(self, stmt: WhileStmt, scope: Scope, current_return_type: Optional[str], allow_codegen: bool):
        self._check_boolean_condition(stmt.cond, scope, 'while')
        if not allow_codegen:
            self._analyze_statement(stmt.body, scope, current_return_type, True, False)
            return
        start, end = self._new_label(), self._new_label()
        self.break_stack.append(end)
        self.quartets.append(f'LABEL,{start},_,_')
        self._emit_expr_if_supported(stmt.cond, scope)
        self.quartets.append(f'JUMPF,{self._expr_ref(stmt.cond, scope)},{end},_')
        self._analyze_statement(stmt.body, scope, current_return_type, True, True)
        self.quartets.append(f'JUMP,{start},_,_')
        self.quartets.append(f'LABEL,{end},_,_')
        self.break_stack.pop()

    def _analyze_do_while(self, stmt: DoWhileStmt, scope: Scope, current_return_type: Optional[str], allow_codegen: bool):
        self._check_boolean_condition(stmt.cond, scope, 'do-while')
        if not allow_codegen:
            self._analyze_statement(stmt.body, scope, current_return_type, True, False)
            return
        start, end = self._new_label(), self._new_label()
        self.break_stack.append(end)
        self.quartets.append(f'LABEL,{start},_,_')
        self._analyze_statement(stmt.body, scope, current_return_type, True, True)
        self._emit_expr_if_supported(stmt.cond, scope)
        self.quartets.append(f'JUMPT,{self._expr_ref(stmt.cond, scope)},{start},_')
        self.quartets.append(f'LABEL,{end},_,_')
        self.break_stack.pop()

    # ===== Declaraciones y asignaciones =====

    def _analyze_vardecl(self, decl: VarDecl, scope: Scope, is_global: bool = False):
        self._ensure_type_exists(decl.type_name)
        for name in decl.names:
            value = self._default_value(decl.type_name)
            if decl.init is not None:
                expr_type, expr_value = self._infer_expr(decl.init, scope)
                if not self._can_assign(expr_type, decl.type_name):
                    raise SemanticError(f"[ERROR] No se puede asignar '{expr_type}' a '{decl.type_name}'")
                value = self._convert_value(expr_value, expr_type, decl.type_name)
                if is_global:
                    self._emit_decl_init(name, decl.type_name, decl.init, scope)
            else:
                if is_global:
                    self._emit_default_assign(name, decl.type_name)
            scope.declare(name, decl.type_name, value)
            if is_global:
                self.global_order.append(name)

    def _analyze_assign(self, stmt: AssignStmt, scope: Scope):
        target_type, getter, setter = self._resolve_target(stmt.target, scope)
        expr_type, expr_value = self._infer_expr(stmt.expr, scope)
        if not self._can_assign(expr_type, target_type):
            raise SemanticError(f"[ERROR] No se puede asignar '{expr_type}' a '{target_type}'")
        setter(self._convert_value(expr_value, expr_type, target_type))

    def _resolve_target(self, target, scope: Scope):
        if isinstance(target, VarRef):
            sym = scope.resolve(target.name)
            if sym is None:
                raise SemanticError(f"[ERROR] Variable '{target.name}' no declarada")
            return sym['type'], lambda: sym['value'], lambda v: sym.__setitem__('value', v)

        if not isinstance(target, FieldAccess):
            raise SemanticError('[ERROR] Lado izquierdo de asignación no válido')

        obj_type, obj_getter, obj_setter = self._resolve_target(target.obj, scope)
        if obj_type in BASIC_TYPES:
            raise SemanticError(f"[ERROR] El tipo '{obj_type}' no tiene campos")
        fields = dict(self.records.get(obj_type, []))
        if target.field not in fields:
            raise SemanticError(f"[ERROR] El record '{obj_type}' no tiene el campo '{target.field}'")

        def getter():
            return obj_getter()[target.field]

        def setter(value):
            obj = obj_getter()
            obj[target.field] = value
            obj_setter(obj)

        return fields[target.field], getter, setter

    # ===== Expresiones =====

    def _infer_expr(self, expr, scope: Scope):
        if isinstance(expr, Literal):
            return expr.type_name, expr.value

        if isinstance(expr, VarRef):
            sym = scope.resolve(expr.name)
            if sym is None:
                raise SemanticError(f"[ERROR] Variable '{expr.name}' no declarada")
            return sym['type'], sym['value']

        if isinstance(expr, FieldAccess):
            base_type, base_value = self._infer_expr(expr.obj, scope)
            if base_type in BASIC_TYPES:
                raise SemanticError(f"[ERROR] El tipo '{base_type}' no tiene campos")
            fields = dict(self.records.get(base_type, []))
            if expr.field not in fields:
                raise SemanticError(f"[ERROR] El record '{base_type}' no tiene el campo '{expr.field}'")
            return fields[expr.field], None if base_value is None else base_value.get(expr.field)

        if isinstance(expr, NewExpr):
            return self._infer_new(expr, scope)
        if isinstance(expr, UnaryExpr):
            return self._infer_unary(expr, scope)
        if isinstance(expr, BinaryExpr):
            return self._infer_binary(expr, scope)
        if isinstance(expr, CallExpr):
            return self._infer_call(expr, scope)
        raise SemanticError('[ERROR] Expresión no soportada')

    def _infer_new(self, expr: NewExpr, scope: Scope):
        if expr.type_name not in self.records:
            raise SemanticError(f"[ERROR] Record '{expr.type_name}' no declarado")
        fields = self.records[expr.type_name]
        if len(expr.args) != len(fields):
            raise SemanticError(f"[ERROR] Número incorrecto de argumentos para new {expr.type_name}")
        value = {}
        for (fname, ftype), arg in zip(fields, expr.args):
            arg_type, arg_value = self._infer_expr(arg, scope)
            if not self._can_assign(arg_type, ftype):
                raise SemanticError(f"[ERROR] Argumento incompatible en new {expr.type_name}: se esperaba '{ftype}' y llegó '{arg_type}'")
            value[fname] = self._convert_value(arg_value, arg_type, ftype)
        return expr.type_name, value

    def _infer_unary(self, expr: UnaryExpr, scope: Scope):
        etype, evalue = self._infer_expr(expr.expr, scope)
        if expr.op == '!':
            if etype != 'boolean':
                raise SemanticError('[ERROR] El operador ! requiere boolean')
            return 'boolean', None if evalue is None else (not evalue)
        if etype not in NUMERIC_TYPES:
            raise SemanticError(f"[ERROR] El operador unario '{expr.op}' requiere int, float o char")
        return etype, None if evalue is None else (+evalue if expr.op == '+' else -evalue)

    def _infer_binary(self, expr: BinaryExpr, scope: Scope):
        lt, lv = self._infer_expr(expr.left, scope)
        rt, rv = self._infer_expr(expr.right, scope)
        op = expr.op

        if op in {'+', '-', '*', '/'}:
            return self._infer_arithmetic(op, lt, lv, rt, rv)
        if op in {'>', '>=', '<', '<='}:
            return self._infer_compare(op, lt, lv, rt, rv)
        if op == '==':
            if not (lt == rt or self._can_assign(lt, rt) or self._can_assign(rt, lt)):
                raise SemanticError(f"[ERROR] No se puede comparar '{lt}' con '{rt}'")
            return 'boolean', None if lv is None or rv is None else (lv == rv)
        if op in {'&&', '||'}:
            if lt != 'boolean' or rt != 'boolean':
                raise SemanticError(f"[ERROR] El operador '{op}' requiere boolean")
            if lv is None or rv is None:
                return 'boolean', None
            return 'boolean', (lv and rv) if op == '&&' else (lv or rv)
        raise SemanticError(f"[ERROR] Operador '{op}' no soportado")

    def _infer_arithmetic(self, op: str, lt: str, lv: Any, rt: str, rv: Any):
        if lt not in NUMERIC_TYPES or rt not in NUMERIC_TYPES:
            raise SemanticError(f"[ERROR] El operador '{op}' requiere operandos numéricos/char")
        result_type = self._numeric_result_type(lt, rt)
        a = None if lv is None else self._coerce_numeric_value(lv, lt, result_type)
        b = None if rv is None else self._coerce_numeric_value(rv, rt, result_type)
        if a is None or b is None:
            return result_type, None
        ops = {
            '+': lambda x, y: x + y,
            '-': lambda x, y: x - y,
            '*': lambda x, y: x * y,
            '/': lambda x, y: x / y if result_type == 'float' else x // y,
        }
        return result_type, ops[op](a, b)

    def _infer_compare(self, op: str, lt: str, lv: Any, rt: str, rv: Any):
        if lt not in NUMERIC_TYPES or rt not in NUMERIC_TYPES:
            raise SemanticError(f"[ERROR] El operador '{op}' requiere operandos comparables")
        result_type = self._numeric_result_type(lt, rt)
        a = None if lv is None else self._coerce_numeric_value(lv, lt, result_type)
        b = None if rv is None else self._coerce_numeric_value(rv, rt, result_type)
        if a is None or b is None:
            return 'boolean', None
        ops = {
            '>': lambda x, y: x > y,
            '>=': lambda x, y: x >= y,
            '<': lambda x, y: x < y,
            '<=': lambda x, y: x <= y,
        }
        return 'boolean', ops[op](a, b)

    def _infer_call(self, expr: CallExpr, scope: Scope):
        if not isinstance(expr.callee, VarRef):
            raise SemanticError('[ERROR] La llamada a función debe hacerse sobre un identificador')
        overloads = self.functions.get(expr.callee.name, [])
        if not overloads:
            raise SemanticError(f"[ERROR] La función '{expr.callee.name}' no existe o aún no ha sido declarada")

        arg_types = [self._infer_expr(arg, scope)[0] for arg in expr.args]
        exact, converted = [], []
        for overload in overloads:
            if len(overload['param_types']) != len(arg_types):
                continue
            if all(a == e for a, e in zip(arg_types, overload['param_types'])):
                exact.append(overload)
            elif all(self._can_assign(a, e) for a, e in zip(arg_types, overload['param_types'])):
                converted.append(overload)

        matches = exact or converted
        if len(matches) > 1:
            raise SemanticError(f"[ERROR] Llamada ambigua a la función '{expr.callee.name}'")
        if not matches:
            raise SemanticError(f"[ERROR] No existe una sobrecarga compatible para '{expr.callee.name}'")
        return matches[0]['return_type'], None

    # ===== Tipos y conversiones =====

    def _ensure_type_exists(self, type_name: str):
        if type_name in BASIC_TYPES or type_name == 'void':
            return
        if type_name not in self.records:
            raise SemanticError(f"[ERROR] Tipo '{type_name}' no declarado")

    def _default_value(self, type_name: str):
        defaults = {'int': 0, 'float': 0.0, 'char': '\x00', 'boolean': False}
        if type_name in defaults:
            return defaults[type_name]
        if type_name not in self.records:
            raise SemanticError(f"[ERROR] Tipo '{type_name}' no declarado")
        return {fname: self._default_value(ftype) for fname, ftype in self.records[type_name]}

    def _can_assign(self, src: str, dst: str) -> bool:
        return src == dst or (src == 'char' and dst in {'int', 'float'}) or (src == 'int' and dst == 'float')

    def _convert_value(self, value: Any, src: str, dst: str):
        if value is None or src == dst:
            return value
        if src == 'char' and dst == 'int':
            return ord(value)
        if src == 'char' and dst == 'float':
            return float(ord(value))
        if src == 'int' and dst == 'float':
            return float(value)
        return value

    def _numeric_result_type(self, left: str, right: str) -> str:
        if 'float' in {left, right}:
            return 'float'
        if 'int' in {left, right}:
            return 'int'
        return 'char'

    def _coerce_numeric_value(self, value: Any, src_type: str, dst_type: str):
        return self._convert_value(value, src_type, dst_type)

    # ===== Cuartetos =====

    def _new_temp(self) -> str:
        self.temp_counter += 1
        return f'@T{self.temp_counter}'

    def _new_label(self) -> str:
        self.label_counter += 1
        return f'@L{self.label_counter}'

    def _expr_ref(self, expr, scope: Scope):
        if isinstance(expr, Literal):
            if expr.type_name == 'char':
                return repr(expr.value)
            if expr.type_name == 'boolean':
                return 'true' if expr.value else 'false'
            return str(expr.value)
        if isinstance(expr, VarRef):
            return expr.name
        return getattr(expr, '_ref', '_')

    def _emit_default_assign(self, name: str, type_name: str):
        if type_name in BASIC_TYPES:
            ref = self._expr_ref(Literal(self._default_value(type_name), type_name), self.global_scope)
            self.quartets.append(f'ASSIGN,{ref},_,{name}')

    def _emit_decl_init(self, name: str, target_type: str, expr, scope: Scope):
        source_ref = self._emit_value_for_target_type(expr, scope, target_type)
        if source_ref is not None:
            self.quartets.append(f'ASSIGN,{source_ref},_,{name}')

    def _emit_assign_if_supported(self, stmt: AssignStmt, scope: Scope):
        if not isinstance(stmt.target, VarRef):
            return
        target_sym = scope.resolve(stmt.target.name)
        if target_sym is None:
            return
        source_ref = self._emit_value_for_target_type(stmt.expr, scope, target_sym['type'])
        if source_ref is not None:
            self.quartets.append(f'ASSIGN,{source_ref},_,{stmt.target.name}')

    def _emit_cast_ref(self, source_ref: str, src_type: str, dst_type: str) -> str:
        if src_type == dst_type:
            return source_ref

        if src_type == 'char' and dst_type == 'int':
            temp = self._new_temp()
            self.quartets.append(f'CHAR_TO_INT,{source_ref},_,{temp}')
            return temp

        if src_type == 'int' and dst_type == 'float':
            temp = self._new_temp()
            self.quartets.append(f'INT_TO_FLOAT,{source_ref},_,{temp}')
            return temp

        if src_type == 'char' and dst_type == 'float':
            temp1 = self._new_temp()
            self.quartets.append(f'CHAR_TO_INT,{source_ref},_,{temp1}')
            temp2 = self._new_temp()
            self.quartets.append(f'INT_TO_FLOAT,{temp1},_,{temp2}')
            return temp2

        return source_ref

    def _emit_value_for_target_type(self, expr, scope: Scope, target_type: str):
        expr_type, _ = self._infer_expr(expr, scope)
        if not self._emit_expr_if_supported(expr, scope):
            return None
        source_ref = self._expr_ref(expr, scope)
        return self._emit_cast_ref(source_ref, expr_type, target_type)

    def _emit_expr_if_supported(self, expr, scope: Scope) -> bool:
        if isinstance(expr, (Literal, VarRef)):
            return True
        if isinstance(expr, FieldAccess):
            return False
        if isinstance(expr, NewExpr):
            return False
        if isinstance(expr, CallExpr):
            return False
        if isinstance(expr, UnaryExpr):
            expr_type, _ = self._infer_expr(expr, scope)
            inner_type, _ = self._infer_expr(expr.expr, scope)
            if not self._emit_expr_if_supported(expr.expr, scope):
                return False

            inner_ref = self._expr_ref(expr.expr, scope)
            if expr.op in {'+', '-'} and inner_type != expr_type:
                inner_ref = self._emit_cast_ref(inner_ref, inner_type, expr_type)

            temp = self._new_temp()
            op_map = {'!': 'NOT', '+': 'UPLUS', '-': 'UMINUS'}
            self.quartets.append(f"{op_map[expr.op]},{inner_ref},_,{temp}")
            expr._ref = temp
            return True

        if isinstance(expr, BinaryExpr):
            left_type, _ = self._infer_expr(expr.left, scope)
            right_type, _ = self._infer_expr(expr.right, scope)
            result_type, _ = self._infer_expr(expr, scope)

            if not (self._emit_expr_if_supported(expr.left, scope) and self._emit_expr_if_supported(expr.right, scope)):
                return False

            left_ref = self._expr_ref(expr.left, scope)
            right_ref = self._expr_ref(expr.right, scope)
            op = expr.op

            if op in {'+', '-', '*', '/'}:
                left_ref = self._emit_cast_ref(left_ref, left_type, result_type)
                right_ref = self._emit_cast_ref(right_ref, right_type, result_type)

            elif op in {'>', '>=', '<', '<='}:
                common_type = self._numeric_result_type(left_type, right_type)
                left_ref = self._emit_cast_ref(left_ref, left_type, common_type)
                right_ref = self._emit_cast_ref(right_ref, right_type, common_type)

            elif op == '==':
                if left_type != right_type:
                    if left_type in NUMERIC_TYPES and right_type in NUMERIC_TYPES:
                        common_type = self._numeric_result_type(left_type, right_type)
                        left_ref = self._emit_cast_ref(left_ref, left_type, common_type)
                        right_ref = self._emit_cast_ref(right_ref, right_type, common_type)
                    elif self._can_assign(left_type, right_type) and not self._can_assign(right_type, left_type):
                        left_ref = self._emit_cast_ref(left_ref, left_type, right_type)
                    elif self._can_assign(right_type, left_type) and not self._can_assign(left_type, right_type):
                        right_ref = self._emit_cast_ref(right_ref, right_type, left_type)

            temp = self._new_temp()
            op_map = {
                '+': 'ADD', '-': 'SUB', '*': 'MUL', '/': 'DIV',
                '>': 'GT', '>=': 'GTE', '<': 'LT', '<=': 'LTE',
                '==': 'EQ', '&&': 'AND', '||': 'OR',
            }
            self.quartets.append(
                f"{op_map[op]},{left_ref},{right_ref},{temp}"
            )
            expr._ref = temp
            return True

        return False

    # ===== Salida =====

    def symbols_lines(self) -> list[str]:
        lines = []
        for name in self.global_order:
            sym = self.global_scope.symbols[name]
            if self.has_control_or_functions:
                lines.append(f"{name}:{sym['type']}")
            else:
                lines.append(f"{name}:{sym['type']},{self._format_value(sym['value'])}")
        return lines

    def records_lines(self) -> list[str]:
        return [f"{name}:[{','.join(f'{f}:{t}' for f, t in fields)}]" for name, fields in self.records.items()]

    def functions_lines(self) -> list[str]:
        lines = []
        for name, overloads in self.functions.items():
            for overload in overloads:
                params = ','.join(f'{p}:{t}' for p, t in overload['params'])
                lines.append(f"{name}:[{params}],{overload['return_type']}")
        return lines

    def _format_value(self, value: Any) -> str:
        if isinstance(value, bool):
            return 'true' if value else 'false'
        if isinstance(value, str):
            return repr(value)
        if isinstance(value, dict):
            return '{' + ','.join(f'{k}:{self._format_value(v)}' for k, v in value.items()) + '}'
        return str(value)


# ===== Construcción del parser =====

def build_parser(**kwargs):
    return yacc.yacc(module=__import__(__name__), start=start, **kwargs)


# ===== Punto de entrada =====

def parse(data: str, **kwargs):
    lexer = lava_lexer.build_lexer()
    lexer.lineno = 1
    parser = build_parser(**kwargs)
    return parser.parse(data, lexer=lexer)


def parse_file(in_path: Path, data: str):
    program = parse(data)
    analyzer = Analyzer(program)
    analyzer.analyze()

    in_path.with_suffix('.symbols').write_text('\n'.join(analyzer.symbols_lines()) + '\n', encoding='utf-8')
    in_path.with_suffix('.records').write_text('\n'.join(analyzer.records_lines()) + '\n', encoding='utf-8')
    in_path.with_suffix('.functions').write_text('\n'.join(analyzer.functions_lines()) + '\n', encoding='utf-8')
    in_path.with_suffix('.quartets').write_text('\n'.join(analyzer.quartets) + '\n', encoding='utf-8')

    return analyzer
