# Image Upscaler by Jair Lima

Aplicativo desktop para Windows que amplia imagens com melhoria real de qualidade por IA, e não só redimensionamento. Usa o motor **upscayl-bin** (NCNN, Vulkan), que roda em placas de vídeo comuns.

## Recursos

- Arrastar e soltar de arquivos, pastas e imagens da web.
- Quatro modelos 4×: Ultra Sharp (máximo detalhe), Remacri (uso geral), Upscayl Standard e Upscayl Lite (rápido).
- Controle deslizante de antes e depois, processamento em lote e cancelamento.

## Instalação

```bat
setup.bat
python upscaler_gui.py
```

O `setup.bat` instala as dependências Python e **baixa o motor e os modelos** dos repositórios oficiais do Upscayl (cerca de 130 MB). Eles não ficam neste repositório.

Para gerar um executável: `python make_icon.py` e depois `build.bat`.

## Licenças de terceiros

O código deste repositório é MIT. O motor e os modelos baixados pelo `setup.bat` têm licenças próprias, definidas pelos autores originais (Upscayl e os criadores de cada modelo). Alguns modelos podem proibir uso comercial. Confira as licenças em [github.com/upscayl](https://github.com/upscayl) antes de redistribuir ou usar comercialmente.

## Licença

MIT, veja [LICENSE](LICENSE).
