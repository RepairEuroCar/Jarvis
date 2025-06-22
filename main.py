import asyncio
import logging
<<<<<<< HEAD
import os
import sys

from jarvis.app import Jarvis
=======
>>>>>>> main

from cli import run
from utils.logger import setup_logging

<<<<<<< HEAD
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,  # Измените на logging.DEBUG, если хотите видеть debug сообщения
    format="%(asctime)s [%(levelname)s] - %(module)s:%(lineno)d - %(message)s",  # Добавил module и lineno для лучшей отладки
    datefmt="%Y-%m-%d %H:%M:%S",
)
=======
setup_logging(level=logging.INFO)
>>>>>>> main


<<<<<<< HEAD

async def main():
    print("🔧 Запуск Jarvis...")
    logging.info("🟢 Jarvis стартует")

    jarvis_instance = (
        None  # Инициализируем None на случай ошибки в конструкторе Jarvis
    )
    try:
        jarvis_instance = Jarvis()
        await jarvis_instance.interactive_loop()
    except KeyboardInterrupt:
        print("\n🔕 Jarvis завершает работу по Ctrl+C")
        logging.warning("🔴 Прерывание пользователем (KeyboardInterrupt)")
    except Exception as e:
        # Логируем полное исключение, включая traceback
        logging.error(
            f"💥 Необработанное исключение в main: {e}", exc_info=True
        )
        # Можно также вывести traceback в консоль для немедленной диагностики
        # traceback.print_exc()
    finally:
        print("🚪 Завершение работы Jarvis...")
        logging.info("🚪 Jarvis начинает процедуру завершения.")

        if (
            jarvis_instance
            and hasattr(jarvis_instance, "memory")
            and hasattr(jarvis_instance, "save_memory")
        ):
            print("📂 Сохраняем память...")
            logging.info("📂 Попытка сохранить память")
            save_func = jarvis_instance.save_memory
            try:
                # В текущей реализации jarvis.py save_memory() синхронная
                if asyncio.iscoroutinefunction(save_func):
                    # Эта ветка не будет выполнена с текущим jarvis.py
                    await save_func()
                    logging.info("✅ Память успешно сохранена (асинхронно).")
                else:
                    save_func()
                    logging.info("✅ Память успешно сохранена (синхронно).")
            except Exception as save_error:
                logging.error(
                    f"❌ Ошибка при сохранении памяти: {save_error}",
                    exc_info=True,
                )
        elif jarvis_instance:
            logging.warning(
                "⚠️ Экземпляр Jarvis существует, но отсутствует метод save_memory или атрибут memory."
            )
        else:
            logging.warning(
                "⚠️ Экземпляр Jarvis не был создан, сохранение памяти невозможно."
            )

        print("✅ Jarvis завершил работу.")
        logging.info("🔚 Jarvis полностью завершил работу.")
=======
async def main() -> None:
    """Entry point that starts the command line interface."""
    await run()

>>>>>>> main


if __name__ == "__main__":
<<<<<<< HEAD
    # Для Windows может потребоваться другая политика цикла событий asyncio, если возникают проблемы
    # if sys.platform == "win32":
    #    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
=======
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nJarvis завершил работу.")
>>>>>>> main
