# TYPEBOT by Math

Aplicativo de desktop em **Python + Tkinter** que **automatiza a digitação** de textos em qualquer campo editável e que também tem uma **área de treino** para você praticar digitação.

> Baseado no projeto [AUTO-ESCRITOR](https://github.com/VILHALVA/AUTO-ESCRITOR) de [@VILHALVA](https://github.com/VILHALVA).

---

## Índice

- [O que ele faz](#o-que-ele-faz)
- [Novidades em relação ao original](#novidades-em-relação-ao-original)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Como usar](#como-usar)
- [Atalhos de teclado](#atalhos-de-teclado)
- [Botões](#botões)
- [Área de teste](#área-de-teste)
- [Área de treino](#área-de-treino)
- [Como funciona por dentro](#como-funciona-por-dentro)
- [Perguntas e problemas comuns](#perguntas-e-problemas-comuns)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Aviso de uso responsável](#aviso-de-uso-responsável)
- [Créditos](#créditos)

---

## O que ele faz

1. Você cola (ou escreve) um texto na caixa do app.
2. Clica no campo onde o texto deve aparecer (um editor, um formulário, um documento...).
3. Aperta **F8**: o TYPEBOT digita o texto sozinho, caractere por caractere, na velocidade escolhida.
4. Aperta **F9** a qualquer momento para interromper.

Além disso, o app corrige "sujeiras" comuns de texto copiado, tem uma janela para **testar se a digitação saiu 100% igual** e uma **área de treino** com textos em 4 níveis de dificuldade.

## Novidades em relação ao original

| Recurso | Original | TYPEBOT |
|---|---|---|
| Pontuação e acentos | Podiam falhar em teclado ABNT2 | Enviados como Unicode, saem exatamente como no texto |
| Limpeza do texto | Não tinha | Botão **Corrigir texto** e limpeza automática ao iniciar |
| Atalhos globais | Não tinha | **F8** inicia e **F9** para (com o app minimizado também) |
| Parar a digitação | Não tinha | Botão **Parar** e atalho **F9** |
| Barra de progresso e status | Não tinha | Tem |
| Área de teste | Não tinha | Botão **Testar** |
| Área de treino | Não tinha | Botão **Treinar**, com 4 níveis e recorde |
| Interface | Padrão do Tkinter | Tema escuro, botões arredondados |

## Requisitos

- **Python 3.8 ou mais novo** (com Tkinter, que já vem no instalador oficial do Python para Windows e macOS)
- A biblioteca **pynput**
- Windows, macOS ou Linux com ambiente gráfico

> No Linux, o Tkinter pode precisar ser instalado à parte (ex.: `sudo apt install python3-tk`). No macOS, é preciso dar permissão de **Acessibilidade** ao terminal/Python para ele poder controlar o teclado. No Linux com Wayland, o controle global do teclado pode ser limitado; use X11 se tiver problemas.

## Instalação

```bash
git clone https://github.com/cryloopz/typebot.git
cd typebot/CODIGO
pip install -r requirements.txt
python CODIGO.py
```

**No Windows**, também dá para dar dois cliques em **`ABRIR-TYPEBOT.bat`**. Ele instala o `pynput` na primeira vez, se faltar, e abre o app sem a janela preta do terminal.

**Sem a janela preta, sem o `.bat`:** renomeie `CODIGO.py` para `CODIGO.pyw` e dê dois cliques.

**Para gerar um `.exe`:**

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile CODIGO.py
```

O programa aparece em `dist/CODIGO.exe`. Alguns antivírus desconfiam de programas feitos assim que controlam o teclado; se isso acontecer, é preciso liberar o arquivo.

## Como usar

1. **Cole o texto** na caixa grande "TEXTO". O contador mostra quantos caracteres ele tem.
2. Se o texto veio de um site, PDF ou Word, clique em **Corrigir texto** (veja [abaixo](#como-funciona-por-dentro) o que isso faz).
3. Ajuste a **velocidade** (de 0,010 a 0,100 segundo por caractere; quanto menor, mais rápido).
4. Use **uma** destas formas de começar:
   - **Atalho F8 (recomendado):** clique no campo de destino e aperte `F8`. A digitação começa na hora.
   - **Botão INICIAR:** a janela é minimizada e o app espera o tempo do controle **"Iniciar em"** (1 a 10 s) para você clicar no campo de destino.
5. Para interromper: **F9** ou o botão **PARAR**.
6. Ao terminar, a barra chega ao fim e o status mostra **"Concluído!"**.

> Durante a digitação, **não clique nem digite nada**. O robô escreve onde estiver o cursor, então qualquer clique faz o texto ir para outro lugar.

## Atalhos de teclado

| Tecla | Ação |
|---|---|
| **F8** | Inicia a digitação do texto que está no TYPEBOT |
| **F9** | Para a digitação |

Funcionam mesmo com o app minimizado ou em segundo plano. Para trocar as teclas, edite no início do `CODIGO.py`:

```python
ATALHO_INICIAR = "<f8>"
ATALHO_PARAR = "<f9>"
```

## Botões

| Botão | O que faz |
|---|---|
| **▶ INICIAR (F8)** | Minimiza o app e começa a digitar depois do tempo "Iniciar em" |
| **■ PARAR (F9)** | Interrompe a digitação (só fica ativo enquanto digita) |
| **✎ CORRIGIR TEXTO** | Limpa espaços estranhos e caracteres escondidos e mostra o que foi trocado |
| **✔ TESTAR** | Abre a [área de teste](#área-de-teste) |
| **★ TREINAR** | Abre a [área de treino](#área-de-treino) |
| **LIMPAR** | Apaga a caixa de texto |

## Área de teste

Serve para conferir se o robô digita **exatamente** o texto, sem nenhum erro. Ela abre uma janela com:

- o **texto original** (verde onde está certo, vermelho no ponto do erro);
- uma **caixa onde o robô digita**;
- acertos, erros, progresso e tempo;
- se algo divergir, a **posição exata** e os **caracteres esperado e digitado, com nome** (por exemplo, "espaço comum" contra "espaço não separável (U+00A0)").

**Como usar:** cole um texto no TYPEBOT, clique em **TESTAR** e aperte **F8**. O app joga o foco para a caixa de teste sozinho. Com a janela de teste aberta, use o atalho F8 (o botão INICIAR fica bloqueado, porque o clique tiraria o foco da janela de teste). No fim, aparece **"100% igual ao texto. Nenhum erro!"** ou a descrição do problema.

## Área de treino

Aqui **você** digita, para praticar. O colar e o Enter ficam bloqueados.

- **4 níveis**, com 4 textos cada, sorteados a cada vez:
  - **Fácil:** frases curtas e simples.
  - **Médio:** parágrafos com acentos e vírgulas.
  - **Difícil:** aspas, parênteses, dois-pontos, ponto e vírgula, reticências e travessão.
  - **Extremo:** números, R$, %, @, #, datas, URLs e símbolos.
- O tempo começa **na primeira tecla**.
- O texto fica **verde** onde está certo e **vermelho** no erro; corrija com Backspace.
- Mostra ao vivo: **TPM** (toques por minuto), **PPM** (palavras por minuto), **precisão**, **erros** e **tempo**.
- O **recorde** de cada nível (maior TPM com pelo menos 95% de precisão) fica salvo em `typebot_recordes.json`, na pasta do programa.

## Como funciona por dentro

### Por que a pontuação falhava no original

O original usa `pyautogui.write()`, que só envia teclas que existem no **layout de teclado americano**. Em teclados brasileiros (ABNT2), vários sinais e os acentos podem sair errados ou nem sair. O TYPEBOT usa `pynput` e envia cada caractere pelo seu **valor Unicode** (`teclado.type(caractere)`), então o que está no texto é o que sai, independente do layout.

### O que o "Corrigir texto" faz

Quando se copia texto de uma página, vêm junto caracteres que parecem normais mas não são. O TYPEBOT:

- troca **espaços especiais** (espaço não separável, espaço fino etc.) e **tabs** por um espaço comum;
- troca **quebras de linha** por um único espaço (textos de digitação costumam ser uma linha só);
- remove **caracteres invisíveis** (largura zero, hífen suave etc.);
- tira espaços do **começo e do fim**.

Espaços duplos que já estavam no texto **não** são mexidos, e a ortografia **não** é alterada. O botão lista exatamente o que foi encontrado. Ao iniciar com **F8**, a mesma limpeza roda automaticamente, em silêncio.

### Digitação, parada e atalhos

- A digitação roda em uma **thread separada**, para a janela não travar.
- O botão PARAR e o atalho F9 sinalizam a thread por um `threading.Event`, então a parada é imediata.
- Os atalhos globais usam `pynput.keyboard.GlobalHotKeys`, e os eventos voltam para a janela por uma **fila** (`queue.Queue`), a forma segura de mexer no Tkinter a partir de outra thread.

## Perguntas e problemas comuns

**Falta algum caractere ou sobra um espaço no destino.**
Aumente o intervalo (0,030 a 0,050 s costuma ser estável) e use **Corrigir texto** antes. Use também a **área de teste** para ver exatamente onde aparece a diferença.

**O F8 não faz nada.**
Verifique se o TYPEBOT mostra "Pronto • F8 inicia • F9 para" embaixo. Se aparecer "atalhos indisponíveis", use os botões. No macOS, dê permissão de Acessibilidade; no Linux, prefira X11.

**O texto foi digitado no lugar errado.**
O robô escreve onde está o cursor. Clique no campo de destino antes do F8, e não mexa em mais nada durante a digitação.

**O F8 avisa "Clique no campo de destino".**
Você apertou F8 com o cursor dentro da caixa de texto do próprio TYPEBOT. Clique no campo de destino e tente de novo.

**Alguns sites ou programas ignoram a digitação automática.**
Alguns aplicativos tratam teclas simuladas de forma diferente ou as bloqueiam. Isso é comportamento deles, não um erro do TYPEBOT.

## Estrutura do projeto

```
typebot/
├── CODIGO/
│   ├── CODIGO.py            # o aplicativo (interface + lógica)
│   ├── ABRIR-TYPEBOT.bat    # atalho para abrir no Windows com dois cliques
│   └── requirements.txt     # dependências (pynput)
├── .gitignore
├── FOTO.png                 # captura de tela do projeto original
└── README.md
```

`typebot_recordes.json` é criado sozinho ao bater um recorde no treino e não vai para o Git.

## Aviso de uso responsável

Use o TYPEBOT apenas onde a automação de digitação é permitida: tarefas repetitivas, testes de interface, preenchimento de formulários seus, treino pessoal. Muitos sites, provas, concursos e testes de velocidade **proíbem o uso de robôs**, e usá-lo neles pode violar as regras do serviço e invalidar resultados. Você é responsável pelo uso que fizer da ferramenta.

## Créditos

- Projeto original: [VILHALVA/AUTO-ESCRITOR](https://github.com/VILHALVA/AUTO-ESCRITOR), de [@VILHALVA](https://github.com/VILHALVA).
- Modificações e interface: **Math**.
