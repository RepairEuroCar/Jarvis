from jarvis.helpers.design import design_module


def test_design_detects_telegram_bot():
    desc = "Создай телеграм бота для отправки напоминаний"
    result = design_module(desc)
    assert result["project_type"] == "telegram_bot"
    assert "bot.py" in result["files"]
    assert "TelegramBot" in result["classes"]


def test_design_extracts_files_and_classes():
    desc = "Create file helper.py with class Helper"
    result = design_module(desc)
    assert "helper.py" in result["files"]
    assert "Helper" in result["classes"]
