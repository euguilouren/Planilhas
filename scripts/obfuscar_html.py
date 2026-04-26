#!/usr/bin/env python3
"""
Extrai os blocos <script> inline do HTML, obfusca com javascript-obfuscator
e reconstrói o arquivo com o JS ofuscado.

Uso:
    python3 scripts/obfuscar_html.py index.html dist/index.html
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path


OBFUSCATOR_FLAGS = [
    '--compact', 'true',
    '--control-flow-flattening', 'true',
    '--control-flow-flattening-threshold', '0.4',
    '--identifier-names-generator', 'hexadecimal',
    '--rename-globals', 'false',
    '--self-defending', 'true',
    '--domain-lock', 'euguilouren.github.io',
    '--string-array', 'true',
    '--string-array-encoding', 'base64',
    '--string-array-threshold', '0.75',
    '--dead-code-injection', 'false',
    '--unicode-escape-sequence', 'false',
]


def obfuscar(js_src: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        inp = Path(tmp) / 'bundle.js'
        out = Path(tmp) / 'bundle.obf.js'
        inp.write_text(js_src, encoding='utf-8')
        cmd = ['javascript-obfuscator', str(inp), '--output', str(out)] + OBFUSCATOR_FLAGS
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print('[obfuscar] ERRO:', result.stderr, file=sys.stderr)
            sys.exit(1)
        return out.read_text(encoding='utf-8')


def processar(src_path: Path, dst_path: Path) -> None:
    html = src_path.read_text(encoding='utf-8')

    # Encontra blocos <script> inline (ignora <script src=...>)
    pattern = re.compile(r'(<script>)(.*?)(</script>)', re.DOTALL)
    scripts = pattern.findall(html)

    if not scripts:
        print('[obfuscar] Nenhum bloco <script> inline encontrado.', file=sys.stderr)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        dst_path.write_text(html, encoding='utf-8')
        return

    # Concatena todos os scripts inline em um bundle
    bundle = '\n'.join(s[1] for s in scripts)
    print(f'[obfuscar] {len(scripts)} bloco(s) JS encontrado(s), {len(bundle)} chars')

    bundle_obf = obfuscar(bundle)
    print(f'[obfuscar] Obfuscado: {len(bundle_obf)} chars')

    # Substitui todos os blocos inline pelo bundle ofuscado (apenas no primeiro, remove os demais)
    first = True

    def substituir(m: re.Match) -> str:
        nonlocal first
        if first:
            first = False
            return f'<script>{bundle_obf}</script>'
        return ''

    html_out = pattern.sub(substituir, html)
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    dst_path.write_text(html_out, encoding='utf-8')
    print(f'[obfuscar] Salvo em {dst_path} ({len(html_out)} chars)')


def main() -> None:
    if len(sys.argv) != 3:
        print('Uso: obfuscar_html.py <entrada.html> <saida.html>', file=sys.stderr)
        sys.exit(1)
    processar(Path(sys.argv[1]), Path(sys.argv[2]))


if __name__ == '__main__':
    main()
