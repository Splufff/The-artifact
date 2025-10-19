import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from datetime import datetime, timedelta
import numpy as np
import re

def validate_data(df):
    """Продвинутая валидация данных для всех возможных ошибок"""
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
                errors.append(f"Некорректные даты начала: {', '.join(invalid_tasks)}")
        except Exception as e:
            errors.append(f"Ошибка преобразования дат: {e}")
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
        
        # Проверка изолированных задач (без зависимостей и без зависимых)
        if len(df) > 1:
            graph = build_dependency_graph(df)
            isolated_tasks = []
            for task_name, task_data in graph.items():
                if not task_data['dependencies'] and not task_data['successors']:
                    isolated_tasks.append(f"'{task_name}'")
            
            if isolated_tasks:
                warnings.append(f"Изолированные задачи (без связей): {', '.join(isolated_tasks)}")
    
    # 7. Проверка числовых колонок
    numeric_columns = ['Workers', 'Priority', 'Cost']  # возможные числовые колонки
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
    
    # 9. Проверка на слишком длинные цепочки зависимостей
    if 'Dependencies' in df.columns and len(df) > 10:
        max_chain_length = find_max_chain_length(df)
        if max_chain_length > len(df) * 0.7:  # Если цепочка больше 70% задач
            warnings.append(f"Обнаружена очень длинная цепочка зависимостей ({max_chain_length} задач)")
    
    # 10. Проверка на пересекающиеся даты (если есть даты начала)
    if 'Start' in df.columns and 'Duration' in df.columns:
        date_conflicts = find_date_conflicts(df)
        if date_conflicts:
            warnings.append(f"Возможные конфликты в расписании: {len(date_conflicts)} пересечений")
    
    # ВЫВОД РЕЗУЛЬТАТОВ ВАЛИДАЦИИ
    if warnings:
        print("⚠️  ПРЕДУПРЕЖДЕНИЯ:")
        for warning in warnings:
            print(f"   • {warning}")
    
    if errors:
        print("❌ ОШИБКИ:")
        for error in errors:
            print(f"   🚫 {error}")
        
        print(f"\n💡 РЕКОМЕНДАЦИИ:")
        for error in errors:
            if "циклическ" in error.lower():
                print("   • Уберите круговые ссылки между задачами")
            elif "несуществующие" in error.lower():
                print("   • Проверьте правильность названий задач в зависимостях")
            elif "дублирующиеся" in error.lower():
                print("   • Сделайте названия задач уникальными")
            elif "отрицательные" in error.lower():
                print("   • Исправьте отрицательные значения на положительные")
            elif "длительности" in error.lower():
                print("   • Длительности должны быть положительными числами")
            elif "даты" in error.lower():
                print("   • Используйте формат ГГГГ-ММ-ДД для дат")
            elif "самозависимости" in error.lower():
                print("   • Задачи не могут зависеть от самих себя")
            elif "символы" in error.lower():
                print("   • Уберите специальные символы из зависимостей")
            elif "пустые элементы" in error.lower():
                print("   • Исправьте формат списка зависимостей")
        
        print(f"\n📋 ОБЗОР ДАННЫХ:")
        print(f"   Всего задач: {len(df)}")
        print(f"   Колонки: {', '.join(df.columns)}")
        print(f"   Пример данных:")
        print(df.head(3).to_string(index=False))
        
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
        # Убираем кавычки и лишние пробелы
        clean_str = str(deps_str).replace('"', '').replace("'", "").strip()
        if not clean_str:
            return []
        
        # Разделяем по запятой и очищаем
        deps = [dep.strip() for dep in clean_str.split(',')]
        return [dep for dep in deps if dep]  # Убираем пустые строки
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
            if neighbor in graph:  # Проверяем существование
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
                cycle_str = ' → '.join(cycle + [cycle[0]])  # Замыкаем цикл
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

def find_max_chain_length(df):
    """Находит максимальную длину цепочки зависимостей"""
    graph = build_dependency_graph(df)
    max_length = 0
    
    def dfs_length(task, visited, length):
        nonlocal max_length
        max_length = max(max_length, length)
        
        for successor in graph[task]['successors']:
            if successor not in visited:
                dfs_length(successor, visited | {successor}, length + 1)
    
    # Начинаем с задач без зависимостей
    start_tasks = [task for task, data in graph.items() if not data['dependencies']]
    for start_task in start_tasks:
        dfs_length(start_task, {start_task}, 1)
    
    return max_length

def find_date_conflicts(df):
    """Находит пересечения в датах выполнения задач"""
    conflicts = []
    
    for i, task1 in df.iterrows():
        if pd.isna(task1['Start']) or pd.isna(task1['Duration']):
            continue
            
        end1 = task1['Start'] + pd.to_timedelta(task1['Duration'], unit='d')
        
        for j, task2 in df.iterrows():
            if i >= j or pd.isna(task2['Start']) or pd.isna(task2['Duration']):
                continue
                
            end2 = task2['Start'] + pd.to_timedelta(task2['Duration'], unit='d')
            
            # Проверяем пересечение интервалов
            if (task1['Start'] <= end2 and task2['Start'] <= end1):
                conflicts.append(f"'{task1['Task']}' и '{task2['Task']}'")
    
    return conflicts

# ОСТАЛЬНЫЕ ФУНКЦИИ БЕЗ ИЗМЕНЕНИЙ (calculate_critical_path_with_dependencies, print_detailed_analysis, create_gantt_chart)

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
            # Задача без зависимостей начинается с даты из CSV
            start_date = pd.to_datetime(df[df['Task'] == task_name]['Start'].iloc[0])
        else:
            # Задача начинается после окончания ВСЕХ зависимостей
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

def create_gantt_chart(df, save_path=None):
    """Основная функция для создания диаграммы Ганта"""
    
    is_valid, errors, df_validated = validate_data(df)
    
    if not is_valid:
        return None
    
    print("🔄 РАСЧЕТ КРИТИЧЕСКОГО ПУТИ И ДАТ...")
    
    df_with_critical = calculate_critical_path_with_dependencies(df_validated)
    
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
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"💾 Диаграмма сохранена: {save_path}")
    
    plt.show()
    
    # Анализ
    print_detailed_analysis(df_with_critical)
    
    return df_with_critical
