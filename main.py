# Programa principal de la Práctica 3, que:
# - Lee el fichero fuente Lava proporcionado por línea de comandos
# - Ejecuta el análisis completo (léxico, sintáctico y semántico)
# - Usa el analizador léxico de lexer.py durante el parseo
# - Genera los ficheros de salida del análisis semántico (.symbols, .records, .functions)
# - Opcionalmente, con --token, genera un fichero <nombre>.token como en la P1

import sys
from pathlib import Path

import lexer as lava_lexer
import parser as lava_parser


# ===== Funciones auxiliares =====

# Normaliza saltos de línea para evitar problemas en Windows (CRLF = \r\n)
def normalize_newlines(text: str) -> str:
    return text.replace('\r\n', '\n').replace('\r', '\n')


# Devuelve el string (se imprime en el campo VALOR del token)
# Para literales numéricos, el lexer ya convierte a int/float y aquí los pasamos a string
# Para el resto, se usa el lexema original para mantener exactamente el texto de entrada
def token_value_str(tok) -> str:
    if tok.type in ("INT_VALUE", "FLOAT_VALUE"):
        return str(tok.value)
    return tok.lexeme


# ===== Modos de ejecución =====

# Ejecuta solo el analizador léxico y genera el fichero .token
def run_lexer_mode(in_path: Path, data: str):
    lx = lava_lexer.build_lexer()
    lx.lineno = 1
    lx.input(data)

    out_lines = []

    # Pedimos tokens hasta EOF
    while True:
        tok = lx.token()
        if not tok:
            break

        out_lines.append(
            f"{tok.type}, {token_value_str(tok)}, {tok.lineno}, {tok.col_start}, {tok.col_end}"
        )

    out_path = in_path.with_suffix('.token')
    out_path.write_text("\n".join(out_lines) + ("\n" if out_lines else ""), encoding='utf-8')


# Ejecuta el análisis completo (léxico, sintáctico y semántico)
# Si el fichero es correcto:
# - No muestra salida por consola
# - Genera los ficheros .symbols, .records, .functions y opcionalmente .quartets
# Si hay errores:
# - Se muestran por consola

def run_full_mode(in_path: Path, data: str):
    lava_parser.parse_file(in_path, data)


# ===== Programa principal =====

def main():
    if len(sys.argv) == 2:
        token_mode = False
        in_path = Path(sys.argv[1])

    elif len(sys.argv) == 3 and sys.argv[1] == '--token':
        token_mode = True
        in_path = Path(sys.argv[2])

    else:
        print('Uso: python main.py <file.lava>')
        print('   o: python main.py --token <file.lava>')
        sys.exit(1)

    if not in_path.exists():
        print(f'No existe el archivo: {in_path}')
        sys.exit(1)

    try:
        # Lee fichero completo
        raw = in_path.read_text(encoding='utf-8')
        data = normalize_newlines(raw)

        if token_mode:
            run_lexer_mode(in_path, data)
        else:
            run_full_mode(in_path, data)

    except (SyntaxError, lava_parser.SemanticError) as e:
        print(e)
        sys.exit(1)


if __name__ == '__main__':
    main()
