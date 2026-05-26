"""
Multi-Agent Text-to-SQL Pipeline
Spider Benchmark — Groq-powered fast inference

Usage:
  python main.py
  python main.py --schema concert_singer --query "How many singers are there?"
  python main.py --batch   (run all sample queries)
  python main.py --schema world_1
"""

import argparse
import time
import json
import os
from datetime import datetime
from dotenv import load_dotenv

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from utils.groq_client import GroqClient
from schemas.spider_schemas import SCHEMAS, get_schema_string, list_schemas
from agents.query_planner import QueryPlannerAgent
from agents.schema_reasoner import SchemaReasonerAgent
from agents.sql_generator import SQLGeneratorAgent
from agents.sql_validator import SQLValidatorAgent

load_dotenv()
console = Console()


class MultiAgentPipeline:
    def __init__(self):
        self.groq = GroqClient()
        self.planner = QueryPlannerAgent(self.groq)
        self.schema_reasoner = SchemaReasonerAgent(self.groq)
        self.sql_generator = SQLGeneratorAgent(self.groq)
        self.validator = SQLValidatorAgent(self.groq)

    def run(self, question: str, schema_name: str, verbose: bool = True) -> dict:
        schema_str = get_schema_string(schema_name)
        results = {"question": question, "schema": schema_name, "agents": {}, "final_sql": ""}
        start = time.time()

        agents_config = [
            ("planner",    "Agent 1 · Query Planner",    "cyan",    lambda: self.planner.run(question, schema_str)),
            ("schema",     "Agent 2 · Schema Reasoner",  "blue",    lambda: self.schema_reasoner.run(question, schema_str, results["agents"].get("planner", {}))),
            ("generator",  "Agent 3 · SQL Generator",    "magenta", lambda: None),
            ("validator",  "Agent 4 · SQL Validator",    "green",   lambda: None),
        ]

        if verbose:
            console.print()
            console.rule(f"[bold]Multi-Agent Text-to-SQL Pipeline[/bold]")
            console.print(f"[dim]Schema:[/dim] [cyan]{schema_name}[/cyan]  [dim]Model:[/dim] [cyan]{self.groq.model}[/cyan]")
            console.print(f"[dim]Question:[/dim] [bold white]{question}[/bold white]")
            console.print()

        # Agent 1 — Query Planner
        if verbose: console.print(Panel("[bold cyan]Agent 1 · Query Planner[/bold cyan]", expand=False))
        with _spinner("Planning query..."):
            planner_out = self.planner.run(question, schema_str)
        results["agents"]["planner"] = planner_out
        if verbose:
            console.print(planner_out["raw_output"])
            console.print()

        # Agent 2 — Schema Reasoner
        if verbose: console.print(Panel("[bold blue]Agent 2 · Schema Reasoner[/bold blue]", expand=False))
        with _spinner("Reasoning over schema..."):
            schema_out = self.schema_reasoner.run(question, schema_str, planner_out)
        results["agents"]["schema"] = schema_out
        if verbose:
            console.print(schema_out["raw_output"])
            console.print()

        # Agent 3 — SQL Generator
        if verbose: console.print(Panel("[bold magenta]Agent 3 · SQL Generator[/bold magenta]", expand=False))
        with _spinner("Generating SQL..."):
            gen_out = self.sql_generator.run(question, schema_str, planner_out, schema_out)
        results["agents"]["generator"] = gen_out
        if verbose:
            console.print(f"[bold green]Generated SQL:[/bold green]")
            console.print(Panel(gen_out["sql"], style="green", expand=False))
            console.print()

        # Agent 4 — SQL Validator
        if verbose: console.print(Panel("[bold green]Agent 4 · SQL Validator[/bold green]", expand=False))
        with _spinner("Validating SQL..."):
            val_out = self.validator.run(question, schema_str, gen_out["sql"])
        results["agents"]["validator"] = val_out
        if verbose:
            console.print(val_out["raw_output"])
            console.print()

        results["final_sql"] = val_out["final_sql"]
        results["verdict"] = val_out["parsed"].get("verdict", "UNKNOWN")
        results["score"] = val_out["parsed"].get("score", "?")
        results["elapsed"] = round(time.time() - start, 2)

        if verbose:
            _print_summary(results)

        return results


def _spinner(msg):
    return Progress(SpinnerColumn(), TextColumn(f"[dim]{msg}[/dim]"), transient=True)


def _print_summary(results):
    console.rule("[bold]Pipeline Summary[/bold]")
    verdict = results["verdict"]
    color = "green" if "APPROVED" in verdict else "yellow"

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column(style="dim", width=18)
    table.add_column()
    table.add_row("Question", results["question"])
    table.add_row("Schema", results["schema"])
    table.add_row("Verdict", f"[{color}]{verdict}[/{color}]")
    table.add_row("Score", results["score"])
    table.add_row("Time", f"{results['elapsed']}s")
    console.print(table)

    console.print(f"\n[bold green]✓ Final SQL:[/bold green]")
    console.print(Panel(results["final_sql"], style="bold green", expand=False))
    console.print()


def interactive_mode(pipeline: MultiAgentPipeline):
    console.print(Panel(
        "[bold]Multi-Agent Text-to-SQL System[/bold]\n"
        "[dim]Spider Benchmark · Groq-powered[/dim]",
        expand=False
    ))

    schemas = list_schemas()
    console.print("\n[bold]Available schemas:[/bold]")
    for i, s in enumerate(schemas):
        desc = SCHEMAS[s]["description"]
        console.print(f"  [{i+1}] [cyan]{s}[/cyan] — {desc}")

    schema_input = console.input("\n[bold]Select schema (number or name):[/bold] ").strip()
    if schema_input.isdigit():
        idx = int(schema_input) - 1
        schema_name = schemas[idx] if 0 <= idx < len(schemas) else schemas[0]
    elif schema_input in SCHEMAS:
        schema_name = schema_input
    else:
        schema_name = schemas[0]

    console.print(f"\n[dim]Schema selected:[/dim] [cyan]{schema_name}[/cyan]")
    console.print("[dim]Sample queries:[/dim]")
    for q, _ in SCHEMAS[schema_name]["sample_queries"]:
        console.print(f"  • {q}")

    console.print("\n[dim](type 'exit' to quit, 'batch' to run all samples)[/dim]\n")

    output_dir = os.getenv("OUTPUT_DIR", "./outputs")
    os.makedirs(output_dir, exist_ok=True)

    while True:
        question = console.input("[bold]Question:[/bold] ").strip()
        if not question:
            continue
        if question.lower() == "exit":
            break
        if question.lower() == "batch":
            run_batch(pipeline, schema_name)
            continue

        result = pipeline.run(question, schema_name)

        # Save output
        fname = f"{output_dir}/result_{datetime.now().strftime('%H%M%S')}.json"
        with open(fname, "w") as f:
            json.dump(result, f, indent=2)
        console.print(f"[dim]Saved to {fname}[/dim]\n")


def run_batch(pipeline: MultiAgentPipeline, schema_name: str):
    console.print(f"\n[bold]Running batch on {schema_name} sample queries...[/bold]\n")
    samples = SCHEMAS[schema_name]["sample_queries"]
    results = []
    approved = 0

    for i, (question, gold_sql) in enumerate(samples):
        console.print(f"[dim][{i+1}/{len(samples)}][/dim] {question}")
        result = pipeline.run(question, schema_name, verbose=False)
        result["gold_sql"] = gold_sql
        verdict = result.get("verdict", "")
        approved += 1 if "APPROVED" in verdict else 0
        color = "green" if "APPROVED" in verdict else "yellow"
        console.print(f"  SQL: [cyan]{result['final_sql']}[/cyan]")
        console.print(f"  Verdict: [{color}]{verdict}[/{color}]  Score: {result['score']}  Time: {result['elapsed']}s")
        console.print()
        results.append(result)

    console.print(Rule())
    console.print(f"[bold]Batch Results:[/bold] {approved}/{len(samples)} queries APPROVED")

    output_dir = os.getenv("OUTPUT_DIR", "./outputs")
    os.makedirs(output_dir, exist_ok=True)
    fname = f"{output_dir}/batch_{schema_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(fname, "w") as f:
        json.dump(results, f, indent=2)
    console.print(f"[dim]Batch saved to {fname}[/dim]\n")


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Text-to-SQL (Spider Benchmark)")
    parser.add_argument("--schema", type=str, help="Schema name", choices=list_schemas())
    parser.add_argument("--query", type=str, help="Natural language query")
    parser.add_argument("--batch", action="store_true", help="Run all sample queries for schema")
    args = parser.parse_args()

    try:
        pipeline = MultiAgentPipeline()
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        return

    if args.query and args.schema:
        pipeline.run(args.query, args.schema)
    elif args.batch and args.schema:
        run_batch(pipeline, args.schema)
    elif args.batch:
        # Run batch on all schemas
        for schema in list_schemas():
            run_batch(pipeline, schema)
    else:
        interactive_mode(pipeline)


if __name__ == "__main__":
    main()
