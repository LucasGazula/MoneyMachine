# MoneyMachine

Estúdio de criação de vídeos curtos com roteiro, mídia, narração, legendas e música. A interface Svelte/TypeScript é servida pelo FastAPI; a API e a CLI também estão disponíveis.

[English](README-en.md) · [Guia do estúdio](docs/studio.md) · [Issues](https://github.com/LucasGazula/MoneyMachine/issues)

## Instalação

Requer Python 3.11+, uv, FFmpeg e Node 22.12+ para compilar a interface.

```sh
git clone https://github.com/LucasGazula/MoneyMachine.git
cd MoneyMachine
cp config.example.toml config.toml
uv sync --frozen --no-dev
cd frontend
npm ci
npm run build
cd ..
sh webui.sh
```

Abra http://127.0.0.1:8501 e configure os provedores em **Configurações**. No Windows, copie o arquivo de configuração e use `webui.bat`. As chaves ficam no `config.toml` local, ignorado pelo Git.

Para transcrição local, instale o extra Whisper: `uv sync --frozen --no-dev --extra whisper`. Consulte o [guia do estúdio](docs/studio.md) para outros runtimes e opções.

## Docker

Com `config.toml` criado:

```sh
docker compose up --build webui
```

Esse comando compila o MoneyMachine a partir deste repositório. `docker-compose.release.yml` usa `ghcr.io/lucasgazula/moneymachine:latest` quando a imagem própria estiver publicada; não usa imagens do projeto original.

## O que mudou

- Estúdio Svelte com configurações por função e histórico de geração.
- Voz e transcrição Gemini, além de música Google Lyria.
- Renderização otimizada com FFmpeg e fallback MoviePy.
- Cancelamento da geração com preservação dos arquivos concluídos.
- Prévia que carrega o vídeo após a conclusão da renderização.

## Desenvolvimento

```sh
cd frontend
npm run check
npm run build
cd ..
uv run --no-sync pytest -q test/services
```

Veja [docs/studio.md](docs/studio.md) e [docs/frontend-migration.md](docs/frontend-migration.md) para arquitetura e validações.

## Origem e licença

MoneyMachine é mantido por [LucasGazula](https://github.com/LucasGazula) como projeto independente. Originou-se do [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo), de Harry, e não acompanha mais suas atualizações. O histórico Git e os créditos originais foram preservados. Licença [MIT](LICENSE).
