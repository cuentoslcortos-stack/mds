# -*- coding: utf-8 -*-
"""CLI del motor RAG del Sistema MDS.

    python cli.py indexar [--forzar]
    python cli.py buscar "objeto a petit" [-k 6]
    python cli.py preguntar "¿que es el objeto a?" [--modo A|B] [--transcripcion ruta.txt]
    python cli.py servir [--puerto 8765]
    python cli.py calibrar
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mds_rag import config, embeddings, llm, prompt  # noqa: E402
from mds_rag.retrieval import Recuperador  # noqa: E402
from mds_rag.store import Store  # noqa: E402

SEP = "=" * 78


def _cargar():
    store = Store()
    rec = Recuperador(store) if store.listo else None
    return store, rec


def cmd_indexar(args) -> int:
    store, _ = _cargar()
    t0 = time.time()
    resultado = store.indexar(forzar=args.forzar, verbose=True)
    resultado["duracion_s"] = round(time.time() - t0, 2)
    print(SEP)
    print(f"Fragmentos indexados: {resultado['chunks']}")
    print(f"Documentos:           {len(store.documentos())}")
    print(f"Palabras:             {sum(f.palabras for f in store.fragmentos)}")
    print(f"Modelo de embeddings: {store.modelo}")
    print(f"Tiempo:               {resultado['duracion_s']}s")
    if resultado.get("procesados"):
        print(f"Procesados:           {', '.join(resultado['procesados'])}")
    return 0


def cmd_buscar(args) -> int:
    _, rec = _cargar()
    if rec is None:
        print("El indice esta vacio. Ejecuta primero: python cli.py indexar", file=sys.stderr)
        return 1
    resultados = rec.buscar(args.consulta, k=args.k)
    print(SEP)
    print(f'Consulta: "{args.consulta}"')
    for i, r in enumerate(resultados, start=1):
        print(f"\n[{i}] {r['score']:.3f}  (vec {r['score_vector']:.3f} / lex {r['score_lexico']:.3f})")
        print(f"    {r['documento']}")
        print(f"    {r['capitulo']}")
        if r["seccion"]:
            print(f"    > {r['seccion']}")
        texto = " ".join(r["texto"].split())
        print(f"    {texto[:400]}{'...' if len(texto) > 400 else ''}")
    return 0


def cmd_preguntar(args) -> int:
    store, rec = _cargar()
    if rec is None:
        print("El indice esta vacio. Ejecuta primero: python cli.py indexar", file=sys.stderr)
        return 1
    transcripcion = ""
    if args.transcripcion:
        transcripcion = Path(args.transcripcion).read_text(encoding="utf-8")
    resultados = rec.buscar(args.pregunta, k=args.k)
    contexto = rec.para_embedding(resultados)
    mensajes = prompt.construir_mensajes(
        args.pregunta, args.modo, transcripcion, contexto, []
    )
    print(SEP)
    print(f"Modelo: {args.modelo or config.LLM_MODEL} ({config.LLM_BACKEND})")
    print(f"Fragmentos recuperados: {len(resultados)}\n")
    partes = []
    for delta in llm.chat_stream(mensajes, modelo=args.modelo):
        partes.append(delta)
        sys.stdout.write(delta)
        sys.stdout.flush()
    print("\n" + SEP)
    print("FUENTES")
    for i, r in enumerate(resultados, start=1):
        ubic = r["capitulo"] + (f" > {r['seccion']}" if r["seccion"] else "")
        print(f"  [{i}] {r['documento']} — {ubic}  (score {r['score']:.3f})")
    return 0


def cmd_servir(args) -> int:
    from mds_rag import server

    server.servir(host=args.host, puerto=args.puerto)
    return 0


def cmd_calibrar(args) -> int:
    """Evalúa prefijos de embedding y muestra el ranking de una consulta de control."""
    store = Store()
    if not store.listo:
        print("El indice esta vacio. Ejecuta primero: python cli.py indexar", file=sys.stderr)
        return 1
    rec = Recuperador(store)
    consultas = [
        "significante y cadena significante",
        "forclusion y psicosis",
        "objeto a petit y goce",
        "represion y retorno de lo reprimido",
        "condensacion y desplazamiento como formaciones del inconsciente",
        "el significante del Otro y la demande",
    ]
    for consulta in consultas:
        print(SEP)
        print(f"Consulta: {consulta}")
        for r in rec.buscar(consulta, k=4):
            print(f"  {r['score']:.3f}  {r['archivo']}  {r['titulo'][:88]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cli.py", description="Motor RAG local del Sistema MDS"
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("indexar", help="Construye o actualiza el indice")
    p.add_argument("--forzar", action="store_true", help="Reembebe todo desde cero")
    p.set_defaults(func=cmd_indexar)

    p = sub.add_parser("buscar", help="Busca fragmentos sin llamar al modelo de lenguaje")
    p.add_argument("consulta")
    p.add_argument("-k", type=int, default=config.TOP_K)
    p.set_defaults(func=cmd_buscar)

    p = sub.add_parser("preguntar", help="Pregunta al corpus (RAG completo)")
    p.add_argument("pregunta")
    p.add_argument("--modo", choices=["A", "B", "a", "b"], default="A")
    p.add_argument("--transcripcion", help="Archivo de texto para el modo B")
    p.add_argument("-k", type=int, default=config.TOP_K)
    p.add_argument("--modelo")
    p.set_defaults(func=cmd_preguntar)

    p = sub.add_parser("servir", help="Levanta la API local")
    p.add_argument("--host", default=config.HOST)
    p.add_argument("--puerto", type=int, default=config.PUERTO)
    p.set_defaults(func=cmd_servir)

    p = sub.add_parser("calibrar", help="Muestra el ranking de consultas de control")
    p.set_defaults(func=cmd_calibrar)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
