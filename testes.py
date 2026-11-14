"""Executa os casos de teste do scanner e salva as saidas em saidas/."""
import os
import subprocess
import sys

CASOS = [
    ("T1", "valido",   ["resultado = (4 + 2) * 3;"]),
    ("T2", "valido",   ["mostre preco * 1.5; # exibe o preco"]),
    ("T3", "valido",   ["media = nota1 + nota2 * peso - 10 / 2;"]),
    ("T4", "invalido", ["total = 10 $ 5;"]),
    ("T5", "invalido", ["nota = 7,5;"]),
    ("T6", "invalido", ["x = (4 + * 2;", "--ast"]),
    ("T7", "valido",   ["--arquivo", "exemplo.mq"]),
    ("E1", "expressao", ["--ast", "--tac", "area = (base + 2) * altura / 4;"]),
    ("E2", "expressao", ["--ast", "--tac", "media = nota1 + nota2 * peso - 10 / 2;"]),
]

os.makedirs("saidas", exist_ok=True)
for nome, tipo, args in CASOS:
    cmd = [sys.executable, "moqueca.py", *args]
    saida = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8").stdout
    mostra = " ".join(f'"{a}"' if " " in a else a for a in args)
    texto = f"$ python moqueca.py {mostra}\n{saida}"
    with open(f"saidas/{nome}.txt", "w", encoding="utf-8") as f:
        f.write(texto)
    print(f"[{nome}] ({tipo})\n{texto}")
