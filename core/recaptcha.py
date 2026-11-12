"""Adaptation minimale de reCognizer aux libellés reCAPTCHA français."""

import asyncio
import concurrent.futures
import os
import sys
import threading
import unicodedata
from pathlib import Path

import numpy as np


_FRENCH_LABELS = {
    "velos": "bicycle",
    "bicyclettes": "bicycle",
    "bateaux": "boat",
    "ponts": "bridge",
    "autobus": "bus",
    "bus": "bus",
    "voitures": "car",
    "vehicules": "car",
    "cheminees": "chimney",
    "passages pietons": "crosswalk",
    "passages pour pietons": "crosswalk",
    "bornes incendie": "fire hydrant",
    "bouches d'incendie": "fire hydrant",
    "motos": "motorcycle",
    "motocyclettes": "motorcycle",
    "montagnes": "mountain",
    "collines": "mountain",
    "palmiers": "palm tree",
    "escaliers": "stair",
    "taxis": "taxi",
    "feux de circulation": "traffic light",
    "feux tricolores": "traffic light",
}

_MODELS_LOCK = threading.Lock()
_MODELS_READY = False


class _InlineExecutor:
    """Exécuteur minimal utilisé uniquement pendant l'import de reCognizer."""

    def __init__(self, *args, **kwargs):
        pass

    def submit(self, function, *args, **kwargs):
        future = concurrent.futures.Future()
        try:
            future.set_result(function(*args, **kwargs))
        except BaseException as error:
            future.set_exception(error)
        return future

    def shutdown(self, wait=True, *, cancel_futures=False):
        pass


def _english_challenge_label(prompt: str) -> str:
    plain = unicodedata.normalize("NFKD", prompt.casefold())
    plain = "".join(char for char in plain if not unicodedata.combining(char))
    for french, english in _FRENCH_LABELS.items():
        if french in plain:
            return english
    return prompt


def _prepare_recognizer_models() -> None:
    """Termine les chargements concurrents puis recrée YOLO dans un état CPU valide."""
    global _MODELS_READY
    if _MODELS_READY:
        return

    with _MODELS_LOCK:
        if _MODELS_READY:
            return

        # reCognizer 1.4 démarre YOLO, CLIP et CLIPSeg dans cinq threads dès
        # l'import. Torch 2.15 peut alors construire YOLO pendant le contexte
        # "meta" de Transformers. L'import séquentiel supprime cette course.
        original_executor = concurrent.futures.ThreadPoolExecutor
        try:
            if "recognizer.components.detector" not in sys.modules:
                concurrent.futures.ThreadPoolExecutor = _InlineExecutor
            from recognizer.components.detector import detection_models
        finally:
            concurrent.futures.ThreadPoolExecutor = original_executor

        from ultralytics import YOLO

        for loading_future in detection_models.loading_futures:
            loading_future.result()
        # reCognizer 1.4 initialise YOLO en parallèle de Transformers. Avec les
        # versions récentes de Torch, cette course peut laisser des tenseurs
        # temporaires sur le device "meta". Un rechargement séquentiel les évite.
        detection_models.yolo_model = YOLO("yolov8m-seg.pt")
        detection_models.yolo_model.predict(
            np.zeros((64, 64, 3), dtype=np.uint8),
            device="cpu",
            verbose=False,
        )
        _MODELS_READY = True


async def solve_recaptcha(page) -> str:
    """Résout le widget sur la page existante et retourne son jeton validé."""
    model_cache = Path(__file__).resolve().parents[1] / ".model-cache"
    os.environ.setdefault("HF_HOME", str(model_cache / "huggingface"))
    os.environ.setdefault("YOLO_CONFIG_DIR", str(model_cache / "ultralytics"))
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

    _prepare_recognizer_models()

    from recognizer import Detector
    from recognizer.agents.playwright import AsyncChallenger

    class FrenchAwareDetector(Detector):
        def detect(self, prompt, images, area_captcha=None):
            return super().detect(_english_challenge_label(prompt), images, area_captcha)

    class GridChallenger(AsyncChallenger):
        async def detect_tiles(self, prompt: str, area_captcha: bool) -> bool:
            frame = self.page.frame_locator("iframe[src*='bframe']")
            tiles = frame.locator(".rc-imageselect-tile")
            grid_image = await frame.locator("#rc-imageselect-target").screenshot()
            # Ultralytics/Torch doit aussi effectuer sa première inférence sur le
            # thread principal, sinon AutoBackend recrée le modèle sur "meta".
            response, _ = self.detector.detect(
                prompt, grid_image, area_captcha=area_captcha
            )
            tile_count = await tiles.count()
            if len(response) != tile_count:
                raise RuntimeError(
                    f"reCognizer a identifié {len(response)} cases pour une grille de {tile_count}."
                )
            selected = [index for index, match in enumerate(response) if match]
            print(f"🧩 reCognizer : {len(selected)} case(s) sélectionnée(s) sur {tile_count}.")
            for index in selected:
                await tiles.nth(index).click()
                if self.click_timeout:
                    await self.page.wait_for_timeout(self.click_timeout)
            return bool(selected)

    challenger = GridChallenger(page, retry_times=4, click_timeout=250)
    challenger.detector = FrenchAwareDetector()
    token = await asyncio.wait_for(challenger.solve_recaptcha(), timeout=120)
    if not isinstance(token, str) or not token:
        raise RuntimeError("reCognizer n'a pas retourné de validation reCAPTCHA.")
    return token
