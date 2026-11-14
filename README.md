# Moqueca – mini-linguagem didática

Trabalho da Avaliação Processual (2º bimestre/2026) de **Linguagens Formais e Compiladores** – Multivix Vitória.

Moqueca reconhece atribuições e expressões aritméticas (`+ - * /`, parênteses e menos unário) e um comando de saída `mostre`.

```
area = (base + 2) * altura / 4;
mostre area;
```

## Como executar (Python 3.8+)

```bash
python moqueca.py "resultado = (4 + 2) * 3;"            # tokens (scanner)
python moqueca.py --ast --tac "media = a + b * c;"     # tokens + AST + código de 3 endereços
python moqueca.py --arquivo exemplo.mq --ast --tac     # lê um arquivo
python testes.py                                       # executa todos os casos de teste
```

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `moqueca.py` | scanner, parser descendente recursivo, AST e gerador de código de três endereços |
| `testes.py` | casos de teste T1–T7, E1 e E2; grava as saídas em `saidas/` |
| `exemplo.mq` | programa de exemplo com várias linhas |
| `saidas/` | saídas reais obtidas na execução dos testes |
