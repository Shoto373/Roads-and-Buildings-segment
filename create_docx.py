"""
Скрипт генерации официального отчета по проекту (.docx), строго удовлетворяющего 5 условиям:
1. Краткое описание запущенного решения (что запущено и что позволяет).
2. Конфигурация компьютера (ОС, CPU, GPU, Python, точные версии библиотек).
3. Подробная пошаговая инструкция по запуску (от клонирования до метрик).
4. Не менее 10 примеров работы программы (10 дорог + 2 здания = 12 примеров).
5. Происхождение изображений (тип носителя/съемки, пространственное разрешение, каналы).
Оформление строго в черном цвете, без ИИ-штампов.
"""

import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls


def set_cell_margins(cell, top=80, bottom=80, left=140, right=140):
    """Установка внутренних отступов ячейки таблицы."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'  <w:top w:w="{top}" w:type="dxa"/>'
        f'  <w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'  <w:left w:w="{left}" w:type="dxa"/>'
        f'  <w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def add_code_box(doc, code_text):
    """Рамка для команд терминала и кода в черном цвете."""
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    cell = table.cell(0, 0)
    cell.width = Inches(6.5)

    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F8F8F8"/>')
    cell._tc.get_or_add_tcPr().append(shading)

    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'  <w:top w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/>'
        f'  <w:left w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/>'
        f'  <w:bottom w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/>'
        f'  <w:right w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/>'
        f'</w:tcBorders>'
    )
    cell._tc.get_or_add_tcPr().append(borders)
    set_cell_margins(cell, top=90, bottom=90, left=150, right=150)

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15

    lines = code_text.strip().split('\n')
    for idx, line in enumerate(lines):
        run = p.add_run(line)
        run.font.name = 'Consolas'
        run.font.size = Pt(9.5)
        run.font.color.rgb = RGBColor(0, 0, 0)
        if idx < len(lines) - 1:
            p.add_run('\n')

    spacing_p = doc.add_paragraph()
    spacing_p.paragraph_format.space_before = Pt(0)
    spacing_p.paragraph_format.space_after = Pt(3)


def add_note(doc, label, text):
    """Строгое текстовое примечание в черном цвете."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(5)
    p.paragraph_format.line_spacing = 1.15

    run_label = p.add_run(label + ": ")
    run_label.bold = True
    run_label.font.color.rgb = RGBColor(0, 0, 0)

    run_text = p.add_run(text)
    run_text.font.size = Pt(10.5)
    run_text.font.color.rgb = RGBColor(0, 0, 0)


def add_divider(doc):
    """Горизонтальный разделитель."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(8)
    pBdr = parse_xml(
        f'<w:pBdr {nsdecls("w")}>'
        f'  <w:bottom w:val="single" w:sz="4" w:space="1" w:color="CCCCCC"/>'
        f'</w:pBdr>'
    )
    p._p.get_or_add_pPr().append(pBdr)


def add_footer_page_numbers(doc):
    """Центрированная нумерация страниц в нижнем колонтитуле."""
    for section in doc.sections:
        footer = section.footer
        p = footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        fldSimple = parse_xml(r'<w:fldSimple %s w:instr="PAGE"/>' % nsdecls('w'))
        run._r.append(fldSimple)
        run.font.name = 'Calibri'
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(0, 0, 0)


def main():
    doc = Document()

    # Поля страницы 1 дюйм
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Базовые стили
    doc.styles['Normal'].font.name = 'Calibri'
    doc.styles['Normal'].font.size = Pt(11)
    doc.styles['Normal'].font.color.rgb = RGBColor(0, 0, 0)

    # Заголовок документа
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(4)
    run_title = p_title.add_run('Отчет по проекту: Сегментация дорог и зданий на аэрофотоснимках')
    run_title.font.name = 'Calibri'
    run_title.font.size = Pt(18)
    run_title.bold = True
    run_title.font.color.rgb = RGBColor(0, 0, 0)

    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(12)
    run_sub = p_sub.add_run('Архитектура EffUNet (UNet + EfficientNet-B7) | Massachusetts Dataset')
    run_sub.font.name = 'Calibri'
    run_sub.font.size = Pt(13)
    run_sub.bold = True
    run_sub.font.color.rgb = RGBColor(0, 0, 0)

    # =========================================================================
    # 1. Описание решения
    # =========================================================================
    h1 = doc.add_heading('1. Описание запущенного решения', level=1)
    h1.paragraph_format.space_before = Pt(8)
    h1.paragraph_format.space_after = Pt(3)
    h1.runs[0].font.color.rgb = RGBColor(0, 0, 0)

    p = doc.add_paragraph(
        'Запущена программная система семантической сегментации дорожной сети и объектов застройки на аэрофотоснимках '
        'высокого пространственного разрешения. Решение построено на базе нейросетевой архитектуры UNet с предобученным '
        'энкодером EfficientNet-B7 и специализированной функцией потерь Combo Loss (DiceLoss + BCEWithLogitsLoss). '
        'Система принимает на вход аэрофотоснимки в формате RGB и в автоматическом режиме формирует бинарные растровые маски, '
        'выделяя полотно автомобильных дорог и контуры зданий с сохранением связности дорожных артерий.'
    )
    p.paragraph_format.space_after = Pt(4)

    add_divider(doc)

    # =========================================================================
    # 2. Конфигурация оборудования и программного обеспечения
    # =========================================================================
    h1 = doc.add_heading('2. Конфигурация системы для запуска', level=1)
    h1.paragraph_format.space_before = Pt(8)
    h1.paragraph_format.space_after = Pt(3)
    h1.runs[0].font.color.rgb = RGBColor(0, 0, 0)

    p = doc.add_paragraph('Запуск, обучение и инференс производились на следующей рабочей станции:')
    p.paragraph_format.space_after = Pt(2)

    hw_info = [
        ("Операционная система: ", "Windows 11 (build 10.0.26100)"),
        ("Центральный процессор (CPU): ", "AMD Ryzen 5 5600 6-Core Processor (3.50 GHz, 6 ядер, 12 логических процессоров)"),
        ("Видеокарта (GPU): ", "NVIDIA GeForce RTX 5060 (8 ГБ видеопамяти GDDR6, шина 128 бит, CUDA 13.3)"),
        ("Интерпретатор Python: ", "Python 3.14.6"),
    ]
    for lbl, val in hw_info:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(1)
        r1 = bp.add_run(lbl)
        r1.bold = True
        r1.font.color.rgb = RGBColor(0, 0, 0)
        r2 = bp.add_run(val)
        r2.font.color.rgb = RGBColor(0, 0, 0)

    p = doc.add_paragraph('Точные версии используемых библиотек (согласно рабочему окружению pip):')
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(2)

    libs_text = (
        "torch==2.13.0\n"
        "torchvision==0.28.0\n"
        "segmentation-models-pytorch==0.5.0\n"
        "albumentations==2.0.8\n"
        "opencv-python==5.0.0.93\n"
        "numpy==2.5.1\n"
        "pandas==3.0.5\n"
        "matplotlib==3.11.1\n"
        "seaborn==0.13.2\n"
        "tqdm==4.70.0\n"
        "tensorboard==2.21.0\n"
        "python-docx==1.2.0"
    )
    add_code_box(doc, libs_text)

    add_divider(doc)

    # =========================================================================
    # 3. Подробная инструкция по запуску по шагам
    # =========================================================================
    h1 = doc.add_heading('3. Подробная пошаговая инструкция по запуску', level=1)
    h1.paragraph_format.space_before = Pt(8)
    h1.paragraph_format.space_after = Pt(3)
    h1.runs[0].font.color.rgb = RGBColor(0, 0, 0)

    # Шаг 1
    h2 = doc.add_heading('Шаг 1. Клонирование репозитория', level=2)
    h2.paragraph_format.space_before = Pt(6)
    h2.paragraph_format.space_after = Pt(2)
    h2.runs[0].font.color.rgb = RGBColor(0, 0, 0)
    p = doc.add_paragraph('Клонируйте проект из репозитория и перейдите в его каталог:')
    p.paragraph_format.space_after = Pt(2)
    add_code_box(doc, "git clone https://github.com/Shoto373/Roads-and-Buildings-segment.git\ncd Roads-and-Buildings-segment")

    # Шаг 2
    h2 = doc.add_heading('Шаг 2. Создание и активация виртуального окружения', level=2)
    h2.paragraph_format.space_before = Pt(6)
    h2.paragraph_format.space_after = Pt(2)
    h2.runs[0].font.color.rgb = RGBColor(0, 0, 0)
    p = doc.add_paragraph('Создайте виртуальное окружение Python:')
    p.paragraph_format.space_after = Pt(2)
    add_code_box(doc, "python -m venv .venv")
    p = doc.add_paragraph('Активируйте окружение:')
    p.paragraph_format.space_after = Pt(2)
    add_code_box(doc, ".\\.venv\\Scripts\\activate       # Для Windows (PowerShell/CMD)\n# source .venv/bin/activate    # Для Linux/macOS")

    # Шаг 3
    h2 = doc.add_heading('Шаг 3. Установка зависимостей', level=2)
    h2.paragraph_format.space_before = Pt(6)
    h2.paragraph_format.space_after = Pt(2)
    h2.runs[0].font.color.rgb = RGBColor(0, 0, 0)
    p = doc.add_paragraph('Обновите менеджер pip и установите пакеты из requirements.txt:')
    p.paragraph_format.space_after = Pt(2)
    add_code_box(doc, "python -m pip install --upgrade pip\npip install -r requirements.txt")
    add_note(doc, 'Примечание', 'Для задействования видеокарты NVIDIA установите PyTorch с CUDA: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121')

    # Шаг 4
    h2 = doc.add_heading('Шаг 4. Подготовка и размещение данных', level=2)
    h2.paragraph_format.space_before = Pt(6)
    h2.paragraph_format.space_after = Pt(2)
    h2.runs[0].font.color.rgb = RGBColor(0, 0, 0)
    p = doc.add_paragraph('Загрузите наборы данных через Kaggle API или вручную с kaggle.com:')
    p.paragraph_format.space_after = Pt(2)
    add_code_box(
        doc,
        "kaggle datasets download -d balraj98/massachusetts-roads-dataset\n"
        "kaggle datasets download -d balraj98/massachusetts-buildings-dataset"
    )
    p = doc.add_paragraph('Распакуйте архивы в каталог notebooks/input/. Структура файлов должна иметь вид:')
    p.paragraph_format.space_after = Pt(2)
    add_code_box(
        doc,
        "notebooks/input/massachusetts-roads-dataset/\n"
        "  ├── train/ (1108 снимков и масок)\n"
        "  ├── val/   (14 снимков и масок)\n"
        "  └── test/  (49 снимков и масок)\n"
        "notebooks/input/massachusetts-buildings-dataset/\n"
        "  ├── train/, val/, test/"
    )

    # Шаг 5
    h2 = doc.add_heading('Шаг 5. Размещение предобученных весов моделей', level=2)
    h2.paragraph_format.space_before = Pt(6)
    h2.paragraph_format.space_after = Pt(2)
    h2.runs[0].font.color.rgb = RGBColor(0, 0, 0)
    p = doc.add_paragraph('Файлы весов модели должны находиться в каталоге weights/:')
    p.paragraph_format.space_after = Pt(2)
    add_code_box(
        doc,
        "weights/best_road_model.pth        # Веса модели сегментации дорог\n"
        "weights/road_model_30_epochs.pth   # Модель дорог (обучение 30 эпох)\n"
        "weights/best_model.pth             # Веса модели сегментации зданий"
    )

    # Шаг 6
    h2 = doc.add_heading('Шаг 6. Запуск инференса (демонстрации работы)', level=2)
    h2.paragraph_format.space_before = Pt(6)
    h2.paragraph_format.space_after = Pt(2)
    h2.runs[0].font.color.rgb = RGBColor(0, 0, 0)
    p = doc.add_paragraph('Для генерации и сохранения сопоставительных примеров предсказания на тестовых снимках:')
    p.paragraph_format.space_after = Pt(2)
    add_code_box(
        doc,
        "# Генерация 10 примеров сегментации дорог:\n"
        "python inference.py --task road --weights weights/road_model_30_epochs.pth --num-examples 10\n\n"
        "# Запуск с Test-Time Augmentation (усреднение отражений TTA):\n"
        "python inference.py --task road --tta --num-examples 10\n\n"
        "# Инференс на произвольном снимке:\n"
        "python inference.py --task road --input-image путь_к_изображению.png"
    )
    add_note(doc, 'Результат', 'Итоговые графические файлы сохраняются в каталоге outputs/.')

    # Шаг 7
    h2 = doc.add_heading('Шаг 7. Запуск обучения моделей', level=2)
    h2.paragraph_format.space_before = Pt(6)
    h2.paragraph_format.space_after = Pt(2)
    h2.runs[0].font.color.rgb = RGBColor(0, 0, 0)
    p = doc.add_paragraph('Для запуска цикла обучения выполните:')
    p.paragraph_format.space_after = Pt(2)
    add_code_box(
        doc,
        "# Обучение модели сегментации дорог (Combo Loss, AMP, Early Stopping):\n"
        "python train.py --task road --epochs 40 --batch-size 4 --loss combo\n\n"
        "# Обучение модели сегментации зданий:\n"
        "python train.py --task building --epochs 40 --batch-size 4 --loss combo\n\n"
        "# Запуск мониторинга TensorBoard:\n"
        "tensorboard --logdir runs"
    )

    # Шаг 8
    h2 = doc.add_heading('Шаг 8. Оценка качества на тестовом наборе', level=2)
    h2.paragraph_format.space_before = Pt(6)
    h2.paragraph_format.space_after = Pt(2)
    h2.runs[0].font.color.rgb = RGBColor(0, 0, 0)
    p = doc.add_paragraph('Для полного расчета метрик (IoU, Dice, Precision, Recall, Accuracy):')
    p.paragraph_format.space_after = Pt(2)
    add_code_box(
        doc,
        "python evaluate.py --task road\n"
        "python evaluate.py --task building"
    )

    add_divider(doc)

    # =========================================================================
    # 4. Источник данных и технические требования к изображениям
    # =========================================================================
    h1 = doc.add_heading('4. Источник данных и технические требования к изображениям', level=1)
    h1.paragraph_format.space_before = Pt(8)
    h1.paragraph_format.space_after = Pt(3)
    h1.runs[0].font.color.rgb = RGBColor(0, 0, 0)

    # 4.1
    h2 = doc.add_heading('4.1. Происхождение набора данных и параметры съемки', level=2)
    h2.paragraph_format.space_before = Pt(6)
    h2.paragraph_format.space_after = Pt(2)
    h2.runs[0].font.color.rgb = RGBColor(0, 0, 0)

    p = doc.add_paragraph(
        'Обучение и тестирование модели проводились на наборах данных Massachusetts Roads Dataset '
        'и Massachusetts Buildings Dataset (автор — Владимир Мних, University of Toronto, 2013).'
    )
    p.paragraph_format.space_after = Pt(2)

    ds_specs = [
        ("Носитель и тип съемки: ", "цифровая аэрофотосъемка (авиационные носители Геологической службы США USGS / MassGIS в рамках национальной программы NAIP — National Agriculture Imagery Program). Съемка велась с пилотируемых самолетов специализированными крупноформатными цифровыми камерами, что исключает орбитальные атмосферные искажения и обеспечивает четкие контуры объектов."),
        ("Базовое пространственное разрешение: ", "1.0 метр на пиксель (1 m/pixel). Каждый пиксель изображения соответствует участку 1 × 1 м на земной поверхности."),
        ("Геометрический охват тайла: ", "1500 × 1500 пикселей. Площадь покрытия одного кадра составляет 1.5 × 1.5 км (2.25 кв. км)."),
        ("Спектральный состав: ", "3-канальный видимый диапазон (RGB — Red, Green, Blue), глубина цвета 24 бит (8 бит на канал)."),
        ("Регион съемки: ", "штат Массачусетс, США (городские округа Бостона, пригородная застройка, автомагистрали, промышленные зоны и лесистая местность).")
    ]
    for lbl, val in ds_specs:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(1)
        r1 = bp.add_run(lbl)
        r1.bold = True
        r1.font.color.rgb = RGBColor(0, 0, 0)
        r2 = bp.add_run(val)
        r2.font.color.rgb = RGBColor(0, 0, 0)

    # 4.2
    h2 = doc.add_heading('4.2. Требования к пространственному разрешению (масштаб на местности / GSD)', level=2)
    h2.paragraph_format.space_before = Pt(6)
    h2.paragraph_format.space_after = Pt(2)
    h2.runs[0].font.color.rgb = RGBColor(0, 0, 0)

    p = doc.add_paragraph(
        'Пространственное разрешение (GSD — Ground Sample Distance) определяет физический масштаб объектов в пикселях. '
        'Модель настроена на геометрию реального мира при масштабе около 1.0 м/пикс:'
    )
    p.paragraph_format.space_after = Pt(2)

    gsd_points = [
        ("Оптимальный диапазон GSD: ", "от 0.5 до 1.5 метра на пиксель (эталонное значение: 1.0 м/пикс)."),
        ("Соотношение объектов и пикселей: ", "стандартная двухполосная дорога шириной 6–8 м занимает 6–8 пикселей; автомагистраль (15–25 м) занимает 15–25 пикселей; узкий проезд или грунтовка (3–4 м) занимает 3–4 пикселя."),
        ("Ограничения спутниковых снимков низкого разрешения: ", "на снимках со спутников класса Sentinel-2 (разрешение 10 м/пикс) ширина дорожного полотна меньше 1 пикселя, вследствие чего сегментация дорожной сети невозможна."),
        ("Особенности снимков сверхвысокого разрешения (БПЛА / квадрокоптеры): ", "на снимках с дронов с детальностью 5–10 см/пикс обычная дорога имеет ширину 80–150 пикселей и воспринимается моделью как открытая асфальтовая площадка, а не линия дороги. Такие снимки перед подачей на вход необходимо масштабировать (downscale) в 5–10 раз до эквивалента ~1 м/пикс.")
    ]
    for lbl, val in gsd_points:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(1)
        r1 = bp.add_run(lbl)
        r1.bold = True
        r1.font.color.rgb = RGBColor(0, 0, 0)
        r2 = bp.add_run(val)
        r2.font.color.rgb = RGBColor(0, 0, 0)

    # 4.3
    h2 = doc.add_heading('4.3. Требования к пиксельному разрешению и размерам входных файлов', level=2)
    h2.paragraph_format.space_before = Pt(6)
    h2.paragraph_format.space_after = Pt(2)
    h2.runs[0].font.color.rgb = RGBColor(0, 0, 0)

    res_points = [
        ("Базовый размер тайлов датасета: ", "1500 × 1500 пикселей (в пайплайне автоматически дополняется паддингом до 1536 × 1536)."),
        ("Кратность 32 для архитектуры UNet: ", "стороны входного тензора должны быть кратны 32 из-за пяти уровней понижения дискретизации (2^5 = 32) в сверточном энкодере."),
        ("Поддержка произвольных размеров фото: ", "скрипт inference.py поддерживает обработку снимков любого исходного разрешения (1024×1024, 1500×1500, 2048×2048, 1920×1080 и др.). Алгоритм автоматически рассчитывает симметричный паддинг до ближайшей границы, кратной 32, выполняет сегментацию и обрезает результат точно под исходные размеры файла."),
        ("Обработка крупноформатных ортофотопланов: ", "аэрофотоснимки размером свыше 3000 × 3000 пикселей рекомендуется предварительно нарезать на тайлы 1500 × 1500 пикселей с перекрытием (overlap) 50–100 пикселей для предотвращения краевых разрывов дорог.")
    ]
    for lbl, val in res_points:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(1)
        r1 = bp.add_run(lbl)
        r1.bold = True
        r1.font.color.rgb = RGBColor(0, 0, 0)
        r2 = bp.add_run(val)
        r2.font.color.rgb = RGBColor(0, 0, 0)

    # 4.4
    h2 = doc.add_heading('4.4. Форматы файлов и цветовая модель', level=2)
    h2.paragraph_format.space_before = Pt(6)
    h2.paragraph_format.space_after = Pt(2)
    h2.runs[0].font.color.rgb = RGBColor(0, 0, 0)

    fmt_points = [
        ("Цветовое пространство: ", "3 канала RGB (Red, Green, Blue). Одноканальные панхроматические или многоканальные мультиспектральные снимки предварительно приводятся к 3-канальному RGB."),
        ("Поддерживаемые форматы файлов: ", "TIFF (.tif, .tiff), PNG (.png), JPEG (.jpg, .jpeg).")
    ]
    for lbl, val in fmt_points:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(1)
        r1 = bp.add_run(lbl)
        r1.bold = True
        r1.font.color.rgb = RGBColor(0, 0, 0)
        r2 = bp.add_run(val)
        r2.font.color.rgb = RGBColor(0, 0, 0)

    add_divider(doc)

    # =========================================================================
    # 5. Результаты тестирования
    # =========================================================================
    h1 = doc.add_heading('5. Количественные результаты тестирования', level=1)
    h1.paragraph_format.space_before = Pt(8)
    h1.paragraph_format.space_after = Pt(3)
    h1.runs[0].font.color.rgb = RGBColor(0, 0, 0)

    p = doc.add_paragraph('Сводные метрики качества по результатам оценки на тестовых выборках с помощью модуля evaluate.py:')
    p.paragraph_format.space_after = Pt(3)

    metrics_data = [
        ["Метрика", "Сегментация дорог (Road, 49 снимков)", "Сегментация зданий (Building, 10 снимков)"],
        ["IoU (Intersection over Union)", "0.4872 ± 0.0603", "0.6039 ± 0.0351"],
        ["Dice / F1-Score", "0.6528 ± 0.0582", "0.7524 ± 0.0273"],
        ["Precision (точность)", "0.5704 ± 0.0492", "0.7908 ± 0.0268"],
        ["Recall (полнота)", "0.7730 ± 0.0991", "0.7187 ± 0.0385"],
        ["Accuracy (пиксельная)", "0.9626 ± 0.0209", "0.9143 ± 0.0340"],
    ]

    m_table = doc.add_table(rows=len(metrics_data), cols=3)
    m_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    m_table.autofit = False

    col_widths = [Inches(2.5), Inches(2.0), Inches(2.0)]
    for row_idx, row in enumerate(m_table.rows):
        for col_idx, cell in enumerate(row.cells):
            cell.width = col_widths[col_idx]
            cell.text = metrics_data[row_idx][col_idx]
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(3)

            p.runs[0].font.color.rgb = RGBColor(0, 0, 0)
            if row_idx == 0:
                shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F0F0F0"/>')
                cell._tc.get_or_add_tcPr().append(shd)
                p.runs[0].bold = True
                p.runs[0].font.size = Pt(10)
            else:
                p.runs[0].font.size = Pt(10)
                if col_idx == 0:
                    p.runs[0].bold = True

            borders = parse_xml(
                f'<w:tcBorders {nsdecls("w")}>'
                f'  <w:top w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/>'
                f'  <w:left w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/>'
                f'  <w:bottom w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/>'
                f'  <w:right w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/>'
                f'</w:tcBorders>'
            )
            cell._tc.get_or_add_tcPr().append(borders)
            set_cell_margins(cell, top=70, bottom=70, left=120, right=120)

    spacing_p = doc.add_paragraph()
    spacing_p.paragraph_format.space_before = Pt(0)
    spacing_p.paragraph_format.space_after = Pt(6)

    add_divider(doc)

    # =========================================================================
    # 6. Примеры работы программы (12 примеров: 10 дорог + 2 здания)
    # =========================================================================
    h1 = doc.add_heading('6. Примеры работы программы (12 примеров)', level=1)
    h1.paragraph_format.space_before = Pt(8)
    h1.paragraph_format.space_after = Pt(3)
    h1.runs[0].font.color.rgb = RGBColor(0, 0, 0)

    p = doc.add_paragraph(
        'Ниже представлены сопоставительные примеры работы модели: 10 примеров сегментации дорожной сети (основная задача) '
        'и 2 демонстрационных примера сегментации зданий. Для каждого примера сопоставлены: исходный аэрофотоснимок, '
        'истинная бинарная разметка (Ground Truth) и маска, предсказанная нейросетью.'
    )
    p.paragraph_format.space_after = Pt(4)

    # 6.1 Дороги (10 примеров)
    h2 = doc.add_heading('6.1. Сегментация дорожной сети (10 примеров)', level=2)
    h2.paragraph_format.space_before = Pt(6)
    h2.paragraph_format.space_after = Pt(3)
    h2.runs[0].font.color.rgb = RGBColor(0, 0, 0)

    road_labels = [
        "Пример 1 (Дороги): Городские улицы и перекрестки",
        "Пример 2 (Дороги): Магистрали и транспортные развязки",
        "Пример 3 (Дороги): Плотная уличная сеть",
        "Пример 4 (Дороги): Дорожная сеть жилых массивов",
        "Пример 5 (Дороги): Загородные шоссе и подъезды",
        "Пример 6 (Дороги): Сложные многополосные пересечения",
        "Пример 7 (Дороги): Извилистые дороги пригорода",
        "Пример 8 (Дороги): Тонкие проезды и проселочные дороги",
        "Пример 9 (Дороги): Радиальная дорожная сеть",
        "Пример 10 (Дороги): Связность дорожного полотна в промышленной зоне",
    ]

    for i in range(1, 11):
        img_path = f'outputs/road_example_{i}.png'
        if os.path.exists(img_path):
            p_ex = doc.add_paragraph()
            p_ex.paragraph_format.space_before = Pt(6)
            p_ex.paragraph_format.space_after = Pt(2)
            run_lbl = p_ex.add_run(f'{road_labels[i-1]} (Оригинал / Разметка / Предсказание)')
            run_lbl.bold = True
            run_lbl.font.size = Pt(10)
            run_lbl.font.color.rgb = RGBColor(0, 0, 0)

            doc.add_picture(img_path, width=Inches(6.2))

    # 6.2 Здания (2 примера)
    h2 = doc.add_heading('6.2. Сегментация зданий (2 примера)', level=2)
    h2.paragraph_format.space_before = Pt(8)
    h2.paragraph_format.space_after = Pt(3)
    h2.runs[0].font.color.rgb = RGBColor(0, 0, 0)

    building_labels = [
        "Пример 11 (Здания): Малоэтажная и коттеджная застройка",
        "Пример 12 (Здания): Плотная городская и промышленная застройка",
    ]

    for i in range(1, 3):
        img_path = f'outputs/building_example_{i}.png'
        if not os.path.exists(img_path):
            img_path = f'outputs/example_{i}.png'
        if os.path.exists(img_path):
            p_ex = doc.add_paragraph()
            p_ex.paragraph_format.space_before = Pt(6)
            p_ex.paragraph_format.space_after = Pt(2)
            run_lbl = p_ex.add_run(f'{building_labels[i-1]} (Оригинал / Разметка / Предсказание)')
            run_lbl.bold = True
            run_lbl.font.size = Pt(10)
            run_lbl.font.color.rgb = RGBColor(0, 0, 0)

            doc.add_picture(img_path, width=Inches(6.2))

    # Нумерация страниц
    add_footer_page_numbers(doc)

    output_path = 'reports/Отчет_по_проекту_Итоговый.docx'
    os.makedirs('reports', exist_ok=True)
    try:
        doc.save(output_path)
        print(f"[+] Successfully generated: {output_path}")
    except PermissionError:
        alt_path = 'reports/Отчет_по_проекту_Итоговый_обновленный.docx'
        doc.save(alt_path)
        print(f"[!] {output_path} is currently locked by another program (e.g. Word).")
        print(f"[+] Successfully generated fallback copy: {alt_path}")


if __name__ == '__main__':
    main()
