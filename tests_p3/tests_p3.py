#!/usr/bin/env python3
"""
Ejecuta todos los tests en tests_p3/*.lava secuencialmente.
Después de cada test borra cualquier directorio __pycache__ (recursivo)
y los archivos `parser.out` y `parsetab.py` en la raíz del proyecto.
Registra la salida concatenada en `tests_p3/tests_p3.log`.
"""
import sys
import os
import glob
import shutil
import subprocess
import re


def remove_artifacts(root):
    # Elimina parser.out y parsetab.py si existen
    for name in ("parser.out", "parsetab.py"):
        path = os.path.join(root, name)
        if os.path.isfile(path):
            try:
                os.remove(path)
            except Exception as e:
                print(f"Warning: could not remove {path}: {e}")

    # Elimina recursivamente cualquier directorio __pycache__
    for dirpath, dirnames, _ in os.walk(root):
        if "__pycache__" in dirnames:
            full = os.path.join(dirpath, "__pycache__")
            try:
                shutil.rmtree(full)
            except Exception as e:
                print(f"Warning: could not remove {full}: {e}")

    # Elimina archivos generados con extensiones específicas (.quartets, .records, .symbols, .functions)
    exts = (".quartets", ".records", ".symbols", ".functions")
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if any(fname.endswith(ext) for ext in exts):
                full = os.path.join(dirpath, fname)
                try:
                    os.remove(full)
                except Exception as e:
                    print(f"Warning: could not remove generated file {full}: {e}")


def run_tests(tests_dir="tests_p3"):
    pattern = os.path.join(tests_dir, "*.lava")
    tests = sorted(glob.glob(pattern))
    if not tests:
        print(f"No hay tests en {tests_dir}")
        return 1

    root = os.getcwd()

    # Archivo log dentro de la carpeta de tests
    master_log = os.path.join(root, tests_dir, f"{tests_dir}.log")
    try:
        master_fh = open(master_log, "w", encoding="utf-8")
    except Exception as e:
        print(f"Warning: could not open master log {master_log}: {e}")
        master_fh = None

    for t in tests:
        print('\n' + '=' * 60)
        print(f"Ejecutando: {t}")

        cmd = [sys.executable, "main.py", t]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        # Añade al log maestro e incluye el contenido del test
        header = f"\n{'=' * 60}\nEjecutando: {t}\n"

        # Lee el contenido del test para incluirlo en el log
        try:
            with open(t, "r", encoding="utf-8") as tf:
                test_content = tf.read()
        except Exception as e:
            test_content = f"Warning: could not read test file {t}: {e}\n"
        # Prepara el contenido adicional de los archivos generados (.quartets, .records, .symbols, .functions)
        def collect_generated_contents(root_dir):
            exts = (".quartets", ".records", ".symbols", ".functions")
            parts = []
            for dirpath, _, filenames in os.walk(root_dir):
                for fname in filenames:
                    if any(fname.endswith(ext) for ext in exts):
                        full = os.path.join(dirpath, fname)
                        try:
                            with open(full, "r", encoding="utf-8", errors="replace") as fh:
                                content = fh.read()
                        except Exception as e:
                            content = f"Warning: could not read generated file {full}: {e}\n"
                        rel = os.path.relpath(full, root_dir)
                        parts.append(f"\n--- Contenido de: {rel} ---\n")
                        parts.append(content)
            return "".join(parts)

        files_content = collect_generated_contents(root)

        # Inserta los contenidos justo después de la línea que contiene "Generating LALR tables"
        def inject_after_marker(output, marker_regex, insert_text):
            if not insert_text:
                return output
            m = re.search(marker_regex, output)
            if m:
                return output[: m.end()] + insert_text + output[m.end() :]
            return output + "\n" + insert_text

        raw_output = proc.stdout or ""
        marker = r"Generating LALR tables.*(?:\r?\n)"
        final_output = inject_after_marker(raw_output, marker, files_content)

        if master_fh:
            try:
                master_fh.write(header)
                master_fh.write("Contenido del test:\n")
                master_fh.write(test_content)
                master_fh.write("\n" + "=" * 60 + "\n")
                master_fh.write(final_output)
                master_fh.write(f"\nExit code: {proc.returncode}\n")
                master_fh.flush()
            except Exception as e:
                print(f"Warning: could not write to master log {master_log}: {e}")

        # Imprime en consola para feedback inmediato
        print(f"Salida añadida a: {master_log}")
        print(f"Exit code: {proc.returncode}\n")

        # Elimina los archivos después de cada test
        remove_artifacts(root)

    if master_fh:
        master_fh.close()
    return 0


if __name__ == "__main__":
    sys.exit(run_tests())
