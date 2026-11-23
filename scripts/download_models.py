"""Downloads the local models once (~2 GB total). Safe to run again; it skips what exists."""
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import config  # noqa: E402

KOKORO_BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"


def fetch(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"ok   {dest.name}")
        return
    print(f"get  {dest.name} ...")
    tmp = dest.with_suffix(dest.suffix + ".part")

    def hook(blocks, bs, total):
        if total > 0:
            print(f"\r     {min(100, blocks * bs * 100 // total)}%", end="", flush=True)

    urllib.request.urlretrieve(url, tmp, hook)
    tmp.replace(dest)
    print()


def main() -> None:
    fetch(KOKORO_BASE + "kokoro-v1.0.onnx", config.KOKORO_MODEL)
    fetch(KOKORO_BASE + "voices-v1.0.bin", config.KOKORO_VOICES)

    print(f"Whisper '{config.WHISPER_MODEL}' (download + GPU test: CUDA or Apple MPS)...")
    from app.stt import stt
    stt.load()
    print(f"ok   whisper {stt.model_name} on {stt.device} ({stt.compute})")
    print("All models ready.")


if __name__ == "__main__":
    main()
