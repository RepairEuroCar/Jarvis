from utils.import_inference import infer_imports


def test_infer_telegram_import():
    imports = infer_imports("Создай телеграм бота")
    assert any("aiogram" in imp for imp in imports)
