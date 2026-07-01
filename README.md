# GovGap

A proof-of-concept AI agent that reads a governance document, an open-source project's AI contribution policy or a vendor's AI coding-tool terms, and reports, risk by risk, whether the document manages it, gestures at it, or ignores it. Give it a URL or a file and it returns structured a report.

Validated as an independent second coder against a hand-coded reference set (Cohen's kappa 0.70, substantial agreement).


> Built on Azure AI Foundry with the Microsoft Agent Framework.

## What it does

Give it one document, a URL, a PDF, a DOCX, a txt or markdown file,  the agent then:

1. Reads it and normalises it to clean text,
2. Checks whether it is in scope, an AI-governance document at the developer or team level, and turns away anything that is not, with a reason,
3. Scores it against six developer-level risk categories on a four-level coverage scale,
4. Returns a readable report: per risk, a coverage code, a supporting quote, a one-line rationale, and a fix where coverage is incomplete.

It is an agent, not a single prompt. It routes each document through two gates, scope and then prohibition, and decides the path from what it reads.

## The six risks

The agent scores against six risks that the research literature has shown AI coding agents create for the people and projects that absorb their output. The framework targets the costs that surface downstream, in the code, the review burden, and the people.

- **C1** Code quality and technical debt
- **C2** Human oversight and verification
- **C3** Over-reliance and skill erosion
- **C4** Expert burden and redistribution
- **C5** Accountability and provenance
- **C6** Security and vulnerability

## How a risk is scored

| Code | Meaning |
|------|---------|
| Addressed-M | A working mechanism manages the risk while still permitting AI use |
| Addressed-P | The risk is foreclosed because the document bans AI contribution outright |
| Partial | The risk is mentioned, but the response is vague or non-binding |
| Gap | The document is silent on the risk |

## How it works

```
  one document (URL / PDF / DOCX / TXT / MD)
              |
              v
      ingest  (normalise any format to clean text, in code)
              |
              v
   eligibility gate  (in scope for the framework?)
        |                         |
   out of scope               in scope
        |                         |
   reasoned rejection      foreclosure gate (does it ban AI?)
                               |              |
                            banned         permitted
                               |              |
                          all Addressed-P   score each of the six risks
                                              |
                                              v
                                   schema-validated report
                                              |
                                              v
                                   readable coverage report
```

Notes worth knowing:

- Ingestion is deterministic code, not an LLM tool. Format handling and its failure messages (scanned PDFs, JavaScript-only pages, unsupported types) live in `src/ingest.py`.
- The scope gate judges on binding substance, not the title: a document is in scope if its body carries at least one binding rule governing AI-assisted contribution, even inside an otherwise general policy. It turns away market-level frameworks and non-binding advisory guidance with a reason.
- Prohibition is treated as a whole-document property: one flag, applied uniformly, so a ban is never re-decided risk by risk.
- Model output is parsed with `json-repair` and validated with Pydantic, so a small formatting slip does not fail a run.

## Running it

Prerequisites: an Azure subscription with a model deployed in a Foundry project, Python 3.12+, and the Azure CLI.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
az login
```

Create `.env` in the project root:

```
FOUNDRY_PROJECT_ENDPOINT=https://<your-project>.services.ai.azure.com
FOUNDRY_MODEL=<your-deployment-name>
```

Then point it at a document:

```bash
python -m src.cli   # prints help and accepted formats
python -m src.cli examples/example-ai-contribution-policy.md
python -m src.cli https://example.com/ai-policy
python -m src.cli ./vendor-terms.pdf
python -m src.cli ./policy.pdf --json   # readable report plus JSON
```

The repository runs from a clean clone: the code, the prompts in `prompts/`, and the bundled example are all that is needed beyond Azure credentials.

## Limitations

- A proof of concept, not a production auditing service.
- It assesses documents, not codebases: what a policy governs, not whether any code is safe, and only the text, not how the policy is enforced.
- The framework was built around open-source AI contribution policies and vendor AI coding-tool terms, in English; the agent is most reliable on those and less certain on other document types.

## Repository layout

```
src/
  cli.py          command-line entry point
  ingest.py       multi-format document loading
  eligibility.py  scope gate
  agent.py        the coder (runs the foreclosure check and risk coding)
  report.py       human-readable rendering
  schema.py       data models
  codebook.py     loads the coding prompt
  tools.py        document fetch helper

prompts/
  codebook_prompt.md     risk coding scheme (agent's instructions)
  eligibility_prompt.md   the scope-gate criteria

examples/         a runnable sample document
```

## Acknowledgements

The six-risk framework is from my MSc dissertation, which is deriven from the empirical literature on the risks of AI-assisted development.
This project implements the said framework as a working tool. 

This is a public demonstration of the agent. The underlying framework's full derivation, the evaluation data, and the dissertation findings are held separately and will be published after the dissertation is submitted to avoid self-plagiarism risks.
