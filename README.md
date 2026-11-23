<img src="assets/icon.svg" width="64" height="64" alt="">

# english-hub

App local para treinar **inglês falado**. Você conversa por voz com um "gringo" e recebe feedback focado em
**ser entendido e se comunicar com clareza**, não em sotaque nativo. Dois focos, escolhidos na introdução ou
em Configurações:

- **Trabalho como desenvolvedor:** entrevistas para vagas internacionais reais, daily, bugs, incidentes, code
  review, explicar para não-técnico, com a sua stack.
- **Dia a dia:** conhecer alguém, aeroporto e imigração, hotel, restaurante, médico, farmácia, compras e trocas,
  atendimento por telefone, problema no apartamento, combinar um programa com amigos.

Tudo roda no seu PC. A única coisa "na nuvem" é a IA da conversa, pela CLI de um plano que você já tem:
**Claude** (Claude Code), **Gemini** (Antigravity CLI) ou **ChatGPT** (Codex CLI). Sem chave de API e sem
cobrança extra, mas conta nos limites do seu plano.

## Como usar

Pré-requisito: [uv](https://docs.astral.sh/uv/). A CLI de IA o próprio app instala e conecta.

| | Instalar o uv | Iniciar |
|---|---|---|
| **Windows** (x64) | `winget install astral-sh.uv` | dois cliques em `start.bat` |
| **macOS** (Apple Silicon) | `mise use -g uv@latest` (ou `brew install uv`) | dois cliques em `start.command` (ou `./start.command` no Terminal) |

1. Inicie pelo arquivo do seu sistema. Na primeira vez ele instala as dependências pelo terminal e
   depois abre o navegador em http://127.0.0.1:8765 sozinho (Chrome, Edge ou Safari).
   No Mac, se o Finder bloquear o arquivo, clique com o botão direito > **Abrir** uma vez.
2. **Configuração inicial:** a tela mostra a GPU, a CPU e a memória detectadas e sugere a qualidade do
   reconhecimento (Leve, Recomendada, Máxima). Em **Avançado** dá para trocar o modelo do Whisper, o dispositivo,
   a precisão, a reserva para CPU e as threads. Clique em **Baixar e preparar**: os modelos (~1 a 3 GB)
   baixam com progresso real e o ouvido é carregado na GPU.
3. **Conectar a IA:** para Claude, Gemini (Antigravity) e ChatGPT (Codex), o app mostra se a CLI está
   instalada, instala com o instalador oficial, abre um terminal para você **entrar na conta** (o login é no
   navegador) e **testa** com uma chamada real. Depois você escolhe quem faz cada parte: conversa, feedback e
   ajudas (ex.: conversa no Claude, que é o mais rápido ao vivo, e feedback no ChatGPT).
4. **Introdução (pode pular):** teste do microfone e do fone, voz e legendas, foco e perfil, e uma primeira
   ligação curta. Para refazer: **Configurações › Refazer a introdução**.
5. Escolha um cenário, fale clicando no microfone ou **segurando Espaço**.
6. Clique em **Encerrar e ver feedback** e depois faça o **re-tell**.

Tema claro, escuro ou do sistema, foco, IA e todas as opções da configuração inicial ficam em **Configurações**
(ícone no canto superior direito). As escolhas são salvas em `data/settings.json`.

**Desinstalar:** em **Configurações › Desinstalar** você escolhe o que remover: cada modelo, seus dados,
as configurações, o ambiente Python do app, e (desmarcadas por padrão, porque outros programas usam) cada CLI
de IA e o login dela. "Tudo do english-hub" remove o que é do app e fecha; depois é só apagar a pasta.

### Sobre as CLIs de IA

| | CLI | Conta | Observação |
|---|---|---|---|
| Claude | Claude Code (`claude`) | Pro ou Max | Mais rápido na conversa ao vivo (1 a 3 s por fala). |
| Gemini | Antigravity CLI (`agy`) | Plano Google AI | Substituiu a Gemini CLI, desligada para contas pessoais em junho de 2026. Cerca de 10 s por fala. |
| ChatGPT | Codex CLI (`codex`) | Plus, Pro ou Business | No Mac/Linux instala via Homebrew ou npm (precisa de Node.js). |

O status de login das CLIs nem sempre é confiável (um token expirado ainda aparece como "logado"), por isso o
app sempre confirma com um teste real.

### Notebooks com GPU de entrada (ex.: Acer Nitro 5, GTX 1650 4 GB, i5-11400H)

Funciona sem configuração extra:

- O app lê a VRAM pelo `nvidia-smi`. Em GPUs com até 6 GB, carrega o Whisper `large-v3-turbo` em
  `int8_float16` (~1 GB de VRAM, precisão praticamente igual ao `float16`). Se a GPU falhar ao carregar
  ou ficar sem memória no meio da conversa, ele passa sozinho para a CPU (modelo `small`).
- Na CPU, o Whisper usa um thread por núcleo físico (6 no i5-11400H) e deixa o resto para a voz e o navegador.
- Requisito: **driver NVIDIA 528 ou mais novo** (CUDA 12). Atualize pelo GeForce Experience/NVIDIA App
  se o log mostrar `Whisper on cuda ... failed`.
- Use o notebook **na tomada**: na bateria a GPU fica limitada e a transcrição fica mais lenta.
- Para conferir o que foi carregado, passe o mouse sobre "pronto para falar" no topo ou veja o log: `Whisper ready on cuda (int8_float16)`.

## Tipos de cenário

- **🎯 Entrevista para vaga real:** busque vagas abertas na web (pela IA escolhida para o feedback) ou cole a descrição/link de uma.
  Escolha a etapa (triagem, técnica, comportamental). O entrevistador lê **Meu perfil**, tem expectativas
  com base nos requisitos da vaga e investiga seus gaps. O feedback mostra o que você demonstrou de cada
  requisito e **como o entrevistador te veria**.
Foco **Trabalho como desenvolvedor**:

- **💼 Situações de trabalho:** relatar bug, bloqueio, atraso/prazo, incidente em produção, discordar em
  code review, esclarecer requisito, explicar para não-técnico. Cada uma gera um contexto **fictício com a sua
  stack** e um briefing em português com todos os fatos. Você precisa comunicar em inglês, e o feedback avalia
  se você atingiu os objetivos da conversa. Há a opção de interlocutor tranquilo ou sob pressão.
- **🎙️ Clássicos:** triagem, técnica, comportamental, daily e conversa livre, genéricos.

Foco **Dia a dia**:

- **🗺️ Situações do dia a dia:** pedido errado, trocar ou devolver uma compra, ligar para o atendimento, pedir
  informação na rua, farmácia, problema no apartamento, combinar um programa. Mesma mecânica: briefing em
  português com os fatos, interlocutor tranquilo ou com pressa, feedback pelos objetivos.
- **🎙️ Clássicos:** conhecer alguém, conversa livre, aeroporto e imigração, check-in no hotel, restaurante e
  consulta médica.
- **📦 Pacotes de vocabulário próprios:** viagem, restaurante, saúde, compras e serviços, small talk, phrasal
  verbs e falsos cognatos do dia a dia.

Cenários gerados ficam salvos em **Meus cenários** para repetir.

## Minhas frases (treino de vocabulário falado)

- Salve com ⭐ expressões do feedback, correções, vocabulário do briefing, opções do "Como se diz?" e trechos
  das falas do gringo, ou digite manualmente: a IA corrige a forma (ex.: `catch-up-on-work` → *catch up on work*),
  explica em português e cria um exemplo.
- **Treinar:** você vê o significado e tenta **dizer** a frase; depois **cria uma frase sua** usando-a e recebe
  correção. Repetição espaçada (acertou: volta em 1, 2, 4, 8, 16, 32 dias; errou: volta na próxima revisão).
- As frases em treino entram nas conversas: o interlocutor cria chances de você usá-las, e o feedback conta
  quando você usou certo.
- **📦 Pacotes de vocabulário:** daily, bugs/incidentes, code review, entrevista, phrasal verbs, falsos cognatos,
  ganhar tempo/reformular, reuniões, ou **preparação para um cenário salvo** (vaga ou situação). A IA gera 10
  itens com a sua stack e sem repetir o que você já tem; você escolhe quais entram no treino.

## Texto do gringo (treino de escuta)

- **🎧 Real:** só áudio, sem texto nem replay, como numa call. Não entendeu? Peça "Sorry, could you say that
  again?" e o interlocutor repete mais devagar ou reformula.
- **👁 Revelar ao clicar** (padrão): textos revelados e replays contam como "ajudas de escuta" no relatório.
- **📄 Sempre visível.** Dá para trocar o modo no meio da conversa.

## O método

| Etapa | O que acontece | Por quê |
|---|---|---|
| Conversa | O interlocutor **não interrompe** para corrigir; só repete a forma certa naturalmente (*recast*). | Correção explícita no meio da fala piora a fluência; recasts ajudam. |
| Feedback | Só os **5 erros de maior impacto** no entendimento, expressões úteis, pronúncia **apenas se atrapalhou**. | Pouco e relevante é o que fica. |
| Re-tell 4/3/2 | Mesma resposta 3x com menos tempo (2 min → 1:30 → 1 min), com dicas após a 1ª rodada. | Nation (1989); Tran & Saito (2021): melhora fluência e, com feedback, precisão. |
| Caderno de erros | Erros recorrentes entram na próxima conversa; após 3 acertos, viram "resolvidos". | Repetição espaçada do que *você* erra. |

**Ferramentas extras:** botão **🇧🇷 Como se diz?** (fale em português, recebe 2 formas em inglês),
opção de esconder o texto do gringo (treino de escuta) e velocidade da voz ajustável.

**Métricas por fala:** palavras/min, pausas longas, hesitações (um/uh) e palavras que o
reconhecedor entendeu com baixa confiança (sublinhadas). Isso indica clareza, não sotaque.

## Peças (todas locais e gratuitas)

- **Ouvido:** [faster-whisper](https://github.com/SYSTRAN/faster-whisper) `large-v3-turbo` na GPU (CUDA no Windows,
  Apple Metal/MPS no Mac), com fallback para CPU (modelo `small`).
- **Voz neutra:** [Kokoro](https://github.com/thewh1teagle/kokoro-onnx) (ONNX, CPU): 21 vozes americanas e
  britânicas, cada uma um personagem fixo (`CHARACTERS` em `app/prompts.py`). Rápida, mas sempre no mesmo tom.
- **Voz com emoção (opcional):** [Orpheus 3B](https://github.com/canopyai/Orpheus-TTS) em GGUF via llama.cpp. Ri,
  suspira e muda a entonação; a IA da conversa marca os sons (`<laugh>`, `<sigh>`...) e as legendas saem sem eles.
  Instala pelas Configurações → Voz dos personagens, num ambiente Python próprio (`models/engines/orpheus`), e só
  fica liberada em Mac com Apple Silicon e 16 GB ou mais, ou em placa NVIDIA com 6 GB ou mais (no Windows). Na GTX 1650
  (4 GB) fica desativada: a VRAM já é do reconhecimento de voz. Tem 8 vozes, então personagens dividem voz.
  A fala é transmitida enquanto é gerada (`/api/tts/stream`): numa GPU que gera mais rápido que o tempo real
  (ex.: RTX 3060 Ti) ela começa em cerca de 1 s; num M4 com 16 GB (gera em ~2,3× a duração) o app espera um buffer
  para não engasgar. Interromper o personagem cancela o resto na hora. Entre 0,90× e 1,10× a fala sai na velocidade
  natural; fora disso, ela só começa com a frase pronta. Se o llama.cpp não usar a GPU, o cartão avisa.
  Se o Orpheus falhar, a fala volta para a Kokoro sozinha.
- **Cérebro:** a CLI do seu plano. Claude em modo streaming (Haiku na conversa, Sonnet no feedback); Antigravity
  (`agy -p`) e Codex (`codex exec`) reenviam a conversa a cada fala.
- **Dados:** SQLite em `data/` (fica fora do git).

## Configuração por variáveis de ambiente

Valem como padrão; o que você escolhe na tela de configuração tem prioridade.

| Variável | Padrão | |
|---|---|---|
| `TRACK` | `dev` | foco: `dev` ou `daily` |
| `CHAT_PROVIDER` / `FEEDBACK_PROVIDER` / `HELPER_PROVIDER` | `claude` | `claude`, `gemini` ou `codex` |
| `CHAT_MODEL` | `haiku` | modelo da conversa (vazio = padrão do plano) |
| `FEEDBACK_MODEL` | `sonnet` | modelo do relatório |
| `WHISPER_MODEL` | `large-v3-turbo` | modelo de reconhecimento |
| `WHISPER_DEVICE` | `auto` | `cuda` (Windows), `mps` (Mac), `cpu` ou `auto` |
| `WHISPER_COMPUTE` | `auto` | `float16`, `int8_float16`, `int8` (auto: `int8_float16` em GPUs ≤ 6 GB) |
| `WHISPER_CPU_THREADS` | núcleos físicos | threads do Whisper na CPU |
| `TTS_ENGINE` | `kokoro` | `kokoro` (neutra) ou `orpheus` (com emoção, se instalado e suportado) |
| `ENGLISH_HUB_ORPHEUS_FORCE` | – | `1` libera o Orpheus mesmo fora dos requisitos (por sua conta) |
| `PORT` | `8765` | porta do servidor |
| `ENGLISH_HUB_NO_BROWSER` | – | `1` para não abrir o navegador ao iniciar |
| `ENGLISH_HUB_DATA` / `ENGLISH_HUB_MODELS` | `data/`, `models/` | pastas de dados e modelos (os nomes antigos `DEV_ENGLISH_*` ainda valem) |

## Desenvolvimento

```
uv sync
uv run python -m app.main      # abre a configuração inicial no navegador
# alternativa só pelo terminal: uv run python scripts/download_models.py
```

Código: `app/main.py` (API), `app/prompts.py` (personas, os dois focos e o método), `app/llm.py` (chamadas às
CLIs de IA), `app/providers.py` (instalar, entrar, testar e remover as CLIs), `app/uninstall.py` (desinstalação),
`app/setup.py` (hardware, downloads e configuração inicial), `app/config.py` (configurações salvas),
`app/stt.py`, `app/tts.py`, `app/metrics.py`, `app/db.py`, `app/static/` (interface).

## Próximos passos

- Análise de pronúncia por fonema (wav2vec2) **só** nas palavras que não foram entendidas.
- Modo shadowing para pares que confundem (ship/sheep, full/fool).
- Gráfico de evolução no histórico.
