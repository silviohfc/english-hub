<img src="assets/icon.svg" width="64" height="64" alt="">

# dev-english

App local para treinar **inglês falado** para vagas internacionais de dev. Você conversa por voz
com um "gringo" (recruiter, engenheiro, hiring manager, colega de time) e recebe feedback focado em
**ser entendido e se comunicar com clareza**, não em sotaque nativo.

Tudo roda no seu PC. A única coisa "na nuvem" é o Claude, usado através do **Claude Code CLI** com a
sua assinatura (sem API key, sem cobrança extra, mas conta nos limites do seu plano).

## Como usar

1. Dê dois cliques em `start.bat` (na primeira vez ele baixa ~2 GB de modelos).
2. O navegador abre em http://127.0.0.1:8765 (use Chrome ou Edge e permita o microfone).
3. Escolha um cenário, fale clicando no 🎤 ou **segurando Espaço**.
4. Clique em **Encerrar e ver feedback** e depois faça o **re-tell**.

## Tipos de cenário

- **🎯 Entrevista para vaga real:** busque vagas abertas na web (via Claude CLI) ou cole a descrição/link de uma.
  Escolha a etapa (triagem, técnica, comportamental). O entrevistador lê **Meu perfil**, tem expectativas
  com base nos requisitos da vaga e investiga seus gaps. O feedback mostra o que você demonstrou de cada
  requisito e **como o entrevistador te veria**.
- **💼 Situações de trabalho:** relatar bug, bloqueio, atraso/prazo, incidente em produção, discordar em
  code review, esclarecer requisito, explicar para não-técnico. Cada uma gera um contexto **fictício com a sua
  stack** e um briefing em português com todos os fatos. Você precisa comunicar em inglês, e o feedback avalia
  se você atingiu os objetivos da conversa. Há a opção de interlocutor tranquilo ou sob pressão.
- **🎙️ Clássicos:** triagem, técnica, comportamental, daily e conversa livre, genéricos.

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

- **Ouvido:** [faster-whisper](https://github.com/SYSTRAN/faster-whisper) `large-v3-turbo` na GPU (CUDA), com fallback para CPU.
- **Voz:** [Kokoro](https://github.com/thewh1teagle/kokoro-onnx) (ONNX, CPU), vozes americanas e britânica.
- **Cérebro:** `claude -p` em modo streaming (Haiku na conversa, Sonnet no feedback).
- **Dados:** SQLite em `data/` (fica fora do git).

## Configuração (variáveis de ambiente)

| Variável | Padrão | |
|---|---|---|
| `CHAT_MODEL` | `haiku` | modelo da conversa |
| `FEEDBACK_MODEL` | `sonnet` | modelo do relatório |
| `WHISPER_MODEL` | `large-v3-turbo` | modelo de reconhecimento |
| `WHISPER_DEVICE` | `auto` | `cuda`, `cpu` ou `auto` |
| `PORT` | `8765` | porta do servidor |

## Desenvolvimento

```
uv sync
uv run python scripts/download_models.py
uv run python -m app.main
```

Código: `app/main.py` (API), `app/prompts.py` (personas e método), `app/llm.py` (Claude CLI),
`app/stt.py`, `app/tts.py`, `app/metrics.py`, `app/db.py`, `app/static/` (interface).

## Próximos passos

- Análise de pronúncia por fonema (wav2vec2) **só** nas palavras que não foram entendidas.
- Modo shadowing para pares que confundem (ship/sheep, full/fool).
- Gráfico de evolução no histórico.
