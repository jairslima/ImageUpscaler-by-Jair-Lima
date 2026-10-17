"""Image Upscaler by Jair Lima — engine wrapper para upscayl-bin (ncnn-vulkan)."""

import subprocess
import sys
import threading
from pathlib import Path
from PIL import Image


def _base_path():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def get_binary_path():
    return _base_path() / "bin" / "upscayl-bin.exe"


def get_models_path():
    return _base_path() / "models"


MODELS = {
    "Ultra Sharp 4× (fotos, máx. detalhe)": {"name": "ultrasharp-4x",       "scale": 4},
    "Remacri 4× (fotos, uso geral)":         {"name": "remacri-4x",          "scale": 4},
    "Upscayl Standard 4× (balanceado)":      {"name": "upscayl-standard-4x", "scale": 4},
    "Upscayl Lite 4× (rápido)":              {"name": "upscayl-lite-4x",     "scale": 4},
}


def upscale(input_path, output_path, model_key, output_format="png",
            jpeg_quality=90, tile_size=0, output_scale=4,
            cancel_event: threading.Event | None = None):
    """
    Amplia uma única imagem. Retorna (sucesso: bool, mensagem_erro: str).
    - output_scale: escala de saída (2 ou 4). O modelo sempre roda em 4×
      internamente; com output_scale=2 o resultado é reamostrado para 2×.
    - cancel_event: threading.Event — se disparado, termina o processo.
    """
    binary = get_binary_path()
    models_dir = get_models_path()

    if not binary.exists():
        return False, (
            f"Binário não encontrado: {binary}\n"
            "Execute setup.bat para baixar o engine."
        )

    model_info = MODELS[model_key]
    input_path = Path(input_path)
    output_path = Path(output_path)
    fmt = output_format.lower().replace("jpeg", "jpg")

    if fmt == "jpg":
        intermediate = output_path.with_suffix(".png")
        ncnn_fmt = "png"
    else:
        intermediate = output_path
        ncnn_fmt = fmt

    cmd = [
        str(binary),
        "-i", str(input_path),
        "-o", str(intermediate),
        "-n", model_info["name"],
        "-z", str(model_info["scale"]),
        "-s", str(output_scale),
        "-f", ncnn_fmt,
        "-m", str(models_dir),
        "-t", str(tile_size),
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        while True:
            try:
                proc.wait(timeout=0.5)
                break
            except subprocess.TimeoutExpired:
                if cancel_event and cancel_event.is_set():
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    return False, "Cancelado pelo usuário."

        if proc.returncode != 0:
            err = proc.stderr.read().decode(errors="replace").strip()
            return False, err or f"Processo encerrou com código {proc.returncode}."

        # Converter PNG intermediário para JPEG com qualidade controlada
        if fmt == "jpg" and intermediate != output_path:
            img = Image.open(intermediate).convert("RGB")
            img.save(output_path, "JPEG", quality=jpeg_quality, optimize=True)
            intermediate.unlink(missing_ok=True)

        return True, ""

    except Exception as e:
        return False, str(e)
