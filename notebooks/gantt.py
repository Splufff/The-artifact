import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from datetime import datetime, timedelta
import numpy as np
import re
from collections import defaultdict, deque
import os
from IPython.display import display, HTML
import ipywidgets as widgets
from io import StringIO, BytesIO
from matplotlib.backends.backend_pdf import PdfPages

# ========== ФУНКЦИЯ ДЛЯ ЗАГРУЗКИ ФАЙЛА В NOTEBOOK ==========

def upload_file_and_create_gantt():
    """
    ЗАГРУЗКА ФАЙЛА ПРЯМО В NOTEBOOK - ПОЯВИТСЯ КНОПКА ВЫБОРА ФАЙЛА
    """
    # Создаем виджет загрузки файла
    uploader = widgets.FileUpload(
        accept='.csv,.xlsx',  # принимаем CSV и Excel
        multiple=False,       # только один файл
        description='📁 ВЫБЕРИ ФАЙЛ',
        style={'description_width': 'initial'}
    )
    
    # Настройки
    project_name = widgets.Text(
        value='Мой проект',
        placeholder='Введите название проекта',
        description='Название:',
        style={'description_width': 'initial'}
    )
    
    # Кнопка создания
    create_btn = widgets.Button(
        description='🚀 ПОСТРОИТЬ ДИАГРАММУ',
        button_style='success',
        icon='rocket',
        layout=widgets.Layout(width='300px', height='40px')
    )
    
    output = widgets.Output()
    
    def on_create_click(b):
        with output:
            output.clear_output()
            
            if not uploader.value:
                print("❌ СНАЧАЛА ВЫБЕРИ ФАЙЛ!")
                return
            
            try:
                # Берем загруженный файл
                uploaded_file = list(uploader.value.values())[0]
                filename = uploaded_file['name']
                content = uploaded_file['content']
                
                print(f"📁 ОБРАБАТЫВАЮ ФАЙЛ: {filename}")
                print("=" * 50)
                
                # Загружаем данные в зависимости от типа файла
                if filename.endswith('.csv'):
                    df = pd.read_csv(BytesIO(content))
                elif filename.endswith('.xlsx'):
                    df = pd.read_excel(BytesIO(content))
                else:
                    print("❌ НЕПОДДЕРЖИВАЕМЫЙ ФОРМАТ ФАЙЛА")
                    return
                
                print(f"✅ ФАЙЛ ЗАГРУЖЕН! ЗАДАЧ: {len(df)}")
                print("\n📊 СОДЕРЖИМОЕ ФАЙЛА:")
                print(df)
                
                # Создаем папку для результатов
                os.makedirs('../figs', exist_ok=True)
                
                # Генерируем имя для сохранения
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_name = f"gantt_{timestamp}"
                save_path = f'../figs/{save_name}.png'
                pdf_path = f'../figs/{save_name}.pdf'
                
                print(f"\n🎨 СОЗДАЮ ДИАГРАММУ...")
                
                # Используем существующую функцию create_gantt_chart
                result_df = create_gantt_chart(
                    df, 
                    save_path=save_path, 
                    save_pdf=True
                )
                
                if result_df is not None:
                    print("\n✅ ДИАГРАММА УСПЕШНО СОЗДАНА!")
                    print(f"📊 PNG: {save_path}")
                    print(f"📄 PDF: {pdf_path}")
                    
                    # Показываем кнопку для скачивания PDF
                    try:
                        with open(pdf_path, "rb") as f:
                            pdf_data = f.read()
                        
                        b64_pdf = base64.b64encode(pdf_data).decode()
                        download_html = f'''
                        <a href="data:application/pdf;base64,{b64_pdf}" 
                           download="{save_name}.pdf"
                           style="background-color: #4CAF50; color: white; padding: 10px 20px; 
                                  text-decoration: none; border-radius: 5px; display: inline-block;
                                  font-weight: bold; margin: 10px 0;">
                           📥 СКАЧАТЬ PDF ОТЧЕТ
                        </a>
                        '''
                        display(HTML(download_html))
                    except:
                        print("💡 PDF сохранен в папке ../figs/")
                
            except Exception as e:
                print(f"❌ ОШИБКА: {e}")
                import traceback
                print(traceback.format_exc())
    
    create_btn.on_click(on_create_click)
    
    # Показываем интерфейс
    display(HTML("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 20px; border-radius: 10px; color: white; text-align: center;">
        <h1>📊 ДИАГРАММЫ ГАНТА</h1>
        <p>Загрузи файл с данными проекта и получи диаграмму с критическим путем</p>
    </div>
    """))
    
    display(HTML("<h3>📁 ЗАГРУЗИ ФАЙЛ ПРОЕКТА:</h3>"))
    display(uploader)
    display(project_name)
    display(create_btn)
    display(output)

# ========== БЫСТРЫЙ СТАРТ ==========

def quick_upload():
    """
    ПРОСТО ЗАПУСТИ ЭТУ ФУНКЦИЮ И ВЫБЕРИ ФАЙЛ
    """
    print("🚀 БЫСТРЫЙ СТАРТ - ЗАГРУЗКА ФАЙЛА")
    print("=" * 50)
    print("📋 Поддерживаемые форматы: CSV, Excel")
    print("📋 Пример структуры CSV файла:")
    print("""
Task,Duration,Dependencies,Workers
A,5,,2
B,3,A,1
C,4,A,3
D,2,B,2
    """)
    print()
    
    upload_file_and_create_gantt()

# ========== ТВОЙ СУЩЕСТВУЮЩИЙ КОД (БЕЗ ИЗМЕНЕНИЙ) ==========

class ProjectStructureAnalyzer:
    """Анализатор логической структуры проекта для определения зависимостей"""
    
    @staticmethod
    def detect_dependency_columns(df, task_column):
        """Определяет колонки зависимостей по логике проекта"""
        print("🔍 АНАЛИЗ ЛОГИЧЕСКОЙ СТРУКТУРЫ ПРОЕКТА...")
        
        dependency_candidates = {
            'predecessors': None,
            'successors': None
        }
        
        # 1. Анализ по формату данных в колонках
        for col in df.columns:
            if col == task_column:
                continue
                
            col_data = df[col].dropna()
            if len(col_data) == 0:
                continue
            
            # Анализируем содержимое колонки
            dependency_score = ProjectStructureAnalyzer.analyze_column_dependency_pattern(col_data, df[task_column])
            
            if dependency_score > 0.7:  # Высокая вероятность что это зависимости
                if dependency_score > dependency_candidates.get('predecessors_score', 0):
                    dependency_candidates['predecessors'] = col
                    dependency_candidates['predecessors_score'] = dependency_score
        
        print(f"✅ Обнаружены зависимости: {dependency_candidates['predecessors']}")
        return dependency_candidates
    
    @staticmethod
    def analyze_column_dependency_pattern(column_data, task_names):
        """Анализирует паттерны данных в колонке для определения зависимостей"""
        score = 0
        total_values = len(column_data)
        task_name_set = set(task_names)
        
        if total_values == 0:
            return 0
        
        # Признаки колонки с зависимостями
        patterns_found = 0
        
        for value in column_data.head(20):  # Анализируем первые 20 значений
            value_str = str(value)
            
            # 1. Проверка на пустые значения (первые задачи могут не иметь зависимостей)
            if pd.isna(value) or value_str in ['', 'nan', 'None']:
                patterns_found += 0.2  # Слабый признак
                continue
            
            # 2. Проверка на наличие названий задач из колонки задач
            if any(task in value_str for task in task_name_set if len(str(task)) > 2):
                patterns_found += 1.0  # Сильный признак
            
            # 3. Проверка на разделители (запятые, точки с запятой)
            if re.search(r'[,;]', value_str):
                patterns_found += 0.8  # Средний признак
            
            # 4. Проверка на числовые коды (ID задач)
            if re.match(r'^[A-Za-z]?\d+([,;]\s*[A-Za-z]?\d+)*$', value_str.strip()):
                patterns_found += 0.6  # Средний признак
        
        score = patterns_found / min(20, total_values)
        return score

class SmartFieldMapper:
    """Умный маппер полей с анализом логики проекта"""
    
    FIELD_ALIASES = {
        'Task': ['task', 'задача', 'activity', 'work', 'name', 'название', 'id', 'код'],
        'Duration': ['duration', 'длительность', 'days', 'дней', 'time', 'продолжительность'],
        'Start': ['start', 'start_date', 'начало', 'дата начала', 'startdate'],
        'Workers': ['workers', 'workforce', 'трудозатраты', 'ресурсы', 'labor', 'рабочая сила', 'team'],
        'Dependencies': ['dependencies', 'predecessors', 'зависимости', 'предшественники', 'dep', 'pred']
    }
    
    @staticmethod
    def detect_fields_with_logic(df):
        """Определяет поля с учетом логики проекта"""
        print("🎯 УМНОЕ ОПРЕДЕЛЕНИЕ СТРУКТУРЫ ПРОЕКТА...")
        
        # 1. Сначала находим колонку с задачами по названию
        task_column = SmartFieldMapper._find_task_column(df)
        if not task_column:
            return None
        
        print(f"   📝 Колонка задач: '{task_column}'")
        
        # 2. Анализируем логику проекта для определения зависимостей
        analyzer = ProjectStructureAnalyzer()
        dependencies = analyzer.detect_dependency_columns(df, task_column)
        
        # 3. Находим остальные поля по названиям
        other_fields = SmartFieldMapper._find_other_fields(df, task_column)
        
        # 4. Объединяем результаты
        field_mapping = {
            'Task': task_column,
            **other_fields
        }
        
        # 5. Если зависимости найдены анализатором, добавляем их
        if dependencies['predecessors']:
            field_mapping['Dependencies'] = dependencies['predecessors']
        
        # 6. Валидируем маппинг
        return SmartFieldMapper._validate_mapping(df, field_mapping)
    
    @staticmethod
    def _find_task_column(df):
        """Находит колонку с названиями задач"""
        for col in df.columns:
            col_lower = str(col).lower()
            
            # Проверяем по названию
            for alias in SmartFieldMapper.FIELD_ALIASES['Task']:
                if alias in col_lower or col_lower in alias:
                    return col
            
            # Проверяем по содержимому (уникальные строковые значения)
            if SmartFieldMapper._looks_like_task_column(df[col]):
                return col
        
        # Если не нашли по названию, берем первую нечисловую колонку
        for col in df.columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                return col
        
        return df.columns[0]  # Последний вариант - первая колонка
    
    @staticmethod
    def _looks_like_task_column(column):
        """Определяет похожа ли колонка на колонку с задачами"""
        if len(column) == 0:
            return False
        
        unique_ratio = column.nunique() / len(column)
        sample_values = column.dropna().head(5)
        
        # Признаки колонки с задачами:
        # - Высокий процент уникальных значений
        # - Строковые значения
        # - Не даты и не числа
        
        if unique_ratio > 0.8 and not pd.api.types.is_numeric_dtype(column):
            return True
        
        return False
    
    @staticmethod
    def _find_other_fields(df, task_column):
        """Находит остальные поля по названиям"""
        other_fields = {}
        
        for field_type, aliases in SmartFieldMapper.FIELD_ALIASES.items():
            if field_type == 'Task':
                continue
                
            for col in df.columns:
                if col == task_column:
                    continue
                    
                col_lower = str(col).lower()
                for alias in aliases:
                    if alias in col_lower or col_lower in alias:
                        other_fields[field_type] = col
                        break
                if field_type in other_fields:
                    break
        
        return other_fields
    
    @staticmethod
    def _validate_mapping(df, field_mapping):
        """Валидирует правильность маппинга"""
        # Проверяем что колонка задач существует и имеет данные
        if field_mapping['Task'] not in df.columns:
            return None
        
        task_col = field_mapping['Task']
        if df[task_col].isna().all() or len(df[task_col].dropna()) == 0:
            return None
        
        # Проверяем зависимости если они найдены
        if field_mapping.get('Dependencies') and field_mapping['Dependencies'] not in df.columns:
            field_mapping['Dependencies'] = None
        
        return field_mapping

class FieldMapper:
    """Маппер полей"""
    @staticmethod
    def map_dataframe(df, field_mapping):
        rename_dict = {}
        inverse_mapping = {}
        
        for standard_field, user_field in field_mapping.items():
            if user_field and user_field in df.columns:
                rename_dict[user_field] = standard_field
                inverse_mapping[standard_field] = user_field
        
        df_mapped = df.rename(columns=rename_dict)
        return df_mapped, inverse_mapping

def validate_and_map_data(df):
    """Продвинутая валидация с анализом логики проекта"""
    print("=" * 60)
    print("🔍 АВТОМАТИЧЕСКИЙ АНАЛИЗ СТРУКТУРЫ ПРОЕКТА")
    print("=" * 60)
    
    # 1. Умное определение полей с анализом логики
    field_mapping = SmartFieldMapper.detect_fields_with_logic(df)
    
    if not field_mapping:
        print("❌ Не удалось определить структуру проекта")
        return False, ["Не удалось автоматически определить структуру данных"], df, {}
    
    print("✅ СТРУКТУРА ПРОЕКТА ОПРЕДЕЛЕНА:")
    for field_type, user_field in field_mapping.items():
        if user_field:
            print(f"   • {field_type.upper()}: '{user_field}'")
    
    # 2. Маппим DataFrame
    df_mapped, inverse_mapping = FieldMapper.map_dataframe(df, field_mapping)
    
    # 3. Если колонка Dependencies не найдена, создаем пустую
    if 'Dependencies' not in df_mapped.columns:
        df_mapped['Dependencies'] = ''
        print("   • DEPENDENCIES: создана пустая колонка")
    
    # 4. Стандартная валидация данных
    is_valid, errors, df_validated = standard_data_validation(df_mapped)
    
    return is_valid, errors, df_validated, inverse_mapping

def topological_sort(df):
    """Топологическая сортировка задач по зависимостям"""
    graph = {}
    for _, task in df.iterrows():
        graph[task['Task']] = parse_dependencies(task.get('Dependencies', ''))
    
    visited = set()
    result = []
    
    def visit(task):
        if task in visited:
            return
        visited.add(task)
        for dep in graph.get(task, []):
            if dep in graph:  # Проверяем что зависимость существует
                visit(dep)
        result.append(task)
    
    # Начинаем с задач без зависимостей
    for task in graph:
        if not graph[task]:
            visit(task)
    
    # Добавляем остальные задачи
    for task in graph:
        if task not in visited:
            visit(task)
    
    return result

def calculate_realistic_dates(df):
    """Правильно рассчитывает даты выполнения задач с учетом зависимостей"""
    df = df.copy()
    
    # Начинаем с текущей даты
    current_date = pd.Timestamp.now().normalize()
    
    # Словарь для хранения дат окончания задач
    task_end_dates = {}
    
    # Топологическая сортировка для правильного порядка
    sorted_tasks = topological_sort(df)
    
    for task_name in sorted_tasks:
        task_idx = df[df['Task'] == task_name].index[0]
        dependencies = parse_dependencies(df.loc[task_idx, 'Dependencies'])
        duration = df.loc[task_idx, 'Duration']
        
        if not dependencies:
            # Задача без зависимостей - начинаем с текущей даты
            start_date = current_date
        else:
            # Находим максимальную дату окончания среди зависимостей
            max_end_date = current_date
            for dep in dependencies:
                if dep in task_end_dates:
                    dep_end = task_end_dates[dep]
                    if dep_end > max_end_date:
                        max_end_date = dep_end
            start_date = max_end_date
        
        end_date = start_date + pd.Timedelta(days=duration)
        
        # Сохраняем даты
        df.loc[task_idx, 'Start'] = start_date
        df.loc[task_idx, 'End'] = end_date
        task_end_dates[task_name] = end_date
    
    return df

def standard_data_validation(df):
    """Стандартная валидация данных"""
    errors = []
    warnings = []
    
    print("🔍 ВАЛИДАЦИЯ ДАННЫХ...")
    print("=" * 50)
    
    # 1. Проверка структуры файла
    if df.empty:
        errors.append("Файл пустой")
        return False, errors, df
    
    # 2. Проверка обязательных колонок
    required_columns = ['Task', 'Duration']
    for col in required_columns:
        if col not in df.columns:
            errors.append(f"Отсутствует обязательная колонка: '{col}'")
    
    if errors:
        return False, errors, df
    
    # 3. Проверка уникальности названий задач
    duplicate_tasks = df[df.duplicated('Task', keep=False)]
    if not duplicate_tasks.empty:
        duplicate_names = duplicate_tasks['Task'].unique()
        errors.append(f"Дублирующиеся названия задач: {', '.join(duplicate_names)}")
    
    # 4. Проверка длительностей
    try:
        df['Duration'] = pd.to_numeric(df['Duration'], errors='coerce')
        invalid_durations = df['Duration'].isna() | (df['Duration'] <= 0)
        if invalid_durations.any():
            invalid_tasks = df[invalid_durations]['Task'].tolist()
            errors.append(f"Некорректные длительности: {', '.join(invalid_tasks)}")
    except Exception as e:
        errors.append(f"Ошибка в колонке 'Duration': {e}")
    
    # 5. Проверка дат (если есть)
    if 'Start' in df.columns:
        try:
            df['Start'] = pd.to_datetime(df['Start'], errors='coerce', format='%Y-%m-%d')
            invalid_dates = df['Start'].isna()
            if invalid_dates.any():
                invalid_tasks = df[invalid_dates]['Task'].tolist()
                warnings.append(f"Некорректные даты начала: {', '.join(invalid_tasks)}")
        except Exception as e:
            warnings.append(f"Ошибка преобразования дат: {e}")
    else:
        df['Start'] = pd.Timestamp.now().normalize()
    
    # 6. ПРОВЕРКА ЗАВИСИМОСТЕЙ
    if 'Dependencies' in df.columns:
        all_tasks = set(df['Task'])
        
        # Проверка формата зависимостей
        for _, task in df.iterrows():
            deps_str = str(task['Dependencies']) if pd.notna(task['Dependencies']) else ''
            
            # Проверка на специальные символы
            if re.search(r'[{}[\]()]', deps_str):
                errors.append(f"Некорректные символы в зависимостях задачи '{task['Task']}': {deps_str}")
            
            # Проверка на пустые элементы в списке
            if ',,' in deps_str or deps_str.startswith(',') or deps_str.endswith(','):
                errors.append(f"Пустые элементы в зависимостях задачи '{task['Task']}': {deps_str}")
        
        # Проверка существования зависимых задач
        missing_deps = []
        for _, task in df.iterrows():
            deps = parse_dependencies(task['Dependencies'])
            for dep in deps:
                if dep and dep not in all_tasks:
                    missing_deps.append(f"'{task['Task']}' → '{dep}'")
        
        if missing_deps:
            errors.append(f"Несуществующие зависимости: {', '.join(missing_deps)}")
        
        # Проверка циклических зависимостей
        cycles = find_cyclic_dependencies(df)
        if cycles:
            for cycle in cycles:
                errors.append(f"Циклическая зависимость: {cycle}")
        
        # Проверка самозависимостей
        self_deps = []
        for _, task in df.iterrows():
            deps = parse_dependencies(task['Dependencies'])
            if task['Task'] in deps:
                self_deps.append(f"'{task['Task']}'")
        
        if self_deps:
            errors.append(f"Самозависимости: {', '.join(self_deps)}")
    
    # 7. Проверка числовых колонок
    numeric_columns = ['Workers', 'Priority', 'Cost']
    for col in numeric_columns:
        if col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                invalid_values = df[col].isna()
                if invalid_values.any():
                    invalid_tasks = df[invalid_values]['Task'].tolist()
                    warnings.append(f"Некорректные значения в '{col}': {', '.join(invalid_tasks)}")
                
                # Проверка отрицательных значений
                if col in ['Workers', 'Duration']:
                    negative_values = df[df[col] < 0]
                    if not negative_values.empty:
                        tasks_list = negative_values['Task'].tolist()
                        errors.append(f"Отрицательные значения в '{col}': {', '.join(tasks_list)}")
            except Exception as e:
                warnings.append(f"Ошибка в колонке '{col}': {e}")
    
    # 8. Проверка формата названий задач
    invalid_names = []
    for task_name in df['Task']:
        if not isinstance(task_name, str) or not task_name.strip():
            invalid_names.append(f"'{task_name}'")
        elif len(task_name.strip()) == 0:
            invalid_names.append("пустое название")
    
    if invalid_names:
        errors.append(f"Некорректные названия задач: {', '.join(invalid_names)}")
    
    # ВЫВОД РЕЗУЛЬТАТОВ ВАЛИДАЦИИ
    if warnings:
        print("⚠️  ПРЕДУПРЕЖДЕНИЯ:")
        for warning in warnings:
            print(f"   • {warning}")
    
    if errors:
        print("❌ ОШИБКИ:")
        for error in errors:
            print(f"   🚫 {error}")
        return False, errors, df
    
    print("✅ ВАЛИДАЦИЯ ПРОЙДЕНА УСПЕШНО!")
    print(f"   • Задачи: {len(df)}")
    print(f"   • Колонки: {', '.join(df.columns)}")
    print(f"   • Период: {df['Start'].min().strftime('%d.%m.%Y')} - {df['End'].max().strftime('%d.%m.%Y') if 'End' in df.columns else 'N/A'}")
    
    return True, errors, df

def parse_dependencies(deps_str):
    """Парсит зависимости из строки с обработкой ошибок"""
    if pd.isna(deps_str) or deps_str == '' or deps_str == 'nan':
        return []
    
    try:
        clean_str = str(deps_str).replace('"', '').replace("'", "").strip()
        if not clean_str:
            return []
        
        deps = [dep.strip() for dep in clean_str.split(',')]
        return [dep for dep in deps if dep]
    except Exception:
        return []

def find_cyclic_dependencies(df):
    """Находит все циклические зависимости"""
    graph = {}
    for _, task in df.iterrows():
        graph[task['Task']] = parse_dependencies(task['Dependencies'])
    
    def dfs(task, visited, path):
        if task in visited:
            if task in path:
                cycle_start = path.index(task)
                return path[cycle_start:]
            return None
        
        visited.add(task)
        path.append(task)
        
        for neighbor in graph.get(task, []):
            if neighbor in graph:
                cycle = dfs(neighbor, visited.copy(), path.copy())
                if cycle:
                    return cycle
        
        return None
    
    all_cycles = []
    visited_global = set()
    
    for task in graph.keys():
        if task not in visited_global:
            cycle = dfs(task, set(), [])
            if cycle:
                cycle_str = ' → '.join(cycle + [cycle[0]])
                if cycle_str not in all_cycles:
                    all_cycles.append(cycle_str)
                visited_global.update(cycle)
    
    return all_cycles

def build_dependency_graph(df):
    """Строит полный граф зависимостей"""
    graph = {}
    for _, task in df.iterrows():
        graph[task['Task']] = {
            'dependencies': parse_dependencies(task['Dependencies']),
            'successors': []
        }
    
    # Заполняем обратные связи
    for task_name, task_data in graph.items():
        for dep in task_data['dependencies']:
            if dep in graph:
                graph[dep]['successors'].append(task_name)
    
    return graph

def calculate_critical_path_with_dependencies(df):
    """ПРАВИЛЬНЫЙ расчет критического пути с учетом зависимостей"""
    
    df = df.copy()
    df['Is_Critical'] = False
    
    # Создаем словарь задач
    tasks_dict = {}
    for _, task in df.iterrows():
        tasks_dict[task['Task']] = {
            'duration': task['Duration'],
            'dependencies': parse_dependencies(task.get('Dependencies', '')),
            'early_start': None,
            'early_finish': None,
            'successors': []
        }
    
    # Заполняем последователей
    for task_name, task_data in tasks_dict.items():
        for dep in task_data['dependencies']:
            if dep in tasks_dict:
                tasks_dict[dep]['successors'].append(task_name)
    
    # Функция для расчета ранних сроков
    def calculate_early_times(task_name):
        if tasks_dict[task_name]['early_start'] is not None:
            return tasks_dict[task_name]['early_start'], tasks_dict[task_name]['early_finish']
        
        deps = tasks_dict[task_name]['dependencies']
        
        if not deps:
            start_date = pd.to_datetime(df[df['Task'] == task_name]['Start'].iloc[0])
        else:
            dep_finish_dates = []
            for dep in deps:
                if dep in tasks_dict:
                    _, dep_finish = calculate_early_times(dep)
                    dep_finish_dates.append(dep_finish)
            
            if dep_finish_dates:
                start_date = max(dep_finish_dates)
            else:
                start_date = pd.to_datetime(df[df['Task'] == task_name]['Start'].iloc[0])
        
        duration = tasks_dict[task_name]['duration']
        finish_date = start_date + pd.to_timedelta(duration, unit='d')
        
        tasks_dict[task_name]['early_start'] = start_date
        tasks_dict[task_name]['early_finish'] = finish_date
        
        return start_date, finish_date
    
    # Рассчитываем ранние сроки для всех задач
    for task_name in tasks_dict.keys():
        calculate_early_times(task_name)
    
    # Обновляем DataFrame с правильными датами
    for task_name, times in tasks_dict.items():
        df.loc[df['Task'] == task_name, 'Start'] = times['early_start']
        df.loc[df['Task'] == task_name, 'End'] = times['early_finish']
    
    # Рассчитываем поздние сроки и резерв
    project_end = df['End'].max()
    
    for task_name in tasks_dict.keys():
        tasks_dict[task_name]['late_finish'] = project_end
        tasks_dict[task_name]['late_start'] = project_end - pd.to_timedelta(tasks_dict[task_name]['duration'], unit='d')
    
    # Обратный проход для расчета поздних сроков
    for task_name in reversed(list(tasks_dict.keys())):
        successors = tasks_dict[task_name]['successors']
        if successors:
            min_late_start = min([tasks_dict[succ]['late_start'] for succ in successors])
            tasks_dict[task_name]['late_finish'] = min_late_start
            tasks_dict[task_name]['late_start'] = min_late_start - pd.to_timedelta(tasks_dict[task_name]['duration'], unit='d')
    
    # Рассчитываем резерв времени
    for task_name in tasks_dict.keys():
        tasks_dict[task_name]['float'] = (tasks_dict[task_name]['late_start'] - tasks_dict[task_name]['early_start']).days
    
    # Критический путь - задачи с нулевым резервом
    critical_tasks = [task_name for task_name, task_data in tasks_dict.items() if task_data['float'] == 0]
    
    # Отмечаем критические задачи
    if critical_tasks:
        df.loc[df['Task'].isin(critical_tasks), 'Is_Critical'] = True
        print(f"✅ Критический путь: {len(critical_tasks)} задач")
        
        # Находим и выводим полную цепочку критического пути
        start_critical = [task for task in critical_tasks if not tasks_dict[task]['dependencies']]
        if start_critical:
            chain = [start_critical[0]]
            current_task = start_critical[0]
            
            while tasks_dict[current_task]['successors']:
                next_critical = [succ for succ in tasks_dict[current_task]['successors'] if succ in critical_tasks]
                if next_critical:
                    chain.append(next_critical[0])
                    current_task = next_critical[0]
                else:
                    break
            
            print(f"🔗 Цепочка: {' → '.join(chain)}")
    
    return df

def print_detailed_analysis(df):
    """Детальный анализ проекта"""
    critical_tasks = df[df['Is_Critical']]
    total_duration = (df['End'].max() - df['Start'].min()).days
    
    print("\n" + "="*50)
    print("📊 АНАЛИЗ ПРОЕКТА")
    print("="*50)
    
    print(f"Всего задач: {len(df)}")
    print(f"Критических задач: {len(critical_tasks)}")
    print(f"Общая длительность: {total_duration} дней")
    print(f"Период: {df['Start'].min().strftime('%d.%m.%Y')} - {df['End'].max().strftime('%d.%m.%Y')}")
    
    print(f"\n🔴 КРИТИЧЕСКИЕ ЗАДАЧИ:")
    if len(critical_tasks) > 0:
        for task in critical_tasks.itertuples():
            deps_info = f" ← {task.Dependencies}" if hasattr(task, 'Dependencies') and pd.notna(task.Dependencies) else ""
            workers_info = f" [{task.Workers}ч]" if hasattr(task, 'Workers') else ""
            print(f"   • {task.Task} - {task.Duration} дней{workers_info}{deps_info}")

def create_gantt_chart(df, save_path=None, save_pdf=False):
    """Основная функция для создания диаграммы Ганта"""
    
    is_valid, errors, df_validated, inverse_mapping = validate_and_map_data(df)
    
    if not is_valid:
        print("❌ Ошибки валидации:")
        for error in errors:
            print(f"   - {error}")
        return None
    
    print("🔄 РАСЧЕТ КРИТИЧЕСКОГО ПУТИ И ДАТ...")
    
    # Правильно рассчитываем даты с учетом зависимостей
    df_with_dates = calculate_realistic_dates(df_validated)
    
    # Рассчитываем критический путь
    df_with_critical = calculate_critical_path_with_dependencies(df_with_dates)
    
    # Создаем диаграмму
    print("🎨 ПОСТРОЕНИЕ ДИАГРАММЫ...")
    fig, ax = plt.subplots(figsize=(16, 10))
    
    # Сортируем задачи по дате начала
    df_sorted = df_with_critical.sort_values('Start')
    
    # Рисуем каждую задачу
    for i, (_, task) in enumerate(df_sorted.iterrows()):
        if task['Is_Critical']:
            color = '#e74c3c'
            alpha = 0.9
        else:
            color = '#3498db'
            alpha = 0.7
        
        # Рисуем полосу задачи
        ax.barh(y=task['Task'],
               left=task['Start'],
               width=task['End'] - task['Start'],
               height=0.6,
               color=color,
               alpha=alpha,
               edgecolor='white',
               linewidth=1)
        
        # Добавляем подпись с длительностью
        center = task['Start'] + (task['End'] - task['Start']) / 2
        workers_info = f"({task.Workers}ч)" if hasattr(task, 'Workers') and task.Workers > 0 else ""
        ax.text(center, task['Task'], f'{int(task["Duration"])}д{workers_info}',
               ha='center', va='center',
               fontweight='bold', fontsize=8,
               color='white')
    
    # Настройка
    ax.set_xlabel('Дата')
    ax.set_ylabel('Задачи')
    ax.set_title('ДИАГРАММА ГАНТА С КРИТИЧЕСКИМ ПУТЕМ', fontweight='bold')
    ax.grid(axis='x', alpha=0.3)
    plt.xticks(rotation=45)
    
    # Легенда
    legend_elements = [
        Patch(facecolor='#e74c3c', alpha=0.9, label='Критический путь'),
        Patch(facecolor='#3498db', alpha=0.7, label='Обычные задачи')
    ]
    ax.legend(handles=legend_elements, loc='upper right')
    
    plt.tight_layout()
    
    # Сохранение
    if save_path:
        # Создаем папку если её нет
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"💾 Диаграмма сохранена: {save_path}")
    
    # Сохранение в PDF
    if save_pdf:
        pdf_path = save_path.replace('.png', '.pdf') if save_path else 'gantt_chart.pdf'
        with PdfPages(pdf_path) as pdf:
            pdf.savefig(fig, bbox_inches='tight')
            # Добавляем страницу с анализом
            plt.figure(figsize=(8, 11))
            plt.axis('off')
            
            # Создаем текстовый анализ для PDF
            critical_tasks = df_with_critical[df_with_critical['Is_Critical']]
            total_duration = (df_with_critical['End'].max() - df_with_critical['Start'].min()).days
            
            analysis_text = f"""
ДИАГРАММА ГАНТА - АНАЛИЗ ПРОЕКТА
{'='*50}

ОБЩАЯ ИНФОРМАЦИЯ:
• Всего задач: {len(df_with_critical)}
• Критических задач: {len(critical_tasks)}
• Общая длительность: {total_duration} дней
• Период выполнения: {df_with_critical['Start'].min().strftime('%d.%m.%Y')} - {df_with_critical['End'].max().strftime('%d.%m.%Y')}

КРИТИЧЕСКИЙ ПУТЬ:
"""
            for task in critical_tasks.itertuples():
                workers_info = f" ({task.Workers}ч)" if hasattr(task, 'Workers') and task.Workers > 0 else ""
                analysis_text += f"• {task.Task} - {task.Duration} дней{workers_info}\n"
            
            analysis_text += f"\nВСЕ ЗАДАЧИ:\n"
            for task in df_sorted.itertuples():
                deps_info = f" ← {task.Dependencies}" if hasattr(task, 'Dependencies') and pd.notna(task.Dependencies) else ""
                workers_info = f" ({task.Workers}ч)" if hasattr(task, 'Workers') and task.Workers > 0 else ""
                critical_mark = " 🔴" if task.Is_Critical else ""
                analysis_text += f"• {task.Task} - {task.Duration} дней{workers_info}{deps_info}{critical_mark}\n"
            
            plt.text(0.1, 0.95, analysis_text, transform=plt.gca().transAxes, 
                    fontsize=9, verticalalignment='top', fontfamily='monospace')
            pdf.savefig(bbox_inches='tight')
            plt.close()
        
        print(f"📄 PDF отчет сохранен: {pdf_path}")
    
    plt.show()
    
    # Анализ
    print_detailed_analysis(df_with_critical)
    
    return df_with_critical

# ========== ЗАПУСК ПРОГРАММЫ ==========

# Просто запусти эту функцию в ноутбуке:
# quick_upload()