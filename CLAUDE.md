# CLAUDE.md — asi-main

Instruções para qualquer sessão Claude Code (local ou nuvem) que trabalhe neste
repo. O operador (Matheus) é médico, não-programador: explique termos técnicos
em linguagem simples na primeira ocorrência, mantendo precisão.

> **O que é isto, em uma frase:** a **linha-mestra local do framework
> ASI-Evolve** (GAIR-NLP) — um "pesquisador de IA automático" que roda um ciclo
> APRENDER → PROJETAR → EXPERIMENTAR → ANALISAR: um LLM (modelo de linguagem)
> propõe versões novas de um programa, um script de avaliação dá nota a cada
> versão, e o sistema aprende com cada tentativa até achar algo melhor.
> Este repo é a **base limpa**, sem os experimentos da frota de scanners
> (esses vivem no irmão `asi-evolve` — ver abaixo).

## 🔀 Relação com os 2 repos irmãos (LEIA antes de decidir onde trabalhar)

Há **3 repos ASI-Evolve** na conta (`matheuscllm-lgtm`), todos clonados como
irmãos em `/home/user/` nas sessões de nuvem:

| Repo | O que é | Que trabalho acontece lá |
|---|---|---|
| **`asi-main`** (ESTE) | Linha-mestra: o framework ASI-Evolve upstream (GAIR-NLP) + skill `/auto`. **Sem** experimentos da frota — só o demo genérico `circle_packing_demo`. | Mudanças de **base/framework** (pipeline, database, cognition, utils), demos genéricos, doc. |
| **`asi-evolve`** | Quase idêntico a este, **mais**: 4 experimentos da frota de scanners Pokémon (`cardtrader_vintage`, `comc_tiers`, `liga_match`, `myp_match`), o `HANDOFF-self-evolving-integration.md` (estado da integração com os scanners — leia-o LÁ antes de mexer nesses experimentos), e 3 diffs de código (detalhados abaixo). | **Todo trabalho de integração com a frota de scanners** — experimentos novos da frota, runs ao vivo, portes de descoberta para os repos dos scanners. |
| **`github.com-GAIR-NLP-ASI-Evolve`** | Port/reimplementação **menor e independente**: pacote `asi_core/` (engine do loop sem dependências, ~sem FAISS/sentence-transformers), exemplo `circle_packing` próprio e `docs/PORTING.md` (como adotar o loop no projeto de oncologia e nos scanners). Não compartilha código com os outros dois. | Trabalho no **engine reutilizável leve** (`asi_core`) e nos guias de porte. |

**Diferenças de código verificadas entre `asi-main` e `asi-evolve`** (diff real
dos arquivos — se você mexer nesses pontos aqui, saiba que o irmão diverge):

- `utils/llm.py`: o `asi-evolve` adiciona `_resolve_env()` — expande `${VAR}`/
  `$VAR` em `api_key`/`base_url` a partir do ambiente e **erra alto** se a
  variável não existir. Aqui no `asi-main`, a expansão de `${VAR}` acontece só
  no `utils/config.py` (ver "Configuração") e variável ausente vira string
  vazia silenciosa.
- `pipeline/engineer/engineer.py`: o `asi-evolve` lê a env var
  `ASI_EVOLVE_BASH` para apontar um bash real no Windows (o `bash` "pelado" lá
  cai no WSL e quebra). Aqui o Engineer chama `bash` fixo.
- `.gitignore`: o `asi-evolve` ignora os artefatos de run dos experimentos
  (`experiments/*/steps/`, `database_data/`, `cognition_data/`, `results.json`,
  `eval.log`, `wandb/` etc.). **Aqui NÃO** — ver o aviso em "Fluxo de
  desenvolvimento".

## Como rodar

**Setup (1ª vez em qualquer ambiente):**

```bash
pip install -r requirements.txt
```

Dependências (`requirements.txt`): `openai>=1.0.0` (cliente da API de LLM),
`pyyaml`, `jinja2` (templates de prompt), `numpy`, `faiss-cpu` (índice de busca
vetorial — "biblioteca que acha textos parecidos rapidamente"),
`sentence-transformers` (gera os embeddings — representações numéricas de
texto; o modelo `all-MiniLM-L6-v2` é baixado do HuggingFace no 1º uso) e
`wandb` (rastreamento de experimentos Weights & Biases, opcional). README pede
**Python 3.10+** e `bash`/`python3` no PATH.

**Rodar o demo incluído (circle packing — empacotar 26 círculos num quadrado):**

```bash
# 1) Semear o cognition store (a "memória de conhecimento prévio") do demo:
python experiments/circle_packing_demo/init_cognition.py

# 2) Rodar 10 passos de evolução:
python main.py \
  --experiment circle_packing_demo \
  --steps 10 \
  --sample-n 3 \
  --eval-script /caminho/ABSOLUTO/para/experiments/circle_packing_demo/eval.sh
```

⚠️ **`--eval-script` tem que ser caminho ABSOLUTO** (o Engineer executa o
script a partir de diretórios de trabalho por passo — `experiments/<exp>/steps/
step_N/` — então caminho relativo quebra a resolução; sem eval-script válido
tudo pontua 0.0). Aviso está no README do próprio demo.

**Flags do `main.py` (verificadas no argparse):**

- `--config PATH` — arquivo de config explícito (default: nenhum; usa a cadeia
  de merge abaixo).
- `--experiment NOME` — nome do experimento (resolve
  `experiments/<NOME>/config.yaml`).
- `--steps N` — número de passos de evolução (default **10**).
- `--sample-n N` — quantos nós históricos são amostrados por passo (default **3**).
- `--eval-script PATH` — script de avaliação (o "juiz" que dá nota a cada
  candidato). Sem ele, o passo roda sem avaliação por benchmark.

No fim do run, o `main.py` imprime estatísticas e o melhor nó (nome, score,
motivação). Os artefatos ficam em `experiments/<exp>/`: `steps/step_N/`
(código candidato + `results.json` + `eval.log` de cada rodada),
`database_data/`, `cognition_data/`, `logs/`.

**Pré-requisito de LLM:** o loop chama um endpoint **compatível com a API da
OpenAI** (qualquer um: OpenAI, local via sglang/LiteLLM etc.). Sem um endpoint
acessível e uma key válida configurados (ver "Configuração"), o run falha nas
chamadas de LLM. Chamadas de LLM em volume **custam dinheiro** — no irmão
`asi-evolve`, os 3 runs ao vivo da frota (endpoint OpenAI, gpt-4o) custaram
~US$6; trate runs longos como custo relevante.

## Configuração (`config.yaml`)

**Ordem de merge (verificada em `utils/config.py::load_config`)** — o de baixo
sobrescreve o de cima:

1. `config.yaml` da raiz do repo (defaults);
2. `experiments/<nome>/config.yaml` (override do experimento);
3. arquivo passado em `--config` (override final).

**Blocos do `config.yaml` da raiz:**

- `experiment_name` — nome default do experimento (`"default"`).
- `api` — o LLM que move os agentes: `provider`, `base_url`, `api_key`,
  `model`, `temperature`, `top_p`, `max_tokens`, `seed`, `timeout`,
  `retry_times`, `retry_delay`. Na raiz são **placeholders**
  (`"your_base_url"`, `"your_api_key"`, `"your_model"`) — na prática o config
  do experimento sobrescreve. O demo `circle_packing_demo` aponta para um
  servidor **sglang local** (`http://localhost:30032/v1`, `api_key: "EMPTY"`,
  `model: "default"`) — herdado do upstream; só funciona se você tiver esse
  servidor rodando. Qualquer chave extra dentro de `api` (ex.: `extra_body`) é
  repassada à API como parâmetro adicional (`utils/llm.py`).
- `logging` — nível/console + `wandb` (**`enabled: true` no default da raiz**;
  o demo usa `offline: true`. Sem conta/login do W&B, prefira desabilitar ou
  usar offline).
- `pipeline` — liga/desliga agentes (`manager: false` por default;
  `researcher`/`engineer`/`analyzer: true`); `researcher.diff_based_evolution`
  (true = o Researcher edita o pai via diffs SEARCH/REPLACE; false = reescreve
  o programa inteiro — o demo usa false) + `diff_pattern` +
  `max_code_length`; `max_retries` por agente; `engineer_timeout` (segundos,
  default 1800); `parallel.num_workers` (1 = sequencial/debug; 2–4 =
  produção); `sample_n`; `judge` (juiz LLM opcional, `enabled: false` —
  exige `judge.jinja2` nos prompts do experimento quando ligado).
- `cognition` — o **cognition store** (memória de conhecimento de domínio):
  `storage_dir` (relativo ao diretório do experimento), modelo de embedding
  (`sentence-transformers/all-MiniLM-L6-v2`, dimensão 384), índice FAISS
  (`IP`), `retrieval.top_k`/`score_threshold`, `web_search` (reservado,
  desabilitado).
- `database` — o **experiment database** (memória de todas as tentativas):
  `storage_dir`, `max_size` (null = sem limite; cheio → remove o pior),
  embedding, e `sampling.algorithm` = **`ucb1` / `greedy` / `random` /
  `island`** (island = MAP-Elites com ilhas; parâmetros próprios, incl.
  `feature_dimensions` como `["complexity", "diversity"]` no demo).

**Chaves de API e variáveis de ambiente:**

- **Nunca versionar chave.** O `.gitignore` cobre `*.env`; segredos vivem em
  env vars ou arquivos `.env` locais, nunca em YAML commitado.
- O jeito suportado de referenciar segredo no YAML é placeholder `${VAR}`:
  `utils/config.py::_resolve_env_vars` resolve valores que sejam **exatamente**
  `${NOME_DA_VAR}` lendo `os.environ` (ex.: `api_key: "${OPENAI_API_KEY}"`).
  ⚠️ Neste repo, variável **não setada vira string vazia em silêncio** (o
  irmão `asi-evolve` erra alto nesse caso — diferença documentada acima).
- `utils/llm.py` deste repo **não lê nenhuma env var diretamente** — recebe
  tudo do config já resolvido. Não há nome de env var hardcoded no código
  deste repo.

## Arquitetura

```
main.py                     entrada CLI: bootstrapa o repo como pacote "Evolve" e roda Pipeline.run
config.yaml                 defaults do repo (template; experimento sobrescreve)
__init__.py                 raiz do pacote "Evolve" (por isso imports são Evolve.*)
pipeline/
  main.py                   Pipeline: orquestra os passos (sequencial ou paralelo), nó inicial
                            a partir de initial_program, step dirs, stats, best node
  base.py                   base dos agentes
  researcher/researcher.py  RESEARCHER: lê database+cognition e propõe o próximo candidato
  engineer/engineer.py      ENGINEER: executa o candidato (roda eval.sh via bash, com timeout)
                            e coleta o results.json
  analyzer/analyzer.py      ANALYZER: destila o resultado em lição reutilizável
  manager/manager.py        MANAGER (desligado por default no config)
cognition/cognition.py      Cognition store (embedding + FAISS): conhecimento de domínio injetado
database/
  database.py               experiment database: cada tentativa com motivação/código/resultado/análise
  algorithms/               amostragem de pai: ucb1.py, greedy.py, random.py, island.py (+factory)
  embedding.py, faiss_index.py
utils/
  config.py                 load_config (merge em 3 camadas) + resolução de ${VAR}
  llm.py                    LLMClient: wrapper OpenAI-compatible (retry, json_mode, log por chamada)
  prompt.py                 prompts: usa experiments/<exp>/prompts/ e cai em utils/prompts/ (defaults)
  prompts/                  templates jinja2 default (researcher, researcher_diff, analyzer, manager)
  structures.py, logger.py, diff.py, best_snapshot.py
experiments/
  circle_packing_demo/      demo runnável (ver "Experimentos")
  best/circle_packing/      4 melhores programas salvos de ablations (referência)
skills/evolve/              a "Evolve Agent Skill" distribuível (SKILL.md + scripts/evolve-* +
                            evolve_core/): versão single-agent leve do loop, com estado em
                            .evolve_runs/ — o README recomenda o repo (pipeline oficial) para
                            trabalho sério; a skill é para experimentação rápida
.claude/commands/auto.md    skill /auto (ver seção própria)
assets/                     Overview.png + paper.pdf (paper do ASI-Evolve, arXiv 2603.29640)
```

Detalhe técnico útil: o `main.py` registra a **raiz do repo** como o pacote
Python `Evolve` (bootstrap por caminho), então os scripts de experimento
importam `from Evolve.cognition.cognition import Cognition` — funciona mesmo
com a pasta se chamando `asi-main`.

## Experimentos disponíveis NESTE repo

- **`experiments/circle_packing_demo/`** — o único experimento runnável aqui:
  empacotar 26 círculos num quadrado unitário maximizando a soma dos raios
  (alvo de referência 2.635, do paper do AlphaEvolve). Estrutura canônica de
  qualquer experimento: `input.md` (descrição do problema), `config.yaml`
  (overrides), `initial_program` (baseline), `init_cognition.py` (semeia
  conhecimento), `evaluator.py` + `eval.sh` (avaliação), `prompts/*.jinja2`
  (prompts específicos). Tem `README.md` próprio.
- **`experiments/best/circle_packing/`** — 4 programas de alta pontuação
  salvos de runs de ablation (`code_map79`, `code_map147`, `code_map286`,
  `code_ucb17`). São artefatos de referência, não experimentos.

Os 4 experimentos da **frota de scanners** (`cardtrader_vintage`, `comc_tiers`,
`liga_match`, `myp_match`) **NÃO estão aqui** — vivem no irmão `asi-evolve`,
junto com o HANDOFF que registra o estado deles.

## Testes

**Não há suíte de testes neste repo** — sem diretório `tests/`, sem
`pytest.ini`, sem CI (não existe `.github/workflows/`). Validação de mudança é
manual: rodar o demo (`circle_packing_demo`) ponta a ponta é o smoke test
disponível. Se você adicionar testes, documente aqui o comando.

## Fluxo de desenvolvimento e segurança

- **Branch + PR, nunca push direto na `main`** (padrão da frota do operador; o
  histórico do repo já mistura commits do upstream GAIR-NLP e PRs `(#N)` —
  siga o padrão PR daqui pra frente). Teste real de "já mergeado" após
  squash-merge: `git diff --stat origin/main <branch>` vazio.
- **Segredos nunca versionados** — `*.env` é gitignored; keys via env var /
  placeholder `${VAR}` no YAML (ver "Configuração").
- ⚠️ **Artefatos de run NÃO estão no `.gitignore` deste repo.** O `.gitignore`
  aqui só cobre `__pycache__`, `*.env`, `.evolve_runs/` (estado da skill
  evolve) e `.test_tmp/`. Um run cria `experiments/<exp>/steps/`,
  `database_data/`, `cognition_data/`, `logs/`, `results.json`, `eval.log`,
  `wandb/` — que aparecerão como untracked. **NUNCA commite esses artefatos**
  (o irmão `asi-evolve` já os ignora no `.gitignore` dele; se for rodar muito
  aqui, alinhar o `.gitignore` por PR é melhoria legítima).
- Remote: `github.com/matheuscllm-lgtm/asi-main`. Licença Apache-2.0 do
  upstream preservada em `LICENSE`.

## Skill `/auto` (`.claude/commands/auto.md`)

O repo tem uma skill/command: **`/auto`** — modo autônomo **genérico** da
frota (mesmo contrato sincronizado nos 3 repos ASI-Evolve): executa a tarefa
ponta a ponta (corrige, integra, testa, commita, abre **PR draft**, mergeia só
quando trivialmente seguro) sem pedir confirmação, salvo os riscos altos
listados no próprio arquivo (perda de dados, segredo, custo relevante —
chamadas pagas de LLM em volume contam —, decisão irreversível). Leia o
arquivo antes de operar nesse modo. Nota do próprio contrato para sessões de
nuvem: `gh` CLI não está disponível — operações GitHub via ferramentas
`mcp__github__*`; `git push` via Bash funciona.
