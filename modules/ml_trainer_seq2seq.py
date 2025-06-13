# modules/ml_trainer_seq2seq.py
import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset  # Добавлен Dataset
from torch.utils.tensorboard import SummaryWriter
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    DataCollatorForSeq2Seq,
    PreTrainedModel,
    PreTrainedTokenizerFast,
)

# Command metadata used by Jarvis
from commands.registry import CommandCategory, CommandInfo

logger = logging.getLogger(__name__)  # Логгер для модуля

MODULE_METADATA = {
    "name": "Seq2Seq_ML_Trainer",
    "version": "0.2.0",  # Версия обновлена
    "description": "Модуль для обучения и использования Seq2Seq моделей с улучшенной загрузкой данных.",
    "dependencies": [],
    "author": "Jarvis Enhanced",
}


# Простой пользовательский Dataset для Seq2Seq задач
class CustomSeq2SeqDataset(Dataset):
    def __init__(
        self,
        data_path: str,
        tokenizer: PreTrainedTokenizerFast,
        max_source_length: int,
        max_target_length: int,
        source_prefix: Optional[str] = None,
    ):
        self.tokenizer = tokenizer
        self.max_source_length = max_source_length
        self.max_target_length = max_target_length
        self.source_prefix = source_prefix if source_prefix else ""

        self.source_texts: List[str] = []
        self.target_texts: List[str] = []

        logger.info(f"Загрузка данных из: {data_path}")
        try:
            # Предполагаем, что данные в JSON файле, каждая строка - объект {"source_text": "...", "target_text": "..."}
            # или файл, где каждая строка - это JSON-объект.
            if not os.path.exists(data_path):
                raise FileNotFoundError(f"Файл данных не найден: {data_path}")

            with open(data_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f):
                    try:
                        record = json.loads(line.strip())
                        source = record.get("source_text")
                        target = record.get("target_text")
                        if source and target:
                            self.source_texts.append(self.source_prefix + source)
                            self.target_texts.append(target)
                        else:
                            logger.warning(
                                f"Пропущена запись в строке {line_num+1} в {data_path}: отсутствует source_text или target_text."
                            )
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Ошибка декодирования JSON в строке {line_num+1} в {data_path}. Строка пропущена."
                        )

            if not self.source_texts:
                logger.error(
                    f"Данные не загружены или файл {data_path} пуст/некорректен."
                )
                # Можно выбросить исключение, если пустой датасет недопустим
                # raise ValueError(f"Не удалось загрузить данные из {data_path}")
            else:
                logger.info(f"Загружено {len(self.source_texts)} записей.")

        except FileNotFoundError:
            logger.error(f"Файл данных не найден: {data_path}")
            raise
        except Exception as e:
            logger.error(
                f"Непредвиденная ошибка при загрузке данных из {data_path}: {e}"
            )
            raise

    def __len__(self):
        return len(self.source_texts)

    def __getitem__(self, idx) -> Dict[str, torch.Tensor]:
        source_text = self.source_texts[idx]
        target_text = self.target_texts[idx]

        # Токенизация исходного текста
        source_encoding = self.tokenizer(
            source_text,
            max_length=self.max_source_length,
            padding="max_length",  # Важно для батчинга, если не используется data_collator
            truncation=True,
            return_tensors="pt",
        )

        # Токенизация целевого текста (для labels)
        # Для моделей энкодер-декодер, labels обычно являются target_ids
        with self.tokenizer.as_target_tokenizer():  # Важно для некоторых токенизаторов (например, mBART)
            target_encoding = self.tokenizer(
                target_text,
                max_length=self.max_target_length,
                padding="max_length",
                truncation=True,
                return_tensors="pt",
            )

        labels = target_encoding.input_ids
        # Для моделей типа T5, pad_token_id в labels заменяется на -100, чтобы они игнорировались в loss
        labels[labels == self.tokenizer.pad_token_id] = -100

        return {
            "input_ids": source_encoding.input_ids.squeeze(),  # Убираем размерность батча (1)
            "attention_mask": source_encoding.attention_mask.squeeze(),
            "labels": labels.squeeze(),
        }


class Seq2SeqTrainer:
    def __init__(self, jarvis_instance: Any, config: Dict[str, Any]):
        self.jarvis = jarvis_instance
        self.config = config
        logger.info(f"Инициализация Seq2SeqTrainer с конфигурацией: {config}")

        self.device = torch.device(
            config.get("device", "cuda" if torch.cuda.is_available() else "cpu")
        )
        logger.info(f"Используемое устройство: {self.device}")

        self.model_name = config.get("model_name_or_path", "t5-small")
        self.tokenizer_name = config.get("tokenizer_name_or_path", self.model_name)
        self.source_prefix = config.get(
            "source_prefix", None
        )  # Например, "translate English to German: "

        try:
            self.tokenizer: PreTrainedTokenizerFast = AutoTokenizer.from_pretrained(
                self.tokenizer_name
            )
            self.model: PreTrainedModel = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_name
            ).to(self.device)
        except Exception as e:
            logger.error(
                f"Ошибка загрузки модели или токенизатора ({self.model_name}): {e}"
            )
            raise

        self.learning_rate = float(config.get("learning_rate", 5e-5))
        self.weight_decay = float(config.get("weight_decay", 0.01))
        self.num_epochs = int(config.get("num_epochs", 3))
        self.checkpoint_dir = config.get("checkpoint_dir", "./ml_checkpoints")
        os.makedirs(self.checkpoint_dir, exist_ok=True)

        tensorboard_log_dir = config.get(
            "tensorboard_log_dir",
            os.path.join(
                self.checkpoint_dir, "runs", config.get("trainer_id", "default_trainer")
            ),
        )
        os.makedirs(tensorboard_log_dir, exist_ok=True)
        self.writer = SummaryWriter(log_dir=tensorboard_log_dir)

        self.max_source_length = int(config.get("max_source_length", 128))
        self.max_target_length = int(
            config.get("max_target_length", 128)
        )  # Отдельно для цели
        self.batch_size = int(config.get("batch_size", 8))
        self.max_grad_norm = float(config.get("max_grad_norm", 1.0))
        self.log_interval = int(config.get("log_interval", 50))
        self.patience = int(config.get("patience", 3))
        self.dataloader_num_workers = int(
            config.get("dataloader_num_workers", 0)
        )  # Для DataLoader

        # DataCollator для Seq2Seq (обрабатывает padding на уровне батча)
        self.data_collator = DataCollatorForSeq2Seq(
            tokenizer=self.tokenizer,
            model=self.model,
            padding="longest",  # или True, или 'max_length'
        )

        self.train_loader: Optional[DataLoader] = self._get_dataloader(
            config.get("train_data_path"), "train"
        )
        self.val_loader: Optional[DataLoader] = self._get_dataloader(
            config.get("val_data_path"), "val"
        )
        self.test_loader: Optional[DataLoader] = self._get_dataloader(
            config.get("test_data_path"), "test"
        )

        self.optimizer: Optional[optim.Optimizer] = None
        self.scheduler: Optional[optim.lr_scheduler._LRScheduler] = None
        self.criterion: Optional[nn.Module] = None

        self.global_step = 0
        self.current_epoch = 0

        logger.info("Seq2SeqTrainer успешно инициализирован.")

    def _get_dataloader(
        self, data_path: Optional[str], split: str
    ) -> Optional[DataLoader]:
        if not data_path:
            logger.warning(
                f"Путь к данным для '{split}' не указан. DataLoader не создан."
            )
            return None

        try:
            dataset = CustomSeq2SeqDataset(
                data_path=data_path,
                tokenizer=self.tokenizer,
                max_source_length=self.max_source_length,
                max_target_length=self.max_target_length,
                source_prefix=self.source_prefix,
            )
            if len(dataset) == 0:
                logger.warning(
                    f"Датасет для '{split}' ({data_path}) пуст. DataLoader не будет эффективен."
                )
                # Можно вернуть None или пустой DataLoader, в зависимости от желаемого поведения
                return None  # или DataLoader([], batch_size=self.batch_size, collate_fn=self.data_collator)

            return DataLoader(
                dataset,
                batch_size=self.batch_size,
                shuffle=(split == "train"),  # Перемешиваем только для обучающего набора
                num_workers=self.dataloader_num_workers,
                collate_fn=self.data_collator,  # Используем DataCollator
                pin_memory=True if self.device.type == "cuda" else False,
            )
        except FileNotFoundError:
            logger.error(f"Файл данных для '{split}' не найден по пути: {data_path}")
            return None
        except Exception as e:
            logger.error(
                f"Ошибка при создании DataLoader для '{split}' ({data_path}): {e}"
            )
            return None

    def _prepare_optimization_parameters(self):
        if self.model is None:
            logger.error(
                "Модель не инициализирована. Невозможно подготовить параметры оптимизации."
            )
            return

        # Параметры, для которых не применяется weight decay (bias, LayerNorm веса)
        no_decay = ["bias", "LayerNorm.weight"]
        optimizer_grouped_parameters = [
            {
                "params": [
                    p
                    for n, p in self.model.named_parameters()
                    if not any(nd in n for nd in no_decay)
                ],
                "weight_decay": self.weight_decay,
            },
            {
                "params": [
                    p
                    for n, p in self.model.named_parameters()
                    if any(nd in n for nd in no_decay)
                ],
                "weight_decay": 0.0,
            },
        ]
        self.optimizer = optim.AdamW(
            optimizer_grouped_parameters,  # Используем сгруппированные параметры
            lr=self.learning_rate,
        )

        num_training_steps = self.num_epochs * (
            len(self.train_loader) if self.train_loader else 1
        )
        self.scheduler = optim.lr_scheduler.CosineAnnealingLR(  # или другой шедулер, например, get_linear_schedule_with_warmup
            self.optimizer,
            T_max=num_training_steps,
            eta_min=self.config.get(
                "scheduler_eta_min", 1e-7
            ),  # Меньшее значение для eta_min
        )
        # CrossEntropyLoss уже встроена в модели Hugging Face, когда передаются labels.
        # self.criterion не нужен, если модель сама считает loss.
        # Если бы мы считали loss вручную:
        # self.criterion = nn.CrossEntropyLoss(ignore_index=self.tokenizer.pad_token_id if self.tokenizer else -100)
        logger.info("Параметры оптимизации подготовлены.")

    def _create_checkpoint(self, epoch: int, val_loss: float):
        if self.model is None or self.optimizer is None or self.scheduler is None:
            logger.error(
                "Модель, оптимизатор или планировщик не инициализированы. Чекпоинт не создан."
            )
            return

        checkpoint_path = os.path.join(
            self.checkpoint_dir, f"checkpoint_epoch_{epoch}_valloss_{val_loss:.4f}.pt"
        )
        # Сохраняем только state_dict, а не весь объект модели/токенизатора
        # Токенизатор обычно сохраняется отдельно или загружается по имени.
        checkpoint = {
            "epoch": epoch,
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "scheduler_state_dict": self.scheduler.state_dict(),
            "val_loss": val_loss,
            "config": self.config,
            "model_name": self.model_name,  # Сохраняем имя модели для восстановления
            "tokenizer_name": self.tokenizer_name,  # И имя токенизатора
        }
        try:
            torch.save(checkpoint, checkpoint_path)
            logger.info(f"Чекпоинт сохранен: {checkpoint_path}")
        except Exception as e:
            logger.error(f"Ошибка сохранения чекпоинта {checkpoint_path}: {e}")

    def _load_checkpoint(self, checkpoint_path: str) -> Tuple[int, float]:
        if not os.path.exists(checkpoint_path):
            logger.error(f"Файл чекпоинта не найден: {checkpoint_path}")
            raise FileNotFoundError(f"Чекпоинт {checkpoint_path} не найден.")

        logger.info(f"Загрузка чекпоинта из: {checkpoint_path}")
        try:
            checkpoint = torch.load(checkpoint_path, map_location=self.device)

            # Проверяем, совпадает ли модель и токенизатор
            if self.model_name != checkpoint.get(
                "model_name"
            ) or self.tokenizer_name != checkpoint.get("tokenizer_name"):
                logger.warning(
                    "Модель или токенизатор в чекпоинте отличаются от текущих. "
                    "Попытка загрузить state_dict может быть несовместима. "
                    "Рекомендуется пересоздать тренер с правильной конфигурацией из чекпоинта."
                )
                # В идеале, здесь нужно пересоздать self.model и self.tokenizer, если они отличаются.
                # self.model = AutoModelForSeq2SeqLM.from_pretrained(checkpoint['model_name']).to(self.device)
                # self.tokenizer = AutoTokenizer.from_pretrained(checkpoint['tokenizer_name'])

            self.model.load_state_dict(checkpoint["model_state_dict"])

            self._prepare_optimization_parameters()
            if self.optimizer and "optimizer_state_dict" in checkpoint:
                self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
            if self.scheduler and "scheduler_state_dict" in checkpoint:
                self.scheduler.load_state_dict(checkpoint["scheduler_state_dict"])

            self.current_epoch = checkpoint.get("epoch", -1)  # Восстанавливаем эпоху
            self.global_step = checkpoint.get(
                "global_step", 0
            )  # И глобальный шаг, если он сохранялся

            val_loss = checkpoint.get("val_loss", float("inf"))

            logger.info(
                f"Чекпоинт успешно загружен. Эпоха: {self.current_epoch}, Val Loss: {val_loss:.4f}"
            )
            return self.current_epoch, val_loss
        except Exception as e:
            logger.error(f"Ошибка загрузки чекпоинта {checkpoint_path}: {e}")
            raise

    def _calculate_metrics(
        self, logits: torch.Tensor, targets: torch.Tensor
    ) -> Dict[str, float]:
        if (
            logits is None
            or targets is None
            or logits.numel() == 0
            or targets.numel() == 0
        ):
            logger.warning("Logits или targets пусты. Метрики не могут быть вычислены.")
            return {
                "accuracy": 0.0,
                "perplexity": float("inf"),
                "loss": float("inf"),
            }  # Возвращаем дефолтные значения

        predictions_ids = torch.argmax(logits.detach(), dim=-1)

        targets_cpu = targets.cpu()
        predictions_ids_cpu = predictions_ids.cpu()

        mask = (targets_cpu != self.tokenizer.pad_token_id) & (
            targets_cpu != -100
        )  # -100 тоже игнорируем

        masked_predictions = torch.masked_select(predictions_ids_cpu, mask)
        masked_targets = torch.masked_select(targets_cpu, mask)

        accuracy = (
            (masked_predictions == masked_targets).float().mean().item()
            if masked_targets.numel() > 0
            else 0.0
        )

        vocab_size = logits.size(-1)
        reshaped_logits = logits.view(-1, vocab_size)
        reshaped_targets = targets.view(-1)

        try:
            # Убедимся, что ignore_index корректен
            ignore_idx = (
                self.tokenizer.pad_token_id
                if self.tokenizer.pad_token_id is not None
                else -100
            )

            cross_entropy_loss_val = F.cross_entropy(
                reshaped_logits, reshaped_targets, ignore_index=ignore_idx
            )
            perplexity = torch.exp(cross_entropy_loss_val).item()
        except Exception as e:
            logger.warning(
                f"Ошибка при вычислении perplexity: {e}. Perplexity будет inf."
            )
            perplexity = float("inf")

        return {
            "accuracy": accuracy,
            "perplexity": perplexity,
            # 'loss' будет добавлен отдельно, так как он приходит из model.forward()
        }

    def _log_metrics(
        self, metrics: dict, prefix: str, epoch: int, step: Optional[int] = None
    ):
        log_step = (
            step
            if step is not None
            else (epoch + 1)
            * (len(self.train_loader) if self.train_loader and prefix == "train" else 1)
        )

        for name, value in metrics.items():
            if value is not None and not (
                isinstance(value, float)
                and (
                    torch.isinf(torch.tensor(value)) or torch.isnan(torch.tensor(value))
                )
            ):
                self.writer.add_scalar(f"{prefix}/{name}", value, log_step)

        step_info = f"Step: {step} | " if step is not None else ""
        loss_val = metrics.get("loss", float("nan"))
        acc_val = metrics.get("accuracy", float("nan"))
        perp_val = metrics.get("perplexity", float("nan"))

        print(
            f"Epoch: {epoch + 1} | {step_info}"  # Эпохи обычно считаются с 1
            f"Loss: {loss_val:.4f} | "
            f"Accuracy: {acc_val:.4f} | "
            f"Perplexity: {perp_val:.2f} ({prefix})"
        )

    async def train_epoch_async(self, dataloader: DataLoader, current_epoch: int):
        if self.model is None or self.optimizer is None or dataloader is None:
            logger.error(
                "Модель, оптимизатор или DataLoader не инициализированы для обучения эпохи."
            )
            await self.jarvis.publish_event(
                "ml_training_error", error="Epoch training initialization error"
            )
            return float("inf")

        self.model.train()
        total_loss = 0.0

        epoch_predictions_logits_list = []
        epoch_targets_list = []

        logger.info(f"Начало эпохи обучения {current_epoch + 1}...")
        progress_bar = None
        try:  # Для tqdm, если установлен
            from tqdm.asyncio import (
                tqdm,  # Используем tqdm.asyncio для асинхронного цикла
            )

            progress_bar = tqdm(
                enumerate(dataloader),
                total=len(dataloader),
                desc=f"Epoch {current_epoch + 1} Training",
            )
        except ImportError:
            logger.info(
                "Библиотека tqdm не найдена. Прогресс-бар не будет отображаться."
            )
            progress_bar = enumerate(dataloader)

        for batch_idx, batch in progress_bar:
            # Перемещаем батч на устройство (DataCollator обычно это делает, но для надежности)
            # batch = {k: v.to(self.device) for k, v in batch.items() if isinstance(v, torch.Tensor)}
            # DataCollatorForSeq2Seq уже должен вернуть тензоры на нужном устройстве, если модель на нем.
            # Но если нет, то:
            input_ids = batch["input_ids"].to(self.device, non_blocking=True)
            attention_mask = batch["attention_mask"].to(self.device, non_blocking=True)
            labels = batch["labels"].to(self.device, non_blocking=True)

            self.optimizer.zero_grad()
            outputs = self.model(
                input_ids=input_ids, attention_mask=attention_mask, labels=labels
            )
            loss = outputs.loss

            if loss is None:
                logger.error(
                    f"Loss is None на батче {batch_idx}. Проверьте модель и данные."
                )
                await self.jarvis.publish_event(
                    "ml_training_error", error="Loss is None during training"
                )
                continue

            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
            self.optimizer.step()
            if self.scheduler:
                self.scheduler.step()

            current_loss_item = loss.item()
            total_loss += current_loss_item

            if self.log_interval > 0 and (
                batch_idx % self.log_interval == 0 or batch_idx == len(dataloader) - 1
            ):
                # Логируем метрики по текущему батчу (или накопленным, если есть смысл)
                # Для простоты, пока логируем только loss батча
                batch_metrics = {"loss": current_loss_item}
                # Можно добавить расчет accuracy/perplexity по батчу, если это не слишком замедляет
                # current_logits_batch = outputs.logits.detach()
                # current_targets_batch = labels.detach()
                # batch_acc_perp = self._calculate_metrics(current_logits_batch, current_targets_batch)
                # batch_metrics.update(batch_acc_perp)

                self._log_metrics(
                    batch_metrics, "train_batch", current_epoch, self.global_step
                )
                await self.jarvis.publish_event(
                    "ml_training_batch_end",
                    epoch=current_epoch,
                    batch=batch_idx,
                    metrics=batch_metrics,
                )

            self.global_step += 1
            if isinstance(progress_bar, tqdm):  # Обновляем описание прогресс-бара
                progress_bar.set_postfix(
                    loss=f"{current_loss_item:.4f}",
                    avg_loss=f"{total_loss / (batch_idx + 1):.4f}",
                )

            # Освобождаем память GPU, если возможно (осторожно, может замедлить)
            # del inputs, attention_mask, labels, outputs, loss
            # if self.device.type == 'cuda': torch.cuda.empty_cache()

        avg_epoch_loss = (
            total_loss / len(dataloader) if len(dataloader) > 0 else float("inf")
        )
        logger.info(
            f"Эпоха обучения {current_epoch + 1} завершена. Средний Loss: {avg_epoch_loss:.4f}"
        )
        return avg_epoch_loss

    async def validate_epoch_async(self, dataloader: DataLoader, current_epoch: int):
        if self.model is None or dataloader is None:
            logger.error(
                "Модель или DataLoader не инициализированы для валидации эпохи."
            )
            await self.jarvis.publish_event(
                "ml_validation_error", error="Epoch validation initialization error"
            )
            return float("inf")

        self.model.eval()
        total_loss = 0.0
        epoch_predictions_logits_list = []
        epoch_targets_list = []

        logger.info(f"Начало эпохи валидации {current_epoch + 1}...")
        progress_bar_val = None
        try:
            from tqdm.asyncio import tqdm

            progress_bar_val = tqdm(
                dataloader,
                total=len(dataloader),
                desc=f"Epoch {current_epoch + 1} Validation",
            )
        except ImportError:
            progress_bar_val = dataloader

        with torch.no_grad():
            for batch in progress_bar_val:
                input_ids = batch["input_ids"].to(self.device, non_blocking=True)
                attention_mask = batch["attention_mask"].to(
                    self.device, non_blocking=True
                )
                labels = batch["labels"].to(self.device, non_blocking=True)

                outputs = self.model(
                    input_ids=input_ids, attention_mask=attention_mask, labels=labels
                )
                loss = outputs.loss
                if loss is None:
                    continue

                total_loss += loss.item()
                epoch_predictions_logits_list.append(
                    outputs.logits.detach().cpu()
                )  # Перемещаем на CPU сразу
                epoch_targets_list.append(labels.detach().cpu())

        if not epoch_predictions_logits_list:
            logger.warning("Нет данных для валидации в этой эпохе.")
            return float("inf")

        all_logits = torch.cat(epoch_predictions_logits_list, dim=0).to(
            self.device
        )  # Возвращаем на device для метрик, если нужно
        all_targets = torch.cat(epoch_targets_list, dim=0).to(self.device)

        metrics = self._calculate_metrics(all_logits, all_targets)
        avg_epoch_loss = (
            total_loss / len(dataloader) if len(dataloader) > 0 else float("inf")
        )
        metrics.update({"loss": avg_epoch_loss})

        self._log_metrics(metrics, "val", current_epoch)
        await self.jarvis.publish_event(
            "ml_validation_epoch_end", epoch=current_epoch, metrics=metrics
        )
        logger.info(
            f"Эпоха валидации {current_epoch + 1} завершена. Средний Loss: {avg_epoch_loss:.4f}"
        )
        return avg_epoch_loss

    async def train_async(self):
        if not self.train_loader or not self.val_loader:
            msg = "Train loader или Validation loader не инициализированы. Обучение невозможно."
            logger.error(msg)
            await self.jarvis.publish_event("ml_training_error", error=msg)
            return {"status": "error", "message": msg}

        self._prepare_optimization_parameters()
        if not self.optimizer:
            msg = "Оптимизатор не был создан. Обучение невозможно."
            logger.error(msg)
            await self.jarvis.publish_event("ml_training_error", error=msg)
            return {"status": "error", "message": msg}

        best_val_loss = float("inf")
        early_stopping_counter = 0
        # self.global_step = 0 # Сброс уже не нужен здесь, если он делается при загрузке чекпоинта или старте

        logger.info(f"Начало цикла обучения на {self.num_epochs} эпох.")
        await self.jarvis.publish_event(
            "ml_training_start", epochs=self.num_epochs, config=self.config
        )

        start_epoch = (
            self.current_epoch
        )  # Если загрузили чекпоинт, начинаем с сохраненной эпохи + 1

        for epoch_idx in range(start_epoch, self.num_epochs):
            self.current_epoch = epoch_idx  # Обновляем текущую эпоху тренера
            logger.info(f"--- Эпоха {self.current_epoch + 1}/{self.num_epochs} ---")

            train_loss = await self.train_epoch_async(
                self.train_loader, self.current_epoch
            )
            val_loss = await self.validate_epoch_async(
                self.val_loader, self.current_epoch
            )

            await self.jarvis.publish_event(
                "ml_training_epoch_end",
                epoch=self.current_epoch,
                train_loss=train_loss,
                val_loss=val_loss,
            )

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                early_stopping_counter = 0
                self._create_checkpoint(
                    self.current_epoch, val_loss
                )  # Сохраняем с текущей эпохой
                logger.info(
                    f"Новый лучший val_loss: {best_val_loss:.4f}. Чекпоинт сохранен для эпохи {self.current_epoch + 1}."
                )
            else:
                early_stopping_counter += 1
                logger.info(
                    f"Val_loss не улучшился ({val_loss:.4f} vs best {best_val_loss:.4f}). Счетчик early stopping: {early_stopping_counter}/{self.patience}"
                )
                if early_stopping_counter >= self.patience:
                    logger.info(
                        f"Ранняя остановка на эпохе {self.current_epoch + 1}. Val_loss не улучшался {self.patience} эпох."
                    )
                    await self.jarvis.publish_event(
                        "ml_training_early_stop",
                        epoch=self.current_epoch,
                        best_val_loss=best_val_loss,
                    )
                    break

        final_epochs_completed = self.current_epoch + 1
        logger.info(
            f"Обучение завершено. Всего эпох: {final_epochs_completed}, лучший val_loss: {best_val_loss:.4f}"
        )
        await self.jarvis.publish_event(
            "ml_training_end",
            best_val_loss=best_val_loss,
            epochs_completed=final_epochs_completed,
        )
        return {
            "status": "completed",
            "best_val_loss": best_val_loss,
            "epochs_completed": final_epochs_completed,
        }

    async def evaluate_async(self, test_loader: Optional[DataLoader] = None):
        loader_to_use = test_loader if test_loader else self.test_loader
        if self.model is None or loader_to_use is None:
            msg = "Модель или test_loader не инициализированы. Оценка невозможна."
            logger.error(msg)
            await self.jarvis.publish_event("ml_evaluation_error", error=msg)
            return {"status": "error", "message": msg, "metrics": {}}

        self.model.eval()
        total_loss = 0.0
        epoch_predictions_logits_list = []
        epoch_targets_list = []

        logger.info("Начало оценки модели на тестовом наборе...")
        with torch.no_grad():
            for batch in loader_to_use:  # Можно добавить tqdm здесь тоже
                input_ids = batch["input_ids"].to(self.device, non_blocking=True)
                attention_mask = batch["attention_mask"].to(
                    self.device, non_blocking=True
                )
                labels = batch["labels"].to(self.device, non_blocking=True)

                outputs = self.model(
                    input_ids=input_ids, attention_mask=attention_mask, labels=labels
                )
                loss = outputs.loss
                if loss is None:
                    continue
                total_loss += loss.item()
                epoch_predictions_logits_list.append(outputs.logits.detach().cpu())
                epoch_targets_list.append(labels.detach().cpu())

        if not epoch_predictions_logits_list:
            msg = "Нет данных для оценки в тестовом наборе."
            logger.warning(msg)
            await self.jarvis.publish_event("ml_evaluation_error", error=msg)
            return {"status": "warning", "message": msg, "metrics": {}}

        all_logits = torch.cat(epoch_predictions_logits_list, dim=0).to(self.device)
        all_targets = torch.cat(epoch_targets_list, dim=0).to(self.device)

        metrics = self._calculate_metrics(all_logits, all_targets)
        avg_loss = (
            total_loss / len(loader_to_use) if len(loader_to_use) > 0 else float("inf")
        )
        metrics.update({"loss": avg_loss})

        self._log_metrics(metrics, "test", epoch=-1, step=self.global_step)
        logger.info(f"Оценка завершена. Метрики: {metrics}")
        await self.jarvis.publish_event("ml_evaluation_end", metrics=metrics)
        return {"status": "completed", "metrics": metrics}

    async def predict_async(self, text: str, max_length: Optional[int] = None) -> str:
        if self.model is None or self.tokenizer is None:
            logger.error("Модель или токенизатор не инициализированы для предсказания.")
            return "Ошибка: Модель не готова."

        self.model.eval()
        eff_max_length = (
            max_length
            if max_length is not None
            else int(self.config.get("predict_max_length", 50))
        )
        # Добавляем префикс, если он есть
        prefixed_text = self.source_prefix + text if self.source_prefix else text

        try:
            encoding = self.tokenizer(
                prefixed_text,
                return_tensors="pt",
                # padding='max_length', # Для generate лучше не использовать max_length padding на входе
                truncation=True,
                max_length=self.max_source_length,
            )
            input_ids = encoding["input_ids"].to(self.device)
            attention_mask = encoding["attention_mask"].to(self.device)

            generation_params = {
                "max_length": eff_max_length,
                "num_beams": int(self.config.get("predict_num_beams", 5)),
                "early_stopping": self.config.get("predict_early_stopping", True),
                "temperature": float(self.config.get("predict_temperature", 1.0)),
                "top_k": int(self.config.get("predict_top_k", 50)),
                "top_p": float(self.config.get("predict_top_p", 1.0)),
                "repetition_penalty": float(
                    self.config.get("predict_repetition_penalty", 1.0)
                ),
                "length_penalty": float(self.config.get("predict_length_penalty", 1.0)),
                "no_repeat_ngram_size": int(
                    self.config.get("predict_no_repeat_ngram_size", 3)
                ),  # Часто полезно
            }
            # Удаляем параметры, которые могут быть None или не поддерживаться всеми моделями
            generation_params = {
                k: v for k, v in generation_params.items() if v is not None
            }

            with torch.no_grad():
                outputs = self.model.generate(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    **generation_params,
                )

            decoded_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            logger.info(
                f"Предсказание для '{text}' (с префиксом '{self.source_prefix if self.source_prefix else ''}'): '{decoded_text}'"
            )
            return decoded_text
        except Exception as e:
            logger.error(
                f"Ошибка во время предсказания для текста '{text}': {e}", exc_info=True
            )
            return f"Ошибка предсказания: {e}"

    def save_model_local(self, path: Optional[str] = None):
        if self.model is None or self.tokenizer is None:
            logger.error(
                "Модель или токенизатор не инициализированы. Сохранение невозможно."
            )
            return "Ошибка: Модель или токенизатор не инициализированы."

        trainer_id = self.config.get("trainer_id", "default_trainer")
        default_save_path = os.path.join(self.checkpoint_dir, trainer_id, "final_model")
        save_path = path if path else default_save_path

        os.makedirs(save_path, exist_ok=True)
        try:
            self.model.save_pretrained(save_path)
            self.tokenizer.save_pretrained(save_path)

            # Сохраняем конфигурацию тренера
            trainer_config_path = os.path.join(save_path, "trainer_config.json")
            with open(trainer_config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"Конфигурация тренера сохранена в {trainer_config_path}")

            logger.info(f"Модель и токенизатор сохранены в: {save_path}")
            return f"Модель сохранена в {save_path}"
        except Exception as e:
            logger.error(f"Ошибка сохранения модели в {save_path}: {e}")
            return f"Ошибка сохранения модели: {e}"

    @classmethod
    def load_model_from_path(
        cls,
        path: str,
        config_overrides: Optional[Dict[str, Any]] = None,
        jarvis_instance: Optional[Any] = None,
    ):
        if not os.path.isdir(path):
            logger.error(f"Путь для загрузки модели не является директорией: {path}")
            return None

        config_path = os.path.join(path, "trainer_config.json")
        loaded_config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
            except Exception as e:
                logger.warning(
                    f"Не удалось загрузить trainer_config.json из {path}: {e}. Используются только overrides."
                )

        if config_overrides:
            loaded_config.update(config_overrides)

        loaded_config.setdefault("model_name_or_path", path)
        loaded_config.setdefault("tokenizer_name_or_path", path)

        if jarvis_instance is None:

            class MockJarvis:
                async def publish_event(self, *args, **kwargs):
                    pass

            jarvis_instance = MockJarvis()

        try:
            return cls(jarvis_instance=jarvis_instance, config=loaded_config)
        except Exception as e:
            logger.error(
                f"Ошибка при создании экземпляра Seq2SeqTrainer из пути {path}: {e}",
                exc_info=True,
            )
            return None

    def __del__(self):
        if hasattr(self, "writer") and self.writer:
            try:
                self.writer.close()
            except Exception as e:
                logger.warning(f"Ошибка при закрытии TensorBoard SummaryWriter: {e}")


active_trainers: Dict[str, Seq2SeqTrainer] = {}


async def init_module(jarvis: Any, module_config: Dict[str, Any]):
    logger.info(f"Модуль {MODULE_METADATA['name']} инициализирован.")
    logger.debug(f"Конфигурация модуля при инициализации: {module_config}")

    default_trainer_id = module_config.get("default_trainer_id")
    if default_trainer_id:
        # Конфигурация для default_trainer_id должна быть в памяти Jarvis
        # или module_config может содержать полный конфиг для него
        default_config = jarvis.memory.query(
            f"system.module_configs.ml_trainer_seq2seq.{default_trainer_id}"
        )
        if not default_config and isinstance(
            module_config.get(default_trainer_id), dict
        ):  # Проверяем, есть ли конфиг в module_config
            default_config = module_config.get(default_trainer_id)

        if default_config:
            logger.info(
                f"Попытка предзагрузки тренера по умолчанию с ID: {default_trainer_id}"
            )
            # Передаем ID как часть конфига, чтобы он сохранился
            default_config.setdefault("trainer_id", default_trainer_id)
            try:
                active_trainers[default_trainer_id] = Seq2SeqTrainer(
                    jarvis_instance=jarvis, config=default_config
                )
                logger.info(
                    f"Тренер по умолчанию '{default_trainer_id}' успешно настроен."
                )
            except Exception as e:
                logger.error(
                    f"Ошибка предзагрузки тренера по умолчанию '{default_trainer_id}': {e}"
                )
        else:
            logger.warning(
                f"Конфигурация для тренера по умолчанию '{default_trainer_id}' не найдена."
            )


async def deinit_module(jarvis: Any):
    global active_trainers
    for trainer_name, trainer_instance in list(active_trainers.items()):
        if hasattr(trainer_instance, "__del__"):
            trainer_instance.__del__()
        del active_trainers[trainer_name]
    logger.info(
        f"Модуль {MODULE_METADATA['name']} деинициализирован, все активные тренеры остановлены."
    )


async def setup_trainer_command(jarvis: Any, args_str: str) -> str:
    global active_trainers
    config_name_or_path = args_str.strip()
    if not config_name_or_path:
        return (
            "Использование: setup_seq2seq_trainer <trainer_id_или_путь_к_json_конфигу>"
        )

    config_dict: Optional[Dict[str, Any]] = None
    trainer_id = config_name_or_path  # По умолчанию ID = имя конфига/путь

    # 1. Проверяем, не является ли это ID уже существующего конфига в памяти
    # Путь в памяти: system.module_configs.<имя_модуля>.<trainer_id>
    memory_config_path = (
        f"system.module_configs.{MODULE_METADATA['name']}.{config_name_or_path}"
    )
    config_from_memory = jarvis.memory.query(memory_config_path)

    if isinstance(config_from_memory, dict):
        config_dict = config_from_memory
        logger.info(
            f"Загружена конфигурация тренера '{trainer_id}' из памяти Jarvis: {memory_config_path}"
        )
    elif os.path.exists(config_name_or_path) and config_name_or_path.endswith(".json"):
        try:
            with open(config_name_or_path, "r", encoding="utf-8") as f:
                config_dict = json.load(f)
            logger.info(
                f"Загружена конфигурация тренера из файла: {config_name_or_path}"
            )
            # Если загрузили из файла, ID может быть внутри файла или равен имени файла
            trainer_id = config_dict.get(
                "trainer_id", os.path.splitext(os.path.basename(config_name_or_path))[0]
            )
        except Exception as e:
            return (
                f"Ошибка загрузки JSON конфигурации из файла {config_name_or_path}: {e}"
            )
    else:
        return f"Конфигурация '{config_name_or_path}' не найдена ни в памяти Jarvis ({memory_config_path}), ни как JSON файл."

    if not config_dict:
        return f"Не удалось получить конфигурацию для '{config_name_or_path}'."

    # Убедимся, что trainer_id есть в конфиге, чтобы он сохранялся с моделью
    config_dict.setdefault("trainer_id", trainer_id)

    try:
        if trainer_id in active_trainers:
            logger.warning(
                f"Тренер с ID '{trainer_id}' уже существует. Пересоздание..."
            )
            # Можно добавить логику закрытия старого тренера
            if hasattr(active_trainers[trainer_id], "__del__"):
                active_trainers[trainer_id].__del__()

        active_trainers[trainer_id] = Seq2SeqTrainer(
            jarvis_instance=jarvis, config=config_dict
        )
        return f"Экземпляр тренера Seq2Seq с ID '{trainer_id}' успешно настроен/пересоздан."
    except Exception as e:
        logger.error(
            f"Ошибка при создании экземпляра Seq2SeqTrainer с конфигурацией '{config_name_or_path}': {e}",
            exc_info=True,
        )
        return f"Ошибка создания тренера: {e}"


async def start_training_command(jarvis: Any, args_str: str) -> str:
    trainer_id = args_str.strip()
    if not trainer_id:
        return "Использование: train_seq2seq <trainer_id>"
    if trainer_id not in active_trainers:
        return f"Тренер с ID '{trainer_id}' не найден."

    trainer = active_trainers[trainer_id]
    logger.info(f"Запуск обучения для тренера '{trainer_id}'...")

    # Запускаем в фоновом режиме, чтобы Jarvis не блокировался надолго
    async def _run_training():
        try:
            result = await trainer.train_async()
            msg = f"Обучение для тренера '{trainer_id}' завершено. Статус: {result.get('status', 'unknown')}, Best Val Loss: {result.get('best_val_loss', 'N/A'):.4f}"
            logger.info(msg)
            await jarvis.publish_event(
                "ml_training_task_completed", trainer_id=trainer_id, result=result
            )
            # Можно отправить сообщение пользователю через Jarvis, если есть такой механизм
        except Exception as e_train:
            logger.error(
                f"Ошибка в фоновой задаче обучения для '{trainer_id}': {e_train}",
                exc_info=True,
            )
            await jarvis.publish_event(
                "ml_training_task_error", trainer_id=trainer_id, error=str(e_train)
            )

    asyncio.create_task(_run_training())
    return f"Задача обучения для тренера '{trainer_id}' запущена в фоновом режиме. Следите за логами."


async def predict_command(jarvis: Any, args_str: str) -> str:
    parts = args_str.split(" ", 1)
    if len(parts) < 2:
        return "Использование: predict_seq2seq <trainer_id> <текст_для_предсказания>"

    trainer_id, text_to_predict = parts[0].strip(), parts[1].strip()
    if trainer_id not in active_trainers:
        return f"Тренер с ID '{trainer_id}' не найден."

    trainer = active_trainers[trainer_id]
    prediction = await trainer.predict_async(text_to_predict)
    return f"Предсказание от '{trainer_id}':\n{prediction}"


async def load_checkpoint_command(jarvis: Any, args_str: str) -> str:
    parts = args_str.split(" ", 1)
    if len(parts) < 2:
        return "Использование: load_seq2seq_checkpoint <trainer_id> <путь_к_чекпоинту>"
    trainer_id, checkpoint_path = parts[0].strip(), parts[1].strip()

    if trainer_id not in active_trainers:
        return f"Тренер с ID '{trainer_id}' не найден."

    trainer = active_trainers[trainer_id]
    try:
        epoch, val_loss = trainer._load_checkpoint(checkpoint_path)
        # После загрузки чекпоинта, сбрасываем счетчик эпох тренера
        trainer.current_epoch = epoch  # Или epoch + 1, если обучение продолжается
        trainer.global_step = 0  # Или восстанавливать global_step из чекпоинта
        return f"Чекпоинт '{checkpoint_path}' успешно загружен для тренера '{trainer_id}'. Эпоха: {epoch + 1}, Val Loss: {val_loss:.4f}."
    except Exception as e:
        return f"Ошибка загрузки чекпоинта для '{trainer_id}': {e}"


async def save_model_command(jarvis: Any, args_str: str) -> str:
    parts = args_str.split(" ", 1)
    trainer_id = parts[0].strip()
    save_path = parts[1].strip() if len(parts) > 1 else None

    if not trainer_id:
        return "Использование: save_seq2seq_model <trainer_id> [путь_для_сохранения]"
    if trainer_id not in active_trainers:
        return f"Тренер с ID '{trainer_id}' не найден."

    trainer = active_trainers[trainer_id]
    result_message = trainer.save_model_local(save_path)
    return result_message


async def list_trainers_command(jarvis: Any, args_str: str) -> str:
    global active_trainers
    if not active_trainers:
        return "Нет активных экземпляров ML тренеров."
    output = ["Активные ML тренеры (Seq2Seq):"]
    for trainer_id, trainer_instance in active_trainers.items():
        output.append(f"  - ID: {trainer_id}")
        output.append(f"    Модель: {trainer_instance.model_name}")
        output.append(f"    Устройство: {trainer_instance.device}")
        # Краткая информация о конфиге, чтобы не перегружать вывод
        brief_config = {
            "lr": trainer_instance.learning_rate,
            "epochs": trainer_instance.num_epochs,
            "batch_size": trainer_instance.batch_size,
            "max_source_len": trainer_instance.max_source_length,
            "max_target_len": trainer_instance.max_target_length,
        }
        output.append(f"    Краткий конфиг: {json.dumps(brief_config)}")
    return "\n".join(output)


commands_to_register: List[CommandInfo] = [
    CommandInfo(
        name="setup_seq2seq_trainer",
        description="Настраивает/пересоздает экземпляр Seq2Seq тренера.",
        category=CommandCategory.DEVELOPMENT,
        usage="setup_seq2seq_trainer <trainer_id_или_путь_к_json>",
        handler_name="setup_trainer_command",
    ),
    CommandInfo(
        name="train_seq2seq",
        description="Запускает обучение для Seq2Seq тренера (в фоне).",
        category=CommandCategory.DEVELOPMENT,
        usage="train_seq2seq <trainer_id>",
        handler_name="start_training_command",
    ),
    CommandInfo(
        name="predict_seq2seq",
        description="Генерирует текст с помощью Seq2Seq тренера.",
        category=CommandCategory.UTILITY,
        usage="predict_seq2seq <trainer_id> <входной_текст>",
        handler_name="predict_command",
    ),
    CommandInfo(
        name="load_seq2seq_checkpoint",
        description="Загружает чекпоинт для Seq2Seq тренера.",
        category=CommandCategory.DEVELOPMENT,
        usage="load_seq2seq_checkpoint <trainer_id> <путь_к_чекпоинту.pt>",
        handler_name="load_checkpoint_command",
    ),
    CommandInfo(
        name="save_seq2seq_model",
        description="Сохраняет модель и токенизатор тренера.",
        category=CommandCategory.DEVELOPMENT,
        usage="save_seq2seq_model <trainer_id> [путь_для_сохранения]",
        handler_name="save_model_command",
    ),
    CommandInfo(
        name="list_seq2seq_trainers",
        description="Список активных Seq2Seq тренеров.",
        category=CommandCategory.DEVELOPMENT,
        usage="list_seq2seq_trainers",
        handler_name="list_trainers_command",
    ),
]
