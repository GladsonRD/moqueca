"""
Moqueca - mini-linguagem didatica para atribuicoes e expressoes aritmeticas.
Linguagens Formais e Compiladores - Multivix Vitoria - 2026/2

Etapas implementadas:
  1. Scanner (analise lexica)            -> obrigatorio
  2. Parser descendente recursivo + AST  -> apoio a analise sintatica
  3. Gerador de codigo de tres enderecos -> opcional (automatizado)

Uso:
  python moqueca.py "resultado = (4 + 2) * 3;"            # so tokens
  python moqueca.py --ast --tac "media = a + b * c;"     # tokens, AST e TAC
  python moqueca.py --arquivo exemplo.mq --ast --tac
"""
import re
import sys
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# 1. ANALISE LEXICA
# ---------------------------------------------------------------------------
PALAVRAS_RESERVADAS = {"mostre": "PAL_RESERVADA"}

# A ORDEM da lista define a prioridade em caso de conflito:
#   - NUM_REAL vem antes de NUM_INT  (3.14 nao vira "3" + ".14")
#   - IDENT reconhece a maior sequencia possivel (maximal munch) e so
#     depois verifica se o lexema e palavra reservada ("mostre" x "mostrei").
ESPECIFICACAO = [
    ("COMENTARIO", r"\#[^\n]*"),
    ("ESPACO",     r"[ \t\r\n]+"),
    ("NUM_REAL",   r"\d+\.\d+"),
    ("NUM_INT",    r"\d+"),
    ("IDENT",      r"[A-Za-z_][A-Za-z0-9_]*"),
    ("ATRIB",      r"="),
    ("OP_SOMA",    r"\+"),
    ("OP_SUB",     r"-"),
    ("OP_MUL",     r"\*"),
    ("OP_DIV",     r"/"),
    ("ABRE_PAR",   r"\("),
    ("FECHA_PAR",  r"\)"),
    ("PONTO_VIRG", r";"),
]
IGNORADOS = {"ESPACO", "COMENTARIO"}
REGEX = [(nome, re.compile(padrao)) for nome, padrao in ESPECIFICACAO]


@dataclass
class Token:
    tipo: str
    lexema: str
    linha: int
    coluna: int


@dataclass
class ErroLexico:
    caractere: str
    linha: int
    coluna: int

    def __str__(self):
        return (f"Erro lexico: caractere desconhecido '{self.caractere}' "
                f"na linha {self.linha}, coluna {self.coluna}")


def scanner(codigo):
    """Le o codigo da esquerda para a direita e devolve (tokens, erros)."""
    tokens, erros = [], []
    pos, linha, inicio_linha = 0, 1, 0
    while pos < len(codigo):
        coluna = pos - inicio_linha + 1
        for nome, regex in REGEX:
            m = regex.match(codigo, pos)
            if m:
                lexema = m.group(0)
                if nome == "IDENT":
                    nome = PALAVRAS_RESERVADAS.get(lexema, "IDENT")
                if nome not in IGNORADOS:
                    tokens.append(Token(nome, lexema, linha, coluna))
                # atualiza contagem de linhas
                quebras = lexema.count("\n")
                if quebras:
                    linha += quebras
                    inicio_linha = pos + lexema.rfind("\n") + 1
                pos = m.end()
                break
        else:
            # Recuperacao de erro lexico (modo panico minimo):
            # registra o caractere, descarta-o e continua a leitura.
            erros.append(ErroLexico(codigo[pos], linha, coluna))
            pos += 1
    tokens.append(Token("EOF", "", linha, pos - inicio_linha + 1))
    return tokens, erros


# ---------------------------------------------------------------------------
# 2. ANALISE SINTATICA (descendente recursiva) E AST
#
#   programa -> comando*
#   comando  -> IDENT '=' expr ';' | 'mostre' expr ';'
#   expr     -> termo (('+' | '-') termo)*
#   termo    -> fator (('*' | '/') fator)*
#   fator    -> NUM_INT | NUM_REAL | IDENT | '(' expr ')' | '-' fator
# ---------------------------------------------------------------------------
@dataclass
class Num:
    valor: str


@dataclass
class Var:
    nome: str


@dataclass
class BinOp:
    op: str
    esq: object
    dir: object


@dataclass
class UnOp:
    op: str
    expr: object


@dataclass
class Atrib:
    alvo: str
    expr: object


@dataclass
class Mostre:
    expr: object


class ErroSintatico(Exception):
    def __init__(self, msg, token):
        super().__init__(f"Erro sintatico: {msg} (encontrado '{token.lexema or 'fim'}' "
                         f"na linha {token.linha}, coluna {token.coluna})")
        self.token = token


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0
        self.erros = []

    def atual(self):
        return self.tokens[self.i]

    def consome(self, tipo, msg):
        tok = self.atual()
        if tok.tipo != tipo:
            raise ErroSintatico(msg, tok)
        self.i += 1
        return tok

    def programa(self):
        comandos = []
        while self.atual().tipo != "EOF":
            try:
                comandos.append(self.comando())
            except ErroSintatico as e:
                self.erros.append(e)
                self.sincroniza()
        return comandos

    def sincroniza(self):
        """Recuperacao em modo panico: descarta tokens ate o proximo ';'."""
        while self.atual().tipo not in ("PONTO_VIRG", "EOF"):
            self.i += 1
        if self.atual().tipo == "PONTO_VIRG":
            self.i += 1

    def comando(self):
        tok = self.atual()
        if tok.tipo == "PAL_RESERVADA" and tok.lexema == "mostre":
            self.i += 1
            e = self.expr()
            self.consome("PONTO_VIRG", "esperado ';' ao final do comando")
            return Mostre(e)
        alvo = self.consome("IDENT", "esperado identificador ou 'mostre' no inicio do comando")
        self.consome("ATRIB", "esperado '=' apos o identificador")
        e = self.expr()
        self.consome("PONTO_VIRG", "esperado ';' ao final do comando")
        return Atrib(alvo.lexema, e)

    def expr(self):
        no = self.termo()
        while self.atual().tipo in ("OP_SOMA", "OP_SUB"):
            op = self.atual().lexema
            self.i += 1
            no = BinOp(op, no, self.termo())      # associatividade a esquerda
        return no

    def termo(self):
        no = self.fator()
        while self.atual().tipo in ("OP_MUL", "OP_DIV"):
            op = self.atual().lexema
            self.i += 1
            no = BinOp(op, no, self.fator())
        return no

    def fator(self):
        tok = self.atual()
        if tok.tipo in ("NUM_INT", "NUM_REAL"):
            self.i += 1
            return Num(tok.lexema)
        if tok.tipo == "IDENT":
            self.i += 1
            return Var(tok.lexema)
        if tok.tipo == "ABRE_PAR":
            self.i += 1
            e = self.expr()
            self.consome("FECHA_PAR", "esperado ')' para fechar a expressao")
            return e
        if tok.tipo == "OP_SUB":
            self.i += 1
            return UnOp("-", self.fator())
        raise ErroSintatico("esperado numero, identificador, '(' ou '-'", tok)


def ast_texto(no, prefixo="", ultimo=True, raiz=True):
    """Desenha a AST em texto (formato de arvore de diretorios)."""
    if isinstance(no, Atrib):
        rotulo, filhos = f"= (atribuicao)", [Var(no.alvo), no.expr]
    elif isinstance(no, Mostre):
        rotulo, filhos = "mostre", [no.expr]
    elif isinstance(no, BinOp):
        rotulo, filhos = no.op, [no.esq, no.dir]
    elif isinstance(no, UnOp):
        rotulo, filhos = f"{no.op} (unario)", [no.expr]
    elif isinstance(no, Num):
        rotulo, filhos = no.valor, []
    else:
        rotulo, filhos = no.nome, []
    if raiz:
        linhas = [rotulo]
        novo = ""
    else:
        linhas = [prefixo + ("└── " if ultimo else "├── ") + rotulo]
        novo = prefixo + ("    " if ultimo else "│   ")
    for k, f in enumerate(filhos):
        linhas.extend(ast_texto(f, novo, k == len(filhos) - 1, False))
    return linhas


def ast_dot(no, nome="AST"):
    """Gera a AST no formato DOT (Graphviz) para virar imagem."""
    linhas = [f'digraph {nome} {{', '  node [fontname="Helvetica", fontsize=13];']
    cont = [0]

    def desenha(ident, rotulo, forma, cor):
        linhas.append(f'  {ident} [label="{rotulo}", shape={forma}, '
                      f'style=filled, fillcolor="{cor}"];')

    def visita(n):
        cont[0] += 1
        meu = f"n{cont[0]}"
        if isinstance(n, Atrib):
            desenha(meu, "=", "box", "#f4d6a0")
            filhos = [Var(n.alvo), n.expr]
        elif isinstance(n, Mostre):
            desenha(meu, "mostre", "box", "#f4d6a0")
            filhos = [n.expr]
        elif isinstance(n, BinOp):
            desenha(meu, n.op, "circle", "#cfe3f5")
            filhos = [n.esq, n.dir]
        elif isinstance(n, UnOp):
            desenha(meu, "-u", "circle", "#cfe3f5")
            filhos = [n.expr]
        elif isinstance(n, Num):
            desenha(meu, n.valor, "ellipse", "white")
            filhos = []
        else:
            desenha(meu, n.nome, "ellipse", "#e3f0d8")
            filhos = []
        for f in filhos:
            linhas.append(f"  {meu} -> {visita(f)};")
        return meu

    visita(no)
    linhas.append("}")
    return "\n".join(linhas)


# ---------------------------------------------------------------------------
# 3. CODIGO DE TRES ENDERECOS (percurso pos-ordem da AST)
# ---------------------------------------------------------------------------
class GeradorTAC:
    def __init__(self):
        self.codigo = []
        self.n = 0

    def novo_temp(self):
        self.n += 1
        return f"t{self.n}"

    def gera(self, no):
        if isinstance(no, Num):
            return no.valor
        if isinstance(no, Var):
            return no.nome
        if isinstance(no, UnOp):
            a = self.gera(no.expr)
            t = self.novo_temp()
            self.codigo.append(f"{t} = - {a}")
            return t
        if isinstance(no, BinOp):
            a = self.gera(no.esq)      # primeiro a subarvore esquerda
            b = self.gera(no.dir)      # depois a direita
            t = self.novo_temp()
            self.codigo.append(f"{t} = {a} {no.op} {b}")
            return t
        if isinstance(no, Atrib):
            r = self.gera(no.expr)
            self.codigo.append(f"{no.alvo} = {r}")
        if isinstance(no, Mostre):
            r = self.gera(no.expr)
            self.codigo.append(f"print {r}")


# ---------------------------------------------------------------------------
# Interface de linha de comando
# ---------------------------------------------------------------------------
def imprime_tokens(tokens, erros):
    print(f"{'#':>3}  {'TIPO':<14} {'LEXEMA':<12} {'LIN:COL'}")
    print("-" * 42)
    for k, t in enumerate(tokens, 1):
        print(f"{k:>3}  {t.tipo:<14} {t.lexema!r:<12} {t.linha}:{t.coluna}")
    if erros:
        print()
        for e in erros:
            print(e)
    else:
        print("\nNenhum erro lexico encontrado.")


def main(argv):
    mostrar_ast = "--ast" in argv
    mostrar_tac = "--tac" in argv
    args = [a for a in argv if a not in ("--ast", "--tac")]
    if args and args[0] == "--arquivo":
        with open(args[1], encoding="utf-8") as f:
            codigo = f.read()
    elif args:
        codigo = " ".join(args)
    else:
        codigo = input("moqueca> ")

    print(f"Entrada: {codigo.strip()}\n")
    tokens, erros = scanner(codigo)
    imprime_tokens(tokens, erros)

    if not (mostrar_ast or mostrar_tac):
        return
    parser = Parser(tokens)
    comandos = parser.programa()
    for e in parser.erros:
        print(e)
    if erros or parser.erros:
        print("\nAST e codigo intermediario nao gerados: corrija os erros acima.")
        return
    if mostrar_ast:
        for c in comandos:
            print("\nAST:")
            print("\n".join(ast_texto(c)))
    if mostrar_tac:
        print("\nCodigo de tres enderecos:")
        g = GeradorTAC()
        for c in comandos:
            g.gera(c)
        print("\n".join(g.codigo))


if __name__ == "__main__":
    main(sys.argv[1:])
