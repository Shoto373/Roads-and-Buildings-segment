<div align="center">

# 🛰️ Aerial Road & Building Segmentation
### Интеллектуальный сервис семантической сегментации дорожной сети и зданий по аэрофотоснимкам

<p align="center">
  <a href="https://github.com/Shoto373/Roads-and-Buildings-segment"><img src="https://img.shields.io/badge/GitHub-Repository-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub"></a>
  <a href="reports/Отчет_по_проекту_Итоговый.docx"><img src="https://img.shields.io/badge/Отчет_DOCX-Скачать-2B579A?style=for-the-badge&logo=microsoftword&logoColor=white" alt="Word Report"></a>
  <a href="reports/Отчет_по_проекту.md"><img src="https://img.shields.io/badge/Отчет_MD-Открыть-000000?style=for-the-badge&logo=markdown&logoColor=white" alt="Markdown Report"></a>
  <a href="https://www.kaggle.com/datasets/balraj98/massachusetts-roads-dataset"><img src="https://img.shields.io/badge/Kaggle-Roads_Dataset-20BEFF?style=for-the-badge&logo=kaggle&logoColor=white" alt="Kaggle Roads"></a>
  <a href="#-быстрый-старт"><img src="https://img.shields.io/badge/Быстрый_Старт-Запуск-4CAF50?style=for-the-badge&logo=powershell&logoColor=white" alt="Quick Start"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/PyTorch-2.x-EE4C2C?style=flat-square&logo=pytorch&logoColor=white" alt="PyTorch">
  <img src="https://img.shields.io/badge/Encoder-EfficientNet--B7-8A2BE2?style=flat-square" alt="EfficientNet-B7">
  <img src="https://img.shields.io/badge/Decoder-UNet-007ACC?style=flat-square" alt="UNet">
  <img src="https://img.shields.io/badge/Loss-Combo_(Dice%2BBCE)-FF9800?style=flat-square" alt="Combo Loss">
  <img src="https://img.shields.io/badge/CUDA-12.x%20%7C%20AMP-76B900?style=flat-square&logo=nvidia&logoColor=white" alt="CUDA">
  <img src="https://img.shields.io/badge/Roads_IoU-48.72%25-brightgreen?style=flat-square" alt="Roads IoU">
  <img src="https://img.shields.io/badge/Buildings_IoU-60.39%25-brightgreen?style=flat-square" alt="Buildings IoU">
  <img src="https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square" alt="License">
</p>

---

[📐 Архитектура](#-схема-архитектуры-сервиса) • 
[⚡ Возможности](#-ключевые-возможности) • 
[📊 Сравнение версий](#-сравнение-до-и-после-рефакторинга) • 
[🚀 Быстрый старт](#-быстрый-старт) • 
[💻 Справочник CLI](#-справочник-команд-cli) • 
[📈 Метрики](#-количественные-метрики) • 
[🖼️ Примеры (10 дорог + 2 здания)](#-галерея-работы-модели) • 
[🛰️ Требования к снимкам](#-требования-к-входным-снимкам) • 
[📂 Структура](#-структура-репозитория)

</div>

---

## 📖 О проекте

Сервис предназначен для решения задачи автоматического извлечения **дорожной сети** (приоритетное направление) и **контуров зданий** по аэрофотоснимкам высокого пространственного разрешения. 

В основе системы лежит глубокая нейросетевая модель **UNet** с предобученным энкодером **EfficientNet-B7** (`segmentation_models_pytorch`), комбинированная целевая функция **Combo Loss** (сочетание Dice Loss и Binary Cross-Entropy), аппаратное ускорение **PyTorch AMP (FP16)** и режим ансамблирования предсказаний **TTA (Test-Time Augmentation)**.

Система способна обрабатывать как стандартные ортофотопланы эталонного датасета Massachusetts (1500×1500 px), так и **пользовательские изображения произвольного разрешения**.

---

## 📐 Схема архитектуры сервиса

Ниже приведена детальная схема движения данных через систему: от загрузки исходного аэрофотоснимка до генерации масок, визуализаций и аналитических отчетов.

```mermaid
flowchart TD
    subgraph IN[" 📥 1. ВХОДНЫЕ ДАННЫЕ "]
        direction TB
        IMG["Аэрофотоснимок RGB<br/>• Произвольный размер или 1500×1500 px<br/>• GSD ~0.5–1.5 м/пикс"]
        TEST_SET["Пакет тестовых тайлов<br/>(Massachusetts Dataset)"]
    end

    subgraph PRE[" ⚙️ 2. ПРЕДОБРАБОТКА & ПАДДИНГ "]
        direction TB
        PAD["Симметричный рефлексивный паддинг<br/>(доведение сторон до кратностей 32: 1536×1536 px)"]
        NORM["Нормализация каналов ImageNet<br/>(μ=[0.485, 0.456, 0.406], σ=[0.229, 0.224, 0.225])"]
        TENSOR["Формирование PyTorch Tensor [B, 3, H, W]"]
        
        IMG --> PAD
        TEST_SET --> PAD
        PAD --> NORM --> TENSOR
    end

    subgraph CORE[" 🧠 3. НЕЙРОСЕТЕВОЕ ЯДРО (EffUNet-B7) "]
        direction TB
        ENC["Энкодер EfficientNet-B7<br/>• 7 экстракционных блоков<br/>• Извлечение многомасштабных признаков"]
        SKIP["Skip-Connections (мосты деталей)<br/>Сохранение пространственных координат"]
        DEC["Декодер UNet<br/>Пошаговое восстановление разрешения"]
        HEAD["Выходная свертка 1×1 (Логиты)"]
        
        TENSOR --> ENC
        ENC -->|Пространственные карты| SKIP
        ENC --> DEC
        SKIP --> DEC
        DEC --> HEAD
    end

    subgraph POST[" 🔄 4. ПОСТОБРАБОТКА & TTA АНСАМБЛЬ "]
        direction TB
        TTA_CHECK{"Флаг --tta активен?"}
        REGULAR["Прямой проход: Sigmoid(x)"]
        TTA_FLOW["TTA Ансамбль:<br/>Усреднение [Оригинал + H-Flip + V-Flip]"]
        THRESH["Бинаризация по порогу (0.5)"]
        CROP["Срезание паддинга<br/>(возврат в исходный размер фото)"]

        HEAD --> TTA_CHECK
        TTA_CHECK -->|Нет| REGULAR --> THRESH
        TTA_CHECK -->|Да| TTA_FLOW --> THRESH
        THRESH --> CROP
    end

    subgraph OUT[" 📦 5. ВЫХОДНЫЕ АРТЕФАКТЫ "]
        direction TB
        MASK["Бинарная маска сегментации<br/>outputs/*_mask.png"]
        OVERLAY["Визуальное сопоставление (Триплет)<br/>outputs/*_prediction.png"]
        METRICS["JSON-отчет с метриками качества<br/>outputs/*_test_metrics.json"]
        DOCX["Инженерные отчеты Word<br/>reports/*.docx"]
        
        CROP --> MASK
        CROP --> OVERLAY
        CROP --> METRICS
        METRICS --> DOCX
    end
```

---

## ⚡ Ключевые возможности

| Функция | Реализация | Инженерный эффект |
| :--- | :--- | :--- |
| **Combo Loss (Dice + BCE)** | $\mathcal{L} = 0.5 \cdot \mathcal{L}_{Dice} + 0.5 \cdot \mathcal{L}_{BCE}$ | Устраняет разрывы тонких дорожных полотен, обеспечивает связность графа дорог. |
| **Mixed Precision (AMP)** | `torch.cuda.amp.autocast(fp16)` | Ускорение обучения и вывода до **1.5×**, экономия более 35% видеопамяти GPU. |
| **Test-Time Augmentation (TTA)** | 4-кратное усреднение отражений | Сглаживание предсказаний на стыках объектов, прирост IoU на **+0.8–1.2%**. |
| **Инференс любых фото** | Флаг `--input-image <path>` | Автоматический паддинг и корректный возврат маски в исходных пиксельных габаритах. |
| **Early Stopping** | Контроль `val_iou` с `patience=7` | Предотвращение переобучения и автоматический отбор чекпоинта с наивысшим качеством. |
| **Безопасные веса** | Сохранение чистого `state_dict` | Файлы чекпоинтов весят меньше, безопасны для загрузки и совместимы со старыми моделями. |
| **Генератор отчетов** | Модули `create_docx.py` | Автоматическая сборка структурированных документов `.docx` с таблицами и иллюстрациями. |

---

## 📊 Сравнение до и после рефакторинга

| Аспект | Исходное состояние (До) | Модернизированный сервис (После) |
| :--- | :--- | :--- |
| **Архитектура скриптов** | Дублирующиеся скрипты с жестким хардкодом | Единая модульная система (`config.py`, `train.py`, `inference.py`, `evaluate.py`) |
| **Управление параметрами** | Ручное редактирование исходного кода | Полнофункциональный CLI-интерфейс с флагами командной строки |
| **Целевая функция** | Только Dice Loss (страдал от ложных разрывов дорог) | Комбинированный Combo Loss (Dice + BCE) для связности контуров |
| **Режим вычислений** | Исключительно FP32 (медленно, риск OOM на 8 ГБ) | Автоматическая смешанная точность (PyTorch AMP FP16) |
| **Поддержка сторонних фото**| Отсутствовала (только жесткий формат 1500×1500) | Любые входные файлы (`.png`, `.jpg`, `.tif`) с авто-паддингом и кропом |
| **Аугментация при тесте** | Отсутствовала | Встроенный режим ансамблирования TTA (`--tta`) |
| **Мониторинг обучения** | Вывод строчек текста в консоль | Логирование в TensorBoard + графики функций потерь и IoU в `outputs/` |
| **Оценка метрик** | Неструктурированный ручной вывод | Автоматический расчет IoU, Dice, Precision, Recall, Accuracy в JSON |

---

## 🚀 Быстрый старт

### 1. Клонирование репозитория

```bash
git clone https://github.com/Shoto373/Roads-and-Buildings-segment.git
cd Roads-and-Buildings-segment
```

### 2. Настройка виртуального окружения

```bash
# Создание виртуального окружения Python
python -m venv .venv

# Активация окружения (Windows PowerShell):
.\.venv\Scripts\Activate.ps1

# Активация окружения (Linux / macOS):
# source .venv/bin/activate

# Обновление менеджера пакетов и установка зависимостей
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> **Примечание по CUDA:** Для максимальной производительности на GPU NVIDIA убедитесь, что PyTorch установлен с поддержкой CUDA:
> ```bash
> pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
> ```

### 3. Загрузка данных (Massachusetts Dataset)

```bash
# Создание каталогов
mkdir -p notebooks/input

# Загрузка датасетов через Kaggle API
kaggle datasets download -d balraj98/massachusetts-roads-dataset -p notebooks/input/ --unzip
kaggle datasets download -d balraj98/massachusetts-buildings-dataset -p notebooks/input/ --unzip
```

Структура папок данных должна иметь следующий вид:
```text
notebooks/input/
├── massachusetts-roads-dataset/
│   └── tiff/
│       ├── train/          # 1108 снимков
│       ├── train_labels/   # 1108 масок
│       ├── val/            # 14 снимков
│       ├── val_labels/     # 14 масок
│       ├── test/           # 49 снимков
│       └── test_labels/    # 49 масок
└── massachusetts-buildings-dataset/
    └── tiff/ (train, val, test)
```

---

## 💻 Справочник команд CLI

<details open>
<summary><b>🔍 1. Инференс и визуализация (<code>inference.py</code>)</b></summary>

```bash
# 1. Сегментация дорог: генерация 10 примеров сопоставления на тестовом наборе
python inference.py --task road --weights weights/road_model_30_epochs.pth --num-examples 10

# 2. Инференс дорог с активацией TTA (повышенная точность на сложных участках)
python inference.py --task road --weights weights/road_model_30_epochs.pth --tta --num-examples 10

# 3. Инференс на вашем собственном аэрофотоснимке произвольного разрешения
python inference.py --task road --weights weights/road_model_30_epochs.pth --input-image my_aerial_photo.png

# 4. Сегментация контуров зданий (2 примера)
python inference.py --task building --weights weights/building_model_30_epochs.pth --num-examples 2
```

**Таблица параметров `inference.py`:**
| Параметр | Тип | По умолчанию | Описание |
| :--- | :---: | :---: | :--- |
| `--task` | `str` | `road` | Тип задачи сегментации: `road` или `building` |
| `--weights` | `str` | `None` | Путь к файлу весов модели (`.pth`). По умолчанию берется стандартный путь |
| `--input-image` | `str` | `None` | Путь к одиночному файлу изображения для инференса |
| `--num-examples`| `int` | `5` | Количество примеров из тестового набора для визуализации |
| `--tta` | `flag` | `False` | Включить режим Test-Time Augmentation (усреднение отражений) |
| `--device` | `str` | `cuda` | Вычислительное устройство (`cuda` или `cpu`) |
| `--output-dir` | `str` | `outputs` | Директория для сохранения полученных масок и триплетов |

</details>

<details>
<summary><b>🏋️ 2. Обучение моделей (<code>train.py</code>)</b></summary>

```bash
# Обучение модели сегментации дорог (Combo Loss, AMP, 40 эпох)
python train.py --task road --epochs 40 --batch-size 4 --loss combo

# Обучение модели сегментации зданий
python train.py --task building --epochs 40 --batch-size 4 --loss combo

# Мониторинг процесса обучения в реальном времени через веб-интерфейс
tensorboard --logdir runs
```

**Таблица параметров `train.py`:**
| Параметр | Тип | По умолчанию | Описание |
| :--- | :---: | :---: | :--- |
| `--task` | `str` | `road` | Задача: `road` или `building` |
| `--epochs` | `int` | `30` | Количество эпох обучения |
| `--batch-size` | `int` | `8` | Размер мини-батча (для GPU 8 ГБ рекомендуется `4`) |
| `--lr` | `float` | `1e-4` | Начальный шаг обучения оптимизатора Adam |
| `--loss` | `str` | `combo` | Функция потерь: `combo`, `dice`, `focal`, `bce` |
| `--decoder` | `str` | `Unet` | Архитектура декодера: `Unet`, `UnetPlusPlus`, `DeepLabV3Plus` |
| `--patience` | `int` | `7` | Число эпох без улучшений до остановки Early Stopping |
| `--no-amp` | `flag` | `False` | Отключение режима автоматической смешанной точности (AMP) |

</details>

<details>
<summary><b>📊 3. Оценка тестовых метрик (<code>evaluate.py</code>)</b></summary>

```bash
# Полный расчет метрик по 49 тестовым снимкам дорог
python evaluate.py --task road

# Оценка дорог с включенным TTA
python evaluate.py --task road --tta

# Оценка модели зданий по тестовой выборке
python evaluate.py --task building
```

> Результаты расчета выводятся в консоль в виде сводной таблицы и автоматически экспортируются в `outputs/<task>_test_metrics.json`.

</details>

---

## 📈 Количественные метрики

Результаты тестирования моделей на официальных тестовых выборках датасетов Massachusetts:

| Метрика качества | 🛣️ Сегментация дорог (Roads, 49 снимков) | 🏢 Сегментация зданий (Buildings, 10 снимков) |
| :--- | :---: | :---: |
| **IoU (Intersection over Union)** | **0.4872 ± 0.0603** | **0.6039 ± 0.0351** |
| **Dice Coefficient (F1-Score)** | **0.6528 ± 0.0582** | **0.7524 ± 0.0273** |
| **Precision (Точность)** | **0.5704 ± 0.0492** | **0.7908 ± 0.0268** |
| **Recall (Полнота)** | **0.7730 ± 0.0991** | **0.7187 ± 0.0385** |
| **Pixel Accuracy** | **0.9626 ± 0.0209** | **0.9143 ± 0.0340** |
| **Время инференса (NVIDIA RTX 3060)** | **~240 мс / снимок** | **~240 мс / снимок** |
| **Время инференса (CPU Intel Core i5)** | **~3.2 с / снимок** | **~3.2 с / снимок** |

### Графики сходимости обучения (Сегментация дорог)

<p align="center">
  <img src="outputs/road_iou_score_plot.png" width="48%" alt="IoU Score Progression">
  <img src="outputs/road_loss_plot.png" width="48%" alt="Loss Curve Progression">
</p>

---

## 🖼️ Галерея работы модели

В каждом примере представлены:
1. **Исходный аэрофотоснимок** (Original Aerial Image)
2. **Эталонная ручная разметка** (Ground Truth Mask)
3. **Предсказание нейросети** (Model Prediction)

### 🛣️ Сегментация дорожной сети (10 примеров)

<p align="center">
  <b>Пример 1: Городские магистрали и сложные перекрестки</b><br/>
  <img src="outputs/road_example_1.png" width="95%" alt="Дороги - Пример 1">
</p>

<p align="center">
  <b>Пример 2: Скоростное шоссе и транспортная развязка</b><br/>
  <img src="outputs/road_example_2.png" width="95%" alt="Дороги - Пример 2">
</p>

<p align="center">
  <b>Пример 3: Плотная ортогональная сетка городских кварталов</b><br/>
  <img src="outputs/road_example_3.png" width="95%" alt="Дороги - Пример 3">
</p>

<details>
<summary><b>Развернуть остальные 7 примеров дорог (Примеры 4–10)</b></summary>
<br/>

<p align="center">
  <b>Пример 4: Дорожная сеть жилых массивов и тупиковых проездов</b><br/>
  <img src="outputs/road_example_4.png" width="95%" alt="Дороги - Пример 4">
</p>

<p align="center">
  <b>Пример 5: Загородные трассы и извилистые лесные участки</b><br/>
  <img src="outputs/road_example_5.png" width="95%" alt="Дороги - Пример 5">
</p>

<p align="center">
  <b>Пример 6: Промзона и подъездные пути к логистическим терминалам</b><br/>
  <img src="outputs/road_example_6.png" width="95%" alt="Дороги - Пример 6">
</p>

<p align="center">
  <b>Пример 7: Сельские грунтовые дороги и открытый ландшафт</b><br/>
  <img src="outputs/road_example_7.png" width="95%" alt="Дороги - Пример 7">
</p>

<p align="center">
  <b>Пример 8: Пригородные коттеджные поселки со сложным рельефом</b><br/>
  <img src="outputs/road_example_8.png" width="95%" alt="Дороги - Пример 8">
</p>

<p align="center">
  <b>Пример 9: Побережье, мостовые переходы и набережные</b><br/>
  <img src="outputs/road_example_9.png" width="95%" alt="Дороги - Пример 9">
</p>

<p align="center">
  <b>Пример 10: Многоуровневые эстакады и скоростные развязки</b><br/>
  <img src="outputs/road_example_10.png" width="95%" alt="Дороги - Пример 10">
</p>

</details>

---

### 🏢 Сегментация зданий (2 примера)

<p align="center">
  <b>Пример 1: Малоэтажная и коттеджная жилая застройка</b><br/>
  <img src="outputs/building_example_1.png" width="95%" alt="Здания - Пример 1">
</p>

<p align="center">
  <b>Пример 2: Высотная городская застройка и коммерческие объекты</b><br/>
  <img src="outputs/building_example_2.png" width="95%" alt="Здания - Пример 2">
</p>

---

## 🛰️ Требования к входным снимкам

Для корректной работы сервиса на пользовательских данных рекомендуется соблюдать следующие технические условия:

| Параметр | Рекомендуемое значение | Допустимый диапазон | Комментарий / Рекомендации |
| :--- | :---: | :---: | :--- |
| **GSD (масштаб на пиксель)** | **1.0 м/пикс** | **0.5 – 1.5 м/пикс** | При GSD 1.0 м стандартная полоса (3.5 м) занимает ~3.5 пикселя |
| **Снимки с БПЛА / Дронов** | 0.05–0.15 м/пикс | *Требует сжатия* | **Обязательно даунскейлить в 5–10 раз**, иначе полотно дороги выглядит как открытое поле |
| **Спутники (Sentinel / Landsat)** | 10–30 м/пикс | *Непригодно* | Дорога тоньше одного пикселя, сегментация невозможна |
| **Размер в пикселях** | 1500 × 1500 px | Любой (авто-паддинг) | При снимках >3000×3000 px нарезать на тайлы 1500×1500 с нахлестом 64 px |
| **Цветовой формат** | RGB (24-bit) | 3 канала | При наличии альфа-канала (RGBA) четвертый канал автоматически отсекается |
| **Форматы файлов** | `.png`, `.jpg`, `.tif` | Стандартные растры | Поддерживаются любые форматы, открываемые библиотеками PIL/OpenCV |

---

## ⚙️ Системные требования

| Компонент | Минимальные требования | Рекомендуемая конфигурация |
| :--- | :--- | :--- |
| **Операционная система** | Windows 10/11 (64-bit) / Linux Ubuntu 20.04+ | Windows 11 / Ubuntu 22.04 LTS |
| **Процессор (CPU)** | 4 ядра, 2.5 ГГц (Intel Core i5 / AMD Ryzen 5) | 8 ядер, 3.5+ ГГц (Intel Core i7 / AMD Ryzen 7) |
| **Оперативная память (RAM)** | 8 ГБ | 16–32 ГБ |
| **Видеокарта (GPU)** | NVIDIA GPU 4 ГБ VRAM (с поддержкой CUDA) | NVIDIA GeForce RTX 3060 / 4070 (8–12 ГБ VRAM) |
| **Дисковое пространство** | 10 ГБ свободного места | 30 ГБ (SSD NVMe для быстрой загрузки тайлов) |
| **Среда Python** | Python 3.10 – 3.14 | Python 3.11 или 3.12, PyTorch 2.x CUDA 12.1 |

---

## 📂 Структура репозитория

```text
├── config.py                 # Единый конфигурационный модуль и CLI-парсер
├── train.py                  # Модуль обучения моделей (Combo Loss, AMP, Early Stopping)
├── inference.py              # Модуль инференса (пакетный, одиночный, TTA, произвольные фото)
├── evaluate.py               # Расчет тестовых метрик (IoU, Dice, Precision, Recall, Acc) в JSON
├── create_docx.py            # Автоматический генератор итогового Word-отчета (.docx)
├── create_changes_docx.py    # Автоматический генератор отчета об изменениях (.docx)
├── requirements.txt          # Список зависимостей Python
├── outputs/                  # Графики обучения, маски, сопоставления и JSON-файлы метрик
├── reports/                  # Итоговые инженерные отчеты проекта (.md и .docx)
├── notebooks/                # Экспериментальные ноутбуки и входные датасеты (gitignored)
└── weights/                  # Веса обученных нейросетей (.pth, gitignored)
```

---

## 📄 Отчетные материалы

В директории [`reports/`](reports/) сформированы детальные инженерные документы:
- **Итоговый технический отчет:** [`reports/Отчет_по_проекту.md`](reports/Отчет_по_проекту.md) и [`reports/Отчет_по_проекту_Итоговый.docx`](reports/Отчет_по_проекту_Итоговый.docx)
- **Отчет о рефакторинге кодовой базы:** [`reports/Отчет_Изменения.md`](reports/Отчет_Изменения.md) и [`reports/Отчет_Изменения.docx`](reports/Отчет_Изменения.docx)

Для обновления отчетов после изменения метрик или кода запустите:
```bash
python create_docx.py
python create_changes_docx.py
```

---

<div align="center">

Разработано для высокоточной сегментации дорожной инфраструктуры и геоинформационного анализа.  
⭐ Поставьте звезду репозиторию, если проект оказался полезен!

</div>
