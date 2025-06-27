import ast  # Abstract Syntax Tree для анализа структуры кода
import asyncio
import datetime
import json
import os
import logging

logger = logging.getLogger(__name__)

import radon.complexity as radon_complexity  # Для цикломатической сложности
from radon.metrics import mi_visit  # Для метрик Холстеда и индекса обслуживаемости
from radon.raw import analyze as radon_raw_analyze  # Для SLOC, комментариев и т.д.

# Концептуально: интеграция с AI моделями для более глубокого анализа
# from some_ai_code_analysis_library import AICodeHelper


class AdvancedCodeAnalyzer:
    """
    Предоставляет расширенные методы для статического анализа исходного кода Python,
    включая метрики, структурный анализ, определение "запахов кода" и сложности.
    """

    def __init__(self, jarvis_instance, config=None):
        self.jarvis = jarvis_instance
        self.config = config if config else {}
        self.default_report_format = self.config.get(
            "default_report_format", "markdown"
        )
        self.complexity_threshold_warning = self.config.get(
            "complexity_threshold_warning", 10
        )
        self.complexity_threshold_critical = self.config.get(
            "complexity_threshold_critical", 20
        )
        self.max_function_lines = self.config.get("max_function_lines", 75)
        self.max_class_methods = self.config.get("max_class_methods", 20)
        self.ignore_dirs = self.config.get(
            "ignore_dirs",
            [".venv", "__pycache__", ".git", "node_modules", "build", "dist"],
        )
        self.cache_results = self.config.get("cache_results", True)
        self.cache_ttl_minutes = self.config.get("cache_ttl_minutes", 60)
        self.analysis_cache = {}  # Простой кэш в памяти: {filepath: (timestamp, data)}

        # Концептуально: Инициализация AI помощника
        # self.ai_helper = AICodeHelper(api_key=self.jarvis.memory.get("api_keys", {}).get("ai_code_analysis_key"))

    def _is_path_ignored(self, path_str, base_path):
        """Проверяет, следует ли игнорировать путь."""
        relative_path = os.path.relpath(path_str, base_path)
        parts = relative_path.split(os.sep)
        for part in parts:
            if part in self.ignore_dirs:
                return True
        return False

    def _get_cached_analysis(self, filepath, analysis_type):
        """Получает результат анализа из кэша, если он свежий."""
        if not self.cache_results:
            return None

        cache_key = (filepath, analysis_type)
        if cache_key in self.analysis_cache:
            timestamp, data = self.analysis_cache[cache_key]
            if (
                datetime.datetime.now() - timestamp
            ).total_seconds() / 60 < self.cache_ttl_minutes:
                return data
        return None

    def _cache_analysis_result(self, filepath, analysis_type, data):
        """Кэширует результат анализа."""
        if self.cache_results:
            self.analysis_cache[(filepath, analysis_type)] = (
                datetime.datetime.now(),
                data,
            )

    async def get_file_metrics_radon(self, filepath):
        """
        Вычисляет метрики файла с использованием Radon (SLOC, комментарии, пустые строки, индекс обслуживаемости).
        """
        cached_data = self._get_cached_analysis(filepath, "metrics_radon")
        if cached_data:
            return cached_data, None

        if not os.path.exists(filepath) or not os.path.isfile(filepath):
            return None, f"Ошибка: Файл не найден или не является файлом: {filepath}"
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source_code = f.read()

            raw_analysis = radon_raw_analyze(source_code)
            # ll_loc = raw_analysis.lloc # Логические строки кода
            # sloc = raw_analysis.sloc # Исходные строки кода (без пустых и комментариев)
            # comments = raw_analysis.comments # Строки комментариев
            # multi_line_comments = raw_analysis.multi # Строки многострочных комментариев
            # blank_lines = raw_analysis.blank # Пустые строки
            # single_comments = raw_analysis.single_comments # Однострочные комментарии

            mi_score = mi_visit(source_code, True)  # Индекс обслуживаемости

            metrics = {
                "filepath": filepath,
                "total_lines": raw_analysis.loc,  # Общее количество строк (как читает Python)
                "sloc": raw_analysis.sloc,
                "comment_lines": raw_analysis.comments + raw_analysis.multi,
                "blank_lines": raw_analysis.blank,
                "logical_lines": raw_analysis.lloc,
                "maintainability_index": round(mi_score, 2) if mi_score else "N/A",
            }
            self._cache_analysis_result(filepath, "metrics_radon", metrics)
            return metrics, None
        except Exception as e:
            return None, f"Ошибка чтения или обработки файла {filepath} с Radon: {e}"

    async def get_file_structure_ast(self, filepath):
        """
        Анализирует файл Python для определения функций, классов и импортов с использованием AST.
        Добавляет количество аргументов и базовую оценку длины.
        """
        cached_data = self._get_cached_analysis(filepath, "structure_ast")
        if cached_data:
            return cached_data, None

        if not os.path.exists(filepath) or not os.path.isfile(filepath):
            return None, f"Ошибка: Файл не найден: {filepath}"

        structure = {
            "functions": [],
            "classes": [],
            "imports": [],
            "filepath": filepath,
        }
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source_code = f.read()
            tree = ast.parse(source_code, filename=filepath)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    num_args = len(node.args.args)
                    lines_in_def = (
                        (node.end_lineno - node.lineno + 1) if node.end_lineno else 0
                    )
                    is_async = isinstance(node, ast.AsyncFunctionDef)
                    structure["functions"].append(
                        {
                            "name": node.name,
                            "async": is_async,
                            "lineno": node.lineno,
                            "args_count": num_args,
                            "docstring": ast.get_docstring(node) is not None,
                            "lines_in_def": lines_in_def,
                        }
                    )
                elif isinstance(node, ast.ClassDef):
                    methods = [
                        item.name
                        for item in node.body
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    ]
                    lines_in_def = (
                        (node.end_lineno - node.lineno + 1) if node.end_lineno else 0
                    )
                    structure["classes"].append(
                        {
                            "name": node.name,
                            "lineno": node.lineno,
                            "methods_count": len(methods),
                            "docstring": ast.get_docstring(node) is not None,
                            "lines_in_def": lines_in_def,
                        }
                    )
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        structure["imports"].append(
                            {"type": "import", "module": alias.name, "as": alias.asname}
                        )
                elif isinstance(node, ast.ImportFrom):
                    module_name = node.module if node.module else "." * node.level
                    for alias in node.names:
                        structure["imports"].append(
                            {
                                "type": "from-import",
                                "module": module_name,
                                "name": alias.name,
                                "as": alias.asname,
                            }
                        )
            self._cache_analysis_result(filepath, "structure_ast", structure)
            return structure, None
        except SyntaxError as e:
            return (
                None,
                f"Синтаксическая ошибка в файле {filepath} на строке {e.lineno}: {e.msg}",
            )
        except Exception as e:
            return None, f"Ошибка парсинга файла {filepath} с AST: {e}"

    async def get_cyclomatic_complexity(self, filepath):
        """Вычисляет цикломатическую сложность для функций и классов."""
        cached_data = self._get_cached_analysis(filepath, "cyclomatic_complexity")
        if cached_data:
            return cached_data, None

        if not os.path.exists(filepath) or not os.path.isfile(filepath):
            return None, f"Ошибка: Файл не найден: {filepath}"
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source_code = f.read()

            visitor = radon_complexity.ComplexityVisitor.from_code(source_code)
            results = {
                "filepath": filepath,
                "functions": [],  # {"name", "complexity", "lineno", "rank"}
                "classes": [],  # {"name", "complexity", "lineno", "rank", "methods_avg_complexity"}
                "average_complexity": 0,
            }
            complexities = []
            for item in visitor.functions:  # radon < 5.0.0 uses .functions
                rank = radon_complexity.rank(item.complexity)
                complexities.append(item.complexity)
                results["functions"].append(
                    {
                        "name": item.name,
                        "complexity": item.complexity,
                        "lineno": item.lineno,
                        "endline": item.endline,
                        "rank": rank,
                    }
                )
            # For radon >= 5.0.0, it might be visitor.blocks and check type
            # For classes, Radon calculates complexity for methods within them.
            # We can aggregate or list them.
            for item in visitor.classes:
                # Need to iterate through methods of this class if available in visitor output
                # This part might need adjustment based on Radon's exact output for classes
                # For now, let's assume item.real_complexity or similar if available
                # Or iterate functions and map them to classes
                rank = radon_complexity.rank(
                    item.real_complexity
                )  # Assuming real_complexity for class overall
                complexities.append(item.real_complexity)
                results["classes"].append(
                    {
                        "name": item.name,
                        "complexity": item.real_complexity,
                        "lineno": item.lineno,
                        "endline": item.endline,
                        "rank": rank,
                        "methods_avg_complexity": (
                            item.average_complexity
                            if hasattr(item, "average_complexity")
                            else "N/A"
                        ),
                    }
                )

            if complexities:
                results["average_complexity"] = round(
                    sum(complexities) / len(complexities), 2
                )

            self._cache_analysis_result(filepath, "cyclomatic_complexity", results)
            return results, None
        except Exception as e:
            return (
                None,
                f"Ошибка вычисления цикломатической сложности для {filepath}: {e}",
            )

    async def detect_code_smells(
        self, filepath, structure_data=None, complexity_data=None
    ):
        """Обнаруживает базовые "запахи кода"."""
        cached_data = self._get_cached_analysis(filepath, "code_smells")
        if cached_data:
            return cached_data, None

        if structure_data is None:
            structure_data, _ = await self.get_file_structure_ast(filepath)
        if complexity_data is None:
            complexity_data, _ = await self.get_cyclomatic_complexity(filepath)

        smells = {"filepath": filepath, "detected_smells": []}
        if not structure_data or not complexity_data:
            return (
                smells,
                "Не удалось получить данные структуры или сложности для анализа запахов.",
            )

        # 1. Длинные функции
        for func in structure_data.get("functions", []):
            if func["lines_in_def"] > self.max_function_lines:
                smells["detected_smells"].append(
                    {
                        "type": "Long Function",
                        "severity": "warning",
                        "message": f"Функция '{func['name']}' (строка {func['lineno']}) слишком длинная: {func['lines_in_def']} строк (макс: {self.max_function_lines}).",
                        "location": f"{filepath}:{func['lineno']}",
                    }
                )

        # 2. Функции с высокой цикломатической сложностью
        for func_comp in complexity_data.get("functions", []):
            if func_comp["complexity"] >= self.complexity_threshold_critical:
                severity = "critical"
            elif func_comp["complexity"] >= self.complexity_threshold_warning:
                severity = "warning"
            else:
                continue
            smells["detected_smells"].append(
                {
                    "type": "High Cyclomatic Complexity",
                    "severity": severity,
                    "message": f"Функция '{func_comp['name']}' (строка {func_comp['lineno']}) имеет высокую сложность: {func_comp['complexity']} (Ранг: {func_comp['rank']}).",
                    "location": f"{filepath}:{func_comp['lineno']}",
                }
            )

        # 3. Большие классы (по количеству методов)
        for cls in structure_data.get("classes", []):
            if cls["methods_count"] > self.max_class_methods:
                smells["detected_smells"].append(
                    {
                        "type": "Large Class",
                        "severity": "warning",
                        "message": f"Класс '{cls['name']}' (строка {cls['lineno']}) имеет слишком много методов: {cls['methods_count']} (макс: {self.max_class_methods}).",
                        "location": f"{filepath}:{cls['lineno']}",
                    }
                )

        # 4. Функции/классы без docstring (если это важно по конфигурации)
        if self.config.get("enforce_docstrings", False):
            for func in structure_data.get("functions", []):
                if not func["docstring"]:
                    smells["detected_smells"].append(
                        {
                            "type": "Missing Docstring",
                            "severity": "info",
                            "message": f"Функция '{func['name']}' (строка {func['lineno']}) не имеет docstring.",
                            "location": f"{filepath}:{func['lineno']}",
                        }
                    )
            for cls in structure_data.get("classes", []):
                if not cls["docstring"]:
                    smells["detected_smells"].append(
                        {
                            "type": "Missing Docstring",
                            "severity": "info",
                            "message": f"Класс '{cls['name']}' (строка {cls['lineno']}) не имеет docstring.",
                            "location": f"{filepath}:{cls['lineno']}",
                        }
                    )

        # Концептуально: AI для более тонких "запахов" или рекомендаций
        # if self.config.get("enable_ai_smell_detection", False):
        #     with open(filepath, 'r', encoding='utf-8') as f: source_code = f.read()
        #     ai_smells = await self.ai_helper.detect_advanced_smells(source_code, filepath)
        #     smells["detected_smells"].extend(ai_smells)

        self._cache_analysis_result(filepath, "code_smells", smells)
        return smells, None

    async def detect_magic_numbers(self, filepath):
        """Ищет в коде числовые литералы, не сохранённые в константы."""
        cached = self._get_cached_analysis(filepath, "magic_numbers")
        if cached:
            return cached, None

        if not os.path.isfile(filepath):
            return None, f"Файл не найден: {filepath}"
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=filepath)

            class MagicVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.stack = []
                    self.items = []

                def generic_visit(self, node):
                    self.stack.append(node)
                    super().generic_visit(node)
                    self.stack.pop()

                def visit_Constant(self, node):
                    if isinstance(node.value, (int, float, complex)):
                        skip = False
                        if self.stack:
                            parent = self.stack[-1]
                            if (
                                isinstance(parent, (ast.Assign, ast.AnnAssign))
                                and parent.value is node
                            ):
                                targets = (
                                    parent.targets
                                    if isinstance(parent, ast.Assign)
                                    else [parent.target]
                                )
                                if all(
                                    isinstance(t, ast.Name) and t.id.isupper()
                                    for t in targets
                                ):
                                    skip = True
                        if not skip:
                            self.items.append(
                                {"value": node.value, "lineno": node.lineno}
                            )

            visitor = MagicVisitor()
            visitor.visit(tree)
            self._cache_analysis_result(filepath, "magic_numbers", visitor.items)
            return visitor.items, None
        except SyntaxError as e:
            return None, f"Синтаксическая ошибка в {filepath}: {e}"

    async def detect_duplicate_code(self, filepath):
        """Находит дублирующиеся функции в файле."""
        cached = self._get_cached_analysis(filepath, "duplicate_code")
        if cached:
            return cached, None

        if not os.path.isfile(filepath):
            return None, f"Файл не найден: {filepath}"
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=filepath)
            func_map = {}
            duplicates = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    body_module = ast.Module(body=node.body, type_ignores=[])
                    body_dump = ast.dump(body_module, include_attributes=False)
                    key = body_dump
                    info = {"name": node.name, "lineno": node.lineno}
                    if key in func_map:
                        prev = func_map[key]
                        duplicates.append(
                            {
                                "function_1": prev["name"],
                                "lineno_1": prev["lineno"],
                                "function_2": info["name"],
                                "lineno_2": info["lineno"],
                            }
                        )
                    else:
                        func_map[key] = info

            self._cache_analysis_result(filepath, "duplicate_code", duplicates)
            return duplicates, None
        except SyntaxError as e:
            return None, f"Синтаксическая ошибка в {filepath}: {e}"

    async def detect_module_globals(self, filepath):
        """Ищет присваивания на уровне модуля."""
        cached = self._get_cached_analysis(filepath, "module_globals")
        if cached:
            return cached, None

        if not os.path.isfile(filepath):
            return None, f"Файл не найден: {filepath}"
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=filepath)
            globals_found = []
            for node in tree.body:
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = (
                        node.targets if isinstance(node, ast.Assign) else [node.target]
                    )
                    for t in targets:
                        if isinstance(t, ast.Name) and not t.id.isupper():
                            globals_found.append({"name": t.id, "lineno": t.lineno})

            self._cache_analysis_result(filepath, "module_globals", globals_found)
            return globals_found, None
        except SyntaxError as e:
            return None, f"Синтаксическая ошибка в {filepath}: {e}"

    async def run_pylint(self, filepath):
        """Запускает pylint и возвращает предупреждения."""
        cached = self._get_cached_analysis(filepath, "pylint")
        if cached:
            return cached, None

        if not os.path.isfile(filepath):
            return None, f"Файл не найден: {filepath}"

        try:
            process = await asyncio.create_subprocess_exec(
                "pylint",
                "--output-format=json",
                filepath,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0 and not stdout:
                return None, stderr.decode().strip()
            try:
                messages = json.loads(stdout.decode() or "[]")
            except json.JSONDecodeError as e:
                return None, f"Ошибка разбора вывода pylint: {e}"

            warnings = [
                {
                    "line": m.get("line"),
                    "symbol": m.get("symbol"),
                    "message": m.get("message"),
                    "message_id": m.get("message-id"),
                }
                for m in messages
                if m.get("type") == "warning"
            ]

            self._cache_analysis_result(filepath, "pylint", warnings)
            return warnings, None
        except FileNotFoundError:
            return None, "pylint not found"
        except Exception as e:
            return None, f"Ошибка запуска pylint: {e}"

    async def generate_comprehensive_report(self, path_str, report_format=None):
        """Генерирует комплексный отчет для файла или директории."""
        report_format = report_format if report_format else self.default_report_format

        abs_path = os.path.abspath(path_str)

        if os.path.isfile(abs_path):
            files_to_analyze = [abs_path]
            project_root = os.path.dirname(abs_path)
        elif os.path.isdir(abs_path):
            files_to_analyze = []
            project_root = abs_path
            for root, _, files in os.walk(abs_path):
                if self._is_path_ignored(root, abs_path):
                    continue
                for file in files:
                    if file.endswith(".py") and not self._is_path_ignored(
                        os.path.join(root, file), abs_path
                    ):
                        files_to_analyze.append(os.path.join(root, file))
        else:
            return (
                None,
                f"Ошибка: Путь не найден или не является файлом/директорией: {path_str}",
            )

        if not files_to_analyze:
            return {
                "summary": "Нет файлов Python для анализа по указанному пути или все игнорируются.",
                "files": [],
            }, None

        report_data = {
            "summary": {},
            "files": [],
            "timestamp": datetime.datetime.now().isoformat(),
            "project_root": project_root,
        }
        all_metrics_summary = {
            "sloc": 0,
            "comment_lines": 0,
            "blank_lines": 0,
            "maintainability_index_sum": 0,
            "analyzed_files_count": 0,
        }
        all_smells_count = 0
        critical_smells_count = 0
        total_magic_numbers = 0
        total_duplicate_functions = 0
        total_module_globals = 0
        total_pylint_warnings = 0

        for filepath in files_to_analyze:
            rel_path = os.path.relpath(filepath, project_root)

            metrics, err_m = await self.get_file_metrics_radon(filepath)
            if metrics:
                metrics["filepath"] = rel_path

            structure, err_s = await self.get_file_structure_ast(filepath)
            if structure:
                structure["filepath"] = rel_path

            complexity, err_c = await self.get_cyclomatic_complexity(filepath)
            if complexity:
                complexity["filepath"] = rel_path

            smells, err_sm = await self.detect_code_smells(
                filepath, structure, complexity
            )
            if smells:
                smells["filepath"] = rel_path
            magic_nums, _ = await self.detect_magic_numbers(filepath)
            duplicates, _ = await self.detect_duplicate_code(filepath)
            globals_defs, _ = await self.detect_module_globals(filepath)
            pylint_warns, _ = await self.run_pylint(filepath)

            file_report = {"filepath": rel_path}
            if metrics:
                file_report["metrics"] = metrics
            if structure:
                file_report["structure"] = structure
            if complexity:
                file_report["complexity"] = complexity
            if smells:
                file_report["smells"] = smells["detected_smells"]
                all_smells_count += len(smells["detected_smells"])
                critical_smells_count += sum(
                    1
                    for s in smells["detected_smells"]
                    if s.get("severity") == "critical"
                )
            if magic_nums:
                file_report["magic_numbers"] = magic_nums
                total_magic_numbers += len(magic_nums)
            if duplicates:
                file_report["duplicate_code"] = duplicates
                total_duplicate_functions += len(duplicates)
            if globals_defs:
                file_report["globals"] = globals_defs
                total_module_globals += len(globals_defs)
            if pylint_warns:
                file_report["pylint_warnings"] = pylint_warns
                total_pylint_warnings += len(pylint_warns)

            if metrics and metrics.get("maintainability_index") != "N/A":
                all_metrics_summary["maintainability_index_sum"] += metrics[
                    "maintainability_index"
                ]
                all_metrics_summary["analyzed_files_count"] += 1
                for key in ["sloc", "comment_lines", "blank_lines"]:
                    all_metrics_summary[key] += metrics.get(key, 0)

            report_data["files"].append(file_report)

        report_data["summary"]["total_files_processed"] = len(files_to_analyze)
        report_data["summary"]["total_sloc"] = all_metrics_summary["sloc"]
        report_data["summary"]["total_comment_lines"] = all_metrics_summary[
            "comment_lines"
        ]
        report_data["summary"]["total_blank_lines"] = all_metrics_summary["blank_lines"]
        if all_metrics_summary["analyzed_files_count"] > 0:
            avg_mi = (
                all_metrics_summary["maintainability_index_sum"]
                / all_metrics_summary["analyzed_files_count"]
            )
            report_data["summary"]["average_maintainability_index"] = round(avg_mi, 2)
        report_data["summary"]["total_code_smells_detected"] = all_smells_count
        report_data["summary"]["critical_code_smells"] = critical_smells_count
        report_data["summary"]["total_magic_numbers"] = total_magic_numbers
        report_data["summary"]["duplicate_functions"] = total_duplicate_functions
        report_data["summary"]["module_level_globals"] = total_module_globals
        report_data["summary"]["pylint_warnings"] = total_pylint_warnings

        # Концептуально: AI генерирует общее резюме по проекту
        # if self.config.get("enable_ai_project_summary", False) and report_data["files"]:
        #     project_summary_text = await self.ai_helper.generate_project_summary(report_data)
        #     report_data["summary"]["ai_project_overview"] = project_summary_text

        return report_data, None  # Форматирование в Markdown/HTML/JSON будет в команде


# --- Интерфейс модуля Jarvis ---


async def load_module(jarvis_instance, module_config=None):
    """Загружает модуль AdvancedCodeAnalyzer и делает его экземпляр доступным."""
    if (
        not hasattr(jarvis_instance, "adv_code_analyzer")
        or jarvis_instance.adv_code_analyzer is None
    ):
        # Передаем весь экземпляр Jarvis, чтобы анализатор мог получить доступ, например, к self.jarvis.memory
        jarvis_instance.adv_code_analyzer = AdvancedCodeAnalyzer(
            jarvis_instance, module_config
        )
        print("Модуль Advanced Code Analyzer загружен.")
    else:
        # Возможно, обновить конфигурацию, если модуль уже загружен
        jarvis_instance.adv_code_analyzer.config = (
            module_config if module_config else {}
        )
        print(
            "Модуль Advanced Code Analyzer уже был загружен. Конфигурация обновлена (если предоставлена)."
        )


async def close_module(jarvis_instance):
    """Очистка ресурсов, если это необходимо в будущем."""
    if hasattr(jarvis_instance, "adv_code_analyzer"):
        jarvis_instance.adv_code_analyzer = None  # Очистка кэша и т.д. может быть здесь
        print("Модуль Advanced Code Analyzer выгружен.")


def _resolve_path(jarvis_instance, relative_path):
    """Разрешает путь относительно текущей директории проекта Jarvis."""
    if os.path.isabs(relative_path):
        return relative_path
    # Убедимся, что current_project_path существует и является директорией
    project_path = jarvis_instance.current_project_path
    if not project_path or not os.path.isdir(project_path):
        project_path = os.getcwd()  # Запасной вариант
        # print(f"Предупреждение: current_project_path не установлен или недействителен, используется CWD: {project_path}")
    return os.path.join(project_path, relative_path)


def _format_report(report_data, format_type="markdown"):
    """Форматирует данные отчета в указанный формат."""
    if format_type == "json":
        return json.dumps(report_data, indent=2, ensure_ascii=False)

    # Базовое форматирование в Markdown
    md = f"# Отчет анализа кода ({report_data.get('timestamp')})\n\n"
    summary = report_data.get("summary", {})
    md += "## Общее резюме\n"
    for key, value in summary.items():
        md += f"- **{key.replace('_', ' ').capitalize()}**: {value}\n"

    if "ai_project_overview" in summary:  # Концептуально
        md += f"\n### Обзор проекта (AI):\n{summary['ai_project_overview']}\n"

    for file_report in report_data.get("files", []):
        relative_filepath = file_report.get("filepath")
        md += f"\n## Файл: `{relative_filepath}`\n"

        if "metrics" in file_report:
            md += "### Метрики:\n"
            for k, v in file_report["metrics"].items():
                if k != "filepath":
                    md += f"- {k.replace('_', ' ').capitalize()}: {v}\n"

        if "complexity" in file_report and file_report["complexity"].get("functions"):
            md += "### Цикломатическая сложность (Функции):\n"
            for func in file_report["complexity"]["functions"]:
                md += f"- `{func['name']}` (строка {func['lineno']}): **{func['complexity']}** (Ранг: {func['rank']})\n"

        if "smells" in file_report and file_report["smells"]:
            md += '### Обнаруженные "запахи кода":\n'
            for smell in file_report["smells"]:
                md += f"- **[{smell['severity'].upper()}]** {smell['type']} (строка {smell['location'].split(':')[-1]}): {smell['message']}\n"
        if "magic_numbers" in file_report and file_report["magic_numbers"]:
            md += "### Найденные magic numbers:\n"
            for item in file_report["magic_numbers"]:
                md += f"- {item['value']} (строка {item['lineno']})\n"
        if "duplicate_code" in file_report and file_report["duplicate_code"]:
            md += "### Дублирующиеся функции:\n"
            for dup in file_report["duplicate_code"]:
                md += f"- `{dup['function_1']}`:{dup['lineno_1']} дублирует `{dup['function_2']}`:{dup['lineno_2']}\n"
        if "globals" in file_report and file_report["globals"]:
            md += "### Глобальные переменные:\n"
            for g in file_report["globals"]:
                md += f"- `{g['name']}` (строка {g['lineno']})\n"
        # Можно добавить вывод структуры (импорты, классы, функции) при необходимости
    return md


async def analyze_code_report_cmd(jarvis_instance, args_string: str):
    """
    Генерирует комплексный отчет для файла или директории.
    Использование: analyze_report <путь_к_файлу_или_директории> [--format=json|md] [--output=имя_файла_отчета]
    """
    parts = args_string.split()
    if not parts:
        return "Использование: analyze_report <путь> [--format=json|md] [--output=имя_файла]"

    path_to_analyze = parts[0]
    report_format = jarvis_instance.adv_code_analyzer.default_report_format
    output_filename = None

    for part in parts[1:]:
        if part.startswith("--format="):
            report_format = part.split("=", 1)[1].lower()
            if report_format not in [
                "json",
                "markdown",
                "html",
            ]:  # HTML пока не реализован
                return f"Ошибка: Неподдерживаемый формат отчета '{report_format}'. Доступные: json, markdown."
        elif part.startswith("--output="):
            output_filename = part.split("=", 1)[1]

    resolved_path = _resolve_path(jarvis_instance, path_to_analyze)
    analyzer = jarvis_instance.adv_code_analyzer
    if not analyzer:
        return "Ошибка: Модуль Advanced Code Analyzer не загружен."

    report_data, error = await analyzer.generate_comprehensive_report(resolved_path)
    if error:
        return f"Ошибка генерации отчета: {error}"
    if not report_data:
        return "Не удалось сгенерировать данные отчета."

    formatted_output = _format_report(report_data, report_format)

    if output_filename:
        resolved_output_filename = _resolve_path(jarvis_instance, output_filename)
        try:
            with open(resolved_output_filename, "w", encoding="utf-8") as f:
                f.write(formatted_output)
            return f"Отчет сохранен в: {resolved_output_filename}"
        except Exception as e:
            return f"Ошибка сохранения отчета в файл {resolved_output_filename}: {e}\n\n{formatted_output[:1000]}"  # Показать часть отчета
    else:
        return formatted_output  # Вывести в консоль (может быть очень длинным)


async def analyze_py_complexity_cmd(jarvis_instance, args_string: str):
    """Анализирует файл Python на цикломатическую сложность. Использование: analyze_complexity <filepath>"""
    if not args_string:
        return "Использование: analyze_complexity <filepath>"

    filepath = _resolve_path(jarvis_instance, args_string.strip())
    analyzer = jarvis_instance.adv_code_analyzer
    if not analyzer:
        return "Ошибка: Модуль Advanced Code Analyzer не загружен."

    complexity_data, error = await analyzer.get_cyclomatic_complexity(filepath)
    if error:
        return error

    output = f"--- Цикломатическая сложность для {filepath} ---\n"
    if complexity_data.get("functions") or complexity_data.get("classes"):
        output += f"Средняя сложность по файлу: {complexity_data.get('average_complexity', 'N/A')}\n\n"
        for func in complexity_data.get("functions", []):
            output += (
                f"Функция: `{func['name']}` (строки {func['lineno']}-{func['endline']})\n"
                f"  Сложность: {func['complexity']} (Ранг: {func['rank']})\n"
            )
        for cls in complexity_data.get(
            "classes", []
        ):  # Если Radon предоставляет агрегированную сложность класса
            output += (
                f"Класс: `{cls['name']}` (строки {cls['lineno']}-{cls['endline']})\n"
                f"  Общая сложность: {cls['complexity']} (Ранг: {cls['rank']})\n"
                f"  Средняя сложность методов: {cls.get('methods_avg_complexity', 'N/A')}\n"
            )
    else:
        output += "Не найдено функций или классов для анализа сложности."
    output += "--------------------------------------------------"
    return output


async def analyze_py_smells_cmd(jarvis_instance, args_string: str):
    """Обнаруживает 'запахи кода' в файле Python. Использование: analyze_smells <filepath>"""
    if not args_string:
        return "Использование: analyze_smells <filepath>"

    filepath = _resolve_path(jarvis_instance, args_string.strip())
    analyzer = jarvis_instance.adv_code_analyzer
    if not analyzer:
        return "Ошибка: Модуль Advanced Code Analyzer не загружен."

    smells_data, error = await analyzer.detect_code_smells(filepath)
    if error:
        return error

    output = f'--- "Запахи кода" для {filepath} ---\n'
    if smells_data and smells_data["detected_smells"]:
        for smell in smells_data["detected_smells"]:
            output += (
                f"[{smell['severity'].upper()}] {smell['type']} на {smell['location']}\n"
                f"  Сообщение: {smell['message']}\n"
            )
    else:
        output += 'Не обнаружено "запахов кода" (согласно текущим правилам).'
    output += "--------------------------------------------------"
    return output


# Словарь команд для регистрации в Jarvis
commands = {
    "analyze_report": analyze_code_report_cmd,
    "analyze_complexity": analyze_py_complexity_cmd,  # Новая команда
    "analyze_smells": analyze_py_smells_cmd,  # Новая команда
    # Старые команды можно либо удалить, либо адаптировать, либо оставить для более простого вывода
    # Например, analyze_py_metrics может использовать get_file_metrics_radon
}


async def health_check() -> bool:
    """Quickly parse a simple snippet to verify analyzer basics."""
    try:
        ast.parse("pass")
        return True
    except Exception as exc:  # pragma: no cover - best effort logging
        logger.warning("Analyzer health check failed: %s", exc)
        return False
