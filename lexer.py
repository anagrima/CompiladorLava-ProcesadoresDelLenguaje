# Analizador léxico para la P1 de Lava utilizando PLY, que define:
# - El conjunto de tokens del lenguaje
# - Las reglas léxicas mediante expresiones regulares 
# - El tratamiento de palabras reservadas
# - La gestión de comentarios y espacios en blanco

import ply.lex as lex
from ply.lex import TOKEN


# ===== Palabras reservadas =====
reserved = (
    "TRUE",
    "BOOLEAN",
    "DO",
    "FALSE",
    "VOID",
    "WHILE",
    "INT",
    "RETURN",
    "PRINT",
    "FLOAT",
    "IF",
    "NEW",
    "CHAR",
    "ELSE",
    "RECORD",
    "BREAK",
)

reserved_map = {}
for r_type in reserved:
    reserved_map[r_type.lower()] = r_type


# ===== Funciones auxiliares =====

# Devuelve la posición del 1er carácter de la línea donde cae lexpos
def _line_start_pos(lexdata: str, lexpos: int) -> int:
    return lexdata.rfind('\n', 0, lexpos) + 1

# Devuelve el string
def _set_token_meta(t, lexeme=None):
    if lexeme is None:
        lexeme = t.value

    col_start = t.lexpos - _line_start_pos(t.lexer.lexdata, t.lexpos)
    col_end = col_start + len(str(lexeme))

    t.lexeme = str(lexeme)
    t.col_start = col_start
    t.col_end = col_end
    return t


# ===== Tokens =====

tokens = reserved + (
    # Identificadores y literales
    "ID",
    "INT_VALUE",
    "FLOAT_VALUE",
    "CHAR_VALUE",
    # Operadores (comparación / booleanos / aritmética)
    "ASSIGN",   # =
    "EQ",       # ==
    "GT",       # >
    "GE",       # >=
    "LT",       # <
    "LE",       # <=
    "PLUS",     # +
    "MINUS",    # -
    "TIMES",    # *
    "DIVIDE",   # /
    "AND",      # &&
    "OR",       # ||
    "NOT",      # !
    # Separadores / puntuación
    "LPAREN",   # (
    "RPAREN",   # )
    "LBRACE",   # {
    "RBRACE",   # }
    "COMMA",    # ,
    "SEMICOLON",# ;
    "DOT",      # .
) 


# ===== Reglas simples =====

# Comparación (orden importante: >= antes que >, etc.)
def t_GE(t):
    r">="
    return _set_token_meta(t)

def t_LE(t):
    r"<="
    return _set_token_meta(t)

def t_EQ(t):
    r"=="
    return _set_token_meta(t)

def t_GT(t):
    r">"
    return _set_token_meta(t)

def t_LT(t):
    r"<"
    return _set_token_meta(t)

def t_ASSIGN(t):
    r"="
    return _set_token_meta(t)

# Lógicos
def t_AND(t):
    r"&&"
    return _set_token_meta(t)

def t_OR(t):
    r"\|\|"
    return _set_token_meta(t)

def t_NOT(t):
    r"!"
    return _set_token_meta(t)

# Aritméticos
def t_PLUS(t):
    r"\+"
    return _set_token_meta(t)

def t_MINUS(t):
    r"-"
    return _set_token_meta(t)

# Separadores 
def t_LPAREN(t):
    r"\("
    return _set_token_meta(t)

def t_RPAREN(t):
    r"\)"
    return _set_token_meta(t)

def t_LBRACE(t):
    r"\{"
    return _set_token_meta(t)

def t_RBRACE(t):
    r"\}"
    return _set_token_meta(t)

def t_COMMA(t):
    r","
    return _set_token_meta(t)

def t_SEMICOLON(t):
    r";"
    return _set_token_meta(t)

def t_DOT(t):
    r"\."
    return _set_token_meta(t)



# ===== Ignorar espacios y tabs =====
t_ignore = " \t"



# ===== Ignorar comentarios =====
# // ... fin de línea
# /* ... */ multilínea 

def t_NEWLINE(t):
    r"\n+"
    t.lexer.lineno += len(t.value)

# Comentarios de una línea
def t_LINE_COMMENT(_):
    r"//[^\n]*"
    return None

states = (("comment", "exclusive"),)

# Comentarios multi-línea (estado exclusivo para evitar expresión regular grande)
def t_MLCOMMENT_START(t):
    r"/\*"
    t.lexer.comment_start_line = t.lineno
    t.lexer.begin("comment")

def t_comment_END(t):
    r"\*/"
    t.lexer.begin("INITIAL")

def t_comment_NEWLINE(t):
    r"\n+"
    t.lexer.lineno += len(t.value)

def t_comment_content(_):
    r"[^*\n]+|\*+[^*/\n]*"
    pass

t_comment_ignore = ""

def t_comment_error(t):
    t.lexer.skip(1)

def t_comment_eof(t):
    start = getattr(t.lexer, "comment_start_line", t.lexer.lineno)
    print(f"Unterminated comment starting at line {start}")
    return None

# ===== Reglas para tokens con procesamiento adicional =====
def t_TIMES(t):
    r"\*"
    return _set_token_meta(t)

def t_DIVIDE(t):
    r"/"
    return _set_token_meta(t)

# ===== Literales =====
# Se combinan las distintas bases en una expresión mediante grupos no capturadores (?:) para simplificar la definición del token entero

# Enteros
_int_dec = r'(0|[1-9][0-9]*)'
_int_bin = r'0b[01]+'
_int_oct = r'0[0-7]+'
_int_hex = r'0x[0-9A-Fa-f]+'
_int_value = rf'(?:{_int_bin}|{_int_hex}|{_int_oct}|{_int_dec})'

# Reales
_float_dot = rf'(?:{_int_dec})\.[0-9]+'
# Se permite notación científica con 'e' o 'E' para mayor robustez, aunque el enunciado solo ejemplifica la 'e' minúscula
_float_sci = rf'(?:{_float_dot}|{_int_dec})[eE][+\-]?{_int_dec}'
_float_value = rf'(?:{_float_sci}|{_float_dot})'

# Floats
@TOKEN(_float_value)
def t_FLOAT_VALUE(t):
    lexeme = t.value
    t.value = float(t.value)
    return _set_token_meta(t, lexeme)

# INT
# La conversión se hace manualmente, ya que Python no interpreta automáticamente ciertas formas
@TOKEN(_int_value)
def t_INT_VALUE(t):
    lexeme = t.value
    s = t.value

    if s.startswith('0b'):
        t.value = int(s[2:], 2)

    elif s.startswith('0x'):
        t.value = int(s[2:], 16)

    elif len(s) > 1 and s.startswith('0') and all(c in '01234567' for c in s[1:]):
        t.value = int(s[1:], 8)

    else:
        t.value = int(s, 10)

    return _set_token_meta(t, lexeme)


# CHAR
# Literal CHAR entre comillas simples. Se permiten los escapes comunes \n, \t, \r, \', \\
def t_CHAR_VALUE(t):
    r"\'([^\\\n]|(\\.))\'"

    lexeme = t.value
    raw = t.value[1:-1]

    if raw.startswith('\\'):
        esc = raw[1:]

        if esc == 'n':
            t.value = '\n'
        elif esc == 't':
            t.value = '\t'
        elif esc == 'r':
            t.value = '\r'
        elif esc == "'":
            t.value = "'"
        elif esc == '\\':
            t.value = '\\'
        else:
            t.value = esc[0]

    else:
        t.value = raw

    return _set_token_meta(t, lexeme)

def t_ID(t):
    r"[a-zA-Z_][a-zA-Z0-9_]*"
    lexeme = t.value
    t.type = reserved_map.get(t.value, "ID")

    if t.type == "TRUE":
        t.value = True
    elif t.type == "FALSE":
        t.value = False

    return _set_token_meta(t, lexeme)


# ===== Manejo de errores =====

def t_error(t):
    print(f"[ERROR] Token ilegal {t.value[0]!r} en la línea {t.lineno}")
    t.lexer.skip(1)

def build_lexer(**kwargs):
    return lex.lex(**kwargs)