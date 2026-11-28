# Pulse Monitor

Service health, latency history and incident investigation. The hosted checks use controlled sample responses rather than real external uptime measurements and require the page to remain active.

[Live demo](https://portfolio-suite-jv.vercel.app/pulse) · [Portfolio](https://jv-software-portfolio.vercel.app/)

**Owner and maintainer:** João Victor da Silva ([JustJao1](https://github.com/JustJao1)).

## Architecture

HTML, CSS and JavaScript frontend with Python domain operations and temporary SQLite storage. Each browser stores its own snapshot; the hosted API reconstructs temporary state for each operation. The public demo is not a production multi-user service.

## Local setup

Python 3.11+. Create and activate a virtual environment, then run:

```sh
python -m pip install -r requirements.txt
python run.py
```

Open http://127.0.0.1:8765/. The local runner is bound to loopback. Use `python -m unittest discover -s tests -v` for the included tests. The GitHub Actions workflow checks compilation and core behavior. Browser and external integration tests are separate.

[Ownership](OWNERSHIP.md) · [Third-party notices](THIRD_PARTY_NOTICES.md)


## Engineering evidence / Evidências de engenharia

[Architecture, decisions and bilingual walkthrough / Arquitetura, decisões e demonstração bilíngue](docs/engineering-quality.md).

Measured snapshot / Registro de 28/11/2026:

PT: 2 testes aprovados; 50% de cobertura (linhas e ramificações no escopo instrumentado); contêiner e health check aprovados.

EN: 2 tests passed; 50% branch-inclusive coverage in the instrumented scope; container and health check passed.

[Actual GitHub Actions run / Execução real de CI](https://github.com/JustJao1/pulse-monitor/actions/runs/46110648409).

[Portfolio evidence / Evidências no portfólio](https://justjao1.vercel.app/#engineering).
