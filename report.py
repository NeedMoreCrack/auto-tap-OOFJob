from pathlib import Path

import re

import pandas as pd
import plotly.express as px
import streamlit as st
import yaml


# =========================================================
# Streamlit 頁面設定
# =========================================================

st.set_page_config(
    page_title="職缺分析",
    page_icon="📊",
    layout="wide",
)


# =========================================================
# 基本路徑
# =========================================================

SCRIPT_DIR = Path(__file__).resolve().parent

CONFIG_PATH = (
        SCRIPT_DIR
        / "config.yaml"
)

LOG_DIR = (
        SCRIPT_DIR
        / "log"
)


# =========================================================
# 預設設定
# =========================================================

DEFAULT_CONFIG = {
    "technology_top_n": 20,
    "district_top_n": 20,
    "duplicate_top_n": 20,
    "ignore_technologies": [
        "",
        "未取得",
        "提升專業能力",
    ],
}


# =========================================================
# 設定檔
# =========================================================

def load_config():
    """
    讀取 config.yaml 中的 report 設定。

    找不到設定或設定值不合法時，
    對應欄位使用預設值。
    """

    config = (
        DEFAULT_CONFIG.copy()
    )

    config[
        "ignore_technologies"
    ] = (
        DEFAULT_CONFIG[
            "ignore_technologies"
        ].copy()
    )

    if not CONFIG_PATH.exists():

        return config

    try:

        with open(
                CONFIG_PATH,
                "r",
                encoding="utf-8"
        ) as file:

            loaded = yaml.safe_load(
                file
            )

    except Exception:

        return config

    if loaded is None:

        return config

    if not isinstance(
            loaded,
            dict
    ):

        return config

    report_config = (
        loaded.get(
            "report",
            {}
        )
    )

    if report_config is None:

        report_config = {}

    if not isinstance(
            report_config,
            dict
    ):

        return config

    integer_settings = [
        "technology_top_n",
        "district_top_n",
        "duplicate_top_n",
    ]

    for key in integer_settings:

        value = (
            report_config.get(
                key,
                config[key]
            )
        )

        if (
                isinstance(
                    value,
                    int
                )
                and not isinstance(
            value,
            bool
        )
                and value > 0
        ):

            config[key] = value

    value = (
        report_config.get(
            "ignore_technologies",
            config[
                "ignore_technologies"
            ]
        )
    )

    if (
            isinstance(
                value,
                list
            )
            and all(
        isinstance(
            item,
            str
        )
        for item
        in value
    )
    ):

        config[
            "ignore_technologies"
        ] = value

    return config


CONFIG = load_config()


TECHNOLOGY_TOP_N = (
    CONFIG[
        "technology_top_n"
    ]
)

DISTRICT_TOP_N = (
    CONFIG[
        "district_top_n"
    ]
)

DUPLICATE_TOP_N = (
    CONFIG[
        "duplicate_top_n"
    ]
)

TECHNOLOGY_IGNORE_LIST = set(
    CONFIG[
        "ignore_technologies"
    ]
)


# =========================================================
# LOG 欄位
# =========================================================

FIELD_MAPPING = {
    "職缺編號": "job_no",
    "職缺名稱": "job_name",
    "工作地點": "location",
    "需要技術": "technologies",
    "學歷限制": "education",
    "薪資範圍": "salary",
    "職缺網址": "href",
    "狀態": "status",
    "錯誤": "error",
}


# =========================================================
# 通用文字處理
# =========================================================

def clean_value(
        value
):
    if value is None:

        return ""

    return value.strip()


def clean_url(
        value
):
    value = clean_value(
        value
    )

    markdown_match = re.match(
        r"\[.*?]\((https?://.*?)\)",
        value
    )

    if markdown_match:

        return (
            markdown_match
            .group(1)
            .replace(
                "\\_",
                "_"
            )
        )

    return value.replace(
        "\\_",
        "_"
    )


# =========================================================
# LOG Parser
# =========================================================

def parse_log_file(
        log_path
):
    jobs = []

    current_job = None

    try:

        with open(
                log_path,
                "r",
                encoding="utf-8"
        ) as file:

            for raw_line in file:

                line = raw_line.strip()

                if not line:

                    continue

                if (
                        len(line) >= 20
                        and set(line) == {"="}
                ):

                    continue

                for (
                        chinese_name,
                        field_name
                ) in FIELD_MAPPING.items():

                    prefix = (
                            chinese_name
                            + "："
                    )

                    if not line.startswith(
                            prefix
                    ):

                        continue

                    value = clean_value(
                        line[
                            len(prefix):
                        ]
                    )

                    if field_name == "job_no":

                        if current_job is not None:

                            jobs.append(
                                current_job
                            )

                        current_job = {
                            "job_no": value,
                            "job_name": "",
                            "location": "",
                            "technologies": "",
                            "education": "",
                            "salary": "",
                            "href": "",
                            "status": "成功",
                            "error": "",
                            "source_log":
                                log_path.name,
                        }

                    elif current_job is not None:

                        if field_name == "href":

                            current_job[
                                field_name
                            ] = clean_url(
                                value
                            )

                        else:

                            current_job[
                                field_name
                            ] = value

                    break

        if current_job is not None:

            jobs.append(
                current_job
            )

    except Exception as e:

        st.warning(
            f"解析 {log_path.name} 失敗："
            f"{type(e).__name__}: {e}"
        )

    return jobs


@st.cache_data(
    show_spinner=False
)
def parse_logs(
        log_file_paths
):
    all_jobs = []

    for path_string in log_file_paths:

        log_path = Path(
            path_string
        )

        jobs = parse_log_file(
            log_path
        )

        all_jobs.extend(
            jobs
        )

    return all_jobs


# =========================================================
# 地點解析
# =========================================================

TAIWAN_CITIES = [
    "台北市",
    "新北市",
    "桃園市",
    "台中市",
    "台南市",
    "高雄市",
    "基隆市",
    "新竹市",
    "嘉義市",
    "新竹縣",
    "苗栗縣",
    "彰化縣",
    "南投縣",
    "雲林縣",
    "嘉義縣",
    "屏東縣",
    "宜蘭縣",
    "花蓮縣",
    "台東縣",
    "澎湖縣",
    "金門縣",
    "連江縣",
]


CITY_PATTERN = re.compile(
    "("
    + "|".join(
        map(
            re.escape,
            TAIWAN_CITIES
        )
    )
    + ")"
)


def extract_city(
        location
):
    if not location:

        return "未取得"

    match = CITY_PATTERN.search(
        location
    )

    if match:

        return match.group(
            1
        )

    return "其他"


def extract_district(
        location
):
    if not location:

        return "未取得"

    city = extract_city(
        location
    )

    remaining_location = (
        location
    )

    if (
            city
            and city not in {
        "未取得",
        "其他",
    }
    ):

        remaining_location = (
            location.replace(
                city,
                "",
                1
            )
        )

    match = re.search(
        r"([\u4e00-\u9fff]{1,4}"
        r"(?:區|鄉|鎮|市))",
        remaining_location
    )

    if match:

        return match.group(
            1
        )

    return "其他"


# =========================================================
# 技術解析
# =========================================================

def parse_technologies(
        value
):
    if not value:

        return []

    parts = re.split(
        r"[、,，;/|]+",
        value
    )

    technologies = []

    seen = set()

    for part in parts:

        technology = (
            part.strip()
        )

        if not technology:

            continue

        if technology in TECHNOLOGY_IGNORE_LIST:

            continue

        normalized = (
            technology.lower()
        )

        if normalized in seen:

            continue

        seen.add(
            normalized
        )

        technologies.append(
            technology
        )

    return technologies


def get_technology_counts(
        df
):
    technology_counter = {}

    for value in df[
        "technologies"
    ]:

        technologies = (
            parse_technologies(
                value
            )
        )

        for technology in technologies:

            technology_counter[
                technology
            ] = (
                    technology_counter.get(
                        technology,
                        0
                    )
                    + 1
            )

    if not technology_counter:

        return pd.Series(
            dtype="int64"
        )

    return pd.Series(
        technology_counter,
        dtype="int64"
    ).sort_values(
        ascending=False
    )


def get_all_technologies(
        df
):
    technologies = set()

    for value in df[
        "technologies"
    ]:

        values = parse_technologies(
            value
        )

        technologies.update(
            values
        )

    return sorted(
        technologies,
        key=str.lower
    )


# =========================================================
# 學歷解析
# =========================================================

def normalize_education(
        value
):
    if not value:

        return "未取得"

    value = value.strip()

    if value == "未取得":

        return "未取得"

    if "不拘" in value:

        return "不拘"

    if "博士" in value:

        return "博士"

    if (
            "碩士" in value
            and "大學" not in value
    ):

        return "碩士"

    if "大學" in value:

        return "大學"

    if "專科" in value:

        return "專科"

    if (
            "高中" in value
            or "高職" in value
    ):

        return "高中 / 高職"

    if "國中" in value:

        return "國中"

    return value


# =========================================================
# 薪資解析
# =========================================================

def parse_number_text(
        text
):
    if not text:

        return None

    text = (
        text
        .replace(
            ",",
            ""
        )
        .replace(
            " ",
            ""
        )
    )

    wan_match = re.search(
        r"(\d+(?:\.\d+)?)萬",
        text
    )

    if wan_match:

        return int(
            float(
                wan_match.group(
                    1
                )
            )
            * 10000
        )

    number_match = re.search(
        r"\d+(?:\.\d+)?",
        text
    )

    if not number_match:

        return None

    return int(
        float(
            number_match.group()
        )
    )


def classify_salary(
        value
):
    if not value:

        return "未取得"

    if value == "未取得":

        return "未取得"

    if "待遇面議" in value:

        return "待遇面議"

    if "月薪" in value:

        return "月薪"

    if "年薪" in value:

        return "年薪"

    if "時薪" in value:

        return "時薪"

    if "日薪" in value:

        return "日薪"

    if "論件" in value:

        return "論件計酬"

    return "其他"


def extract_salary_numbers(
        value
):
    salary_type = classify_salary(
        value
    )

    if salary_type == "待遇面議":

        return (
            None,
            None
        )

    if salary_type not in {
        "月薪",
        "年薪",
        "時薪",
        "日薪",
    }:

        return (
            None,
            None
        )

    value_without_type = re.sub(
        r"^(月薪|年薪|時薪|日薪)",
        "",
        value
    )

    number_texts = re.findall(
        r"\d+(?:,\d{3})*(?:\.\d+)?\s*萬?"
        r"|\d+(?:\.\d+)?\s*萬",
        value_without_type
    )

    parsed_numbers = []

    for number_text in number_texts:

        number = parse_number_text(
            number_text
        )

        if number is not None:

            parsed_numbers.append(
                number
            )

    if not parsed_numbers:

        return (
            None,
            None
        )

    if len(parsed_numbers) == 1:

        return (
            parsed_numbers[0],
            None
        )

    return (
        parsed_numbers[0],
        parsed_numbers[1]
    )


def salary_bucket(
        salary_type,
        salary_min
):
    if salary_type != "月薪":

        return None

    if salary_min is None:

        return None

    if salary_min < 40000:

        return "40K 以下"

    if salary_min < 50000:

        return "40K ~ 50K"

    if salary_min < 60000:

        return "50K ~ 60K"

    if salary_min < 70000:

        return "60K ~ 70K"

    if salary_min < 80000:

        return "70K ~ 80K"

    if salary_min < 100000:

        return "80K ~ 100K"

    return "100K+"


# =========================================================
# DataFrame
# =========================================================

def create_dataframe(
        jobs
):
    df = pd.DataFrame(
        jobs
    )

    if df.empty:

        return df

    df[
        "city"
    ] = df[
        "location"
    ].apply(
        extract_city
    )

    df[
        "district"
    ] = df[
        "location"
    ].apply(
        extract_district
    )

    df[
        "education_normalized"
    ] = df[
        "education"
    ].apply(
        normalize_education
    )

    df[
        "salary_type"
    ] = df[
        "salary"
    ].apply(
        classify_salary
    )

    salary_numbers = (
        df[
            "salary"
        ].apply(
            extract_salary_numbers
        )
    )

    df[
        "salary_min"
    ] = salary_numbers.apply(
        lambda item:
        item[0]
    )

    df[
        "salary_max"
    ] = salary_numbers.apply(
        lambda item:
        item[1]
    )

    df[
        "salary_bucket"
    ] = df.apply(
        lambda row:
        salary_bucket(
            row[
                "salary_type"
            ],
            row[
                "salary_min"
            ]
        ),
        axis=1
    )

    return df


def get_unique_job_dataframe(
        df
):
    return (
        df.drop_duplicates(
            subset=[
                "job_no"
            ],
            keep="last"
        )
        .copy()
    )


# =========================================================
# LOG 選擇
# =========================================================

def get_available_log_files():
    if not LOG_DIR.exists():

        return []

    return sorted(
        LOG_DIR.glob(
            "*.log"
        ),
        key=lambda path:
        path.name,
        reverse=True
    )


def render_log_selector():
    log_files = (
        get_available_log_files()
    )

    if not log_files:

        st.error(
            f"找不到任何 LOG："
            f"{LOG_DIR}"
        )

        st.stop()

    file_name_mapping = {
        log_file.name:
            log_file
        for log_file
        in log_files
    }

    st.sidebar.subheader(
        "分析來源"
    )

    analyze_all = (
        st.sidebar.checkbox(
            "分析全部 LOG",
            value=True
        )
    )

    if analyze_all:

        selected_names = list(
            file_name_mapping.keys()
        )

        st.sidebar.caption(
            f"已選擇全部 "
            f"{len(selected_names)} "
            f"個 LOG"
        )

    else:

        selected_names = (
            st.sidebar.multiselect(
                "選擇 LOG",
                options=list(
                    file_name_mapping.keys()
                ),
                default=[],
                placeholder=(
                    "選擇一個或多個 LOG"
                )
            )
        )

    if not selected_names:

        st.warning(
            "請至少選擇一個 LOG。"
        )

        st.stop()

    return [
        file_name_mapping[
            file_name
        ]
        for file_name
        in selected_names
    ]


# =========================================================
# Sidebar 篩選
# =========================================================

def render_filters(
        df
):
    st.sidebar.divider()

    st.sidebar.subheader(
        "篩選條件"
    )

    city_options = sorted(
        [
            value
            for value
            in df[
            "city"
        ]
        .dropna()
        .unique()
            if value
        ]
    )

    selected_cities = (
        st.sidebar.multiselect(
            "城市",
            options=
            city_options,
            placeholder=
            "全部城市"
        )
    )

    district_source_df = df

    if selected_cities:

        district_source_df = (
            df[
                df[
                    "city"
                ].isin(
                    selected_cities
                )
            ]
        )

    district_options = sorted(
        [
            value
            for value
            in district_source_df[
            "district"
        ]
        .dropna()
        .unique()
            if value not in {
            "",
            "其他",
            "未取得",
        }
        ]
    )

    selected_districts = (
        st.sidebar.multiselect(
            "行政區",
            options=
            district_options,
            placeholder=
            "全部行政區"
        )
    )

    education_options = sorted(
        [
            value
            for value
            in df[
            "education_normalized"
        ]
        .dropna()
        .unique()
            if value
        ]
    )

    selected_education = (
        st.sidebar.multiselect(
            "學歷要求",
            options=
            education_options,
            placeholder=
            "全部學歷"
        )
    )

    salary_type_options = sorted(
        [
            value
            for value
            in df[
            "salary_type"
        ]
        .dropna()
        .unique()
            if value
        ]
    )

    selected_salary_types = (
        st.sidebar.multiselect(
            "薪資類型",
            options=
            salary_type_options,
            placeholder=
            "全部薪資類型"
        )
    )

    technology_options = (
        get_all_technologies(
            df
        )
    )

    selected_technologies = (
        st.sidebar.multiselect(
            "技術",
            options=
            technology_options,
            placeholder=(
                "例如 Java、"
                "Python、AWS"
            )
        )
    )

    technology_match_mode = (
        st.sidebar.radio(
            "技術匹配模式",
            options=[
                "任一符合",
                "全部符合",
            ],
            horizontal=True,
            disabled=(
                    len(
                        selected_technologies
                    )
                    <= 1
            )
        )
    )

    minimum_monthly_salary = (
        st.sidebar.selectbox(
            "最低月薪",
            options=[
                0,
                40000,
                50000,
                60000,
                70000,
                80000,
                100000,
            ],
            format_func=lambda value:
            (
                "不限"
                if value == 0
                else (
                    f"{value // 1000}K+"
                )
            )
        )
    )

    return {
        "selected_cities":
            selected_cities,

        "selected_districts":
            selected_districts,

        "selected_education":
            selected_education,

        "selected_salary_types":
            selected_salary_types,

        "selected_technologies":
            selected_technologies,

        "technology_match_mode":
            technology_match_mode,

        "minimum_monthly_salary":
            minimum_monthly_salary,
    }


# =========================================================
# 套用篩選
# =========================================================

def apply_filters(
        df,
        selected_cities,
        selected_districts,
        selected_education,
        selected_salary_types,
        selected_technologies,
        technology_match_mode,
        minimum_monthly_salary
):
    filtered_df = (
        df.copy()
    )

    if selected_cities:

        filtered_df = (
            filtered_df[
                filtered_df[
                    "city"
                ].isin(
                    selected_cities
                )
            ]
        )

    if selected_districts:

        filtered_df = (
            filtered_df[
                filtered_df[
                    "district"
                ].isin(
                    selected_districts
                )
            ]
        )

    if selected_education:

        filtered_df = (
            filtered_df[
                filtered_df[
                    "education_normalized"
                ].isin(
                    selected_education
                )
            ]
        )

    if selected_salary_types:

        filtered_df = (
            filtered_df[
                filtered_df[
                    "salary_type"
                ].isin(
                    selected_salary_types
                )
            ]
        )

    if selected_technologies:

        selected_normalized = {
            technology.lower()
            for technology
            in selected_technologies
        }

        def match_technology(
                value
        ):
            job_technologies = {
                technology.lower()
                for technology
                in parse_technologies(
                    value
                )
            }

            if (
                    technology_match_mode
                    == "全部符合"
            ):

                return (
                    selected_normalized
                    .issubset(
                        job_technologies
                    )
                )

            return bool(
                job_technologies
                & selected_normalized
            )

        filtered_df = (
            filtered_df[
                filtered_df[
                    "technologies"
                ].apply(
                    match_technology
                )
            ]
        )

    if minimum_monthly_salary > 0:

        filtered_df = (
            filtered_df[
                (
                        filtered_df[
                            "salary_type"
                        ]
                        == "月薪"
                )
                &
                (
                        filtered_df[
                            "salary_min"
                        ].fillna(
                            0
                        )
                        >=
                        minimum_monthly_salary
                )
                ]
        )

    return filtered_df


# =========================================================
# KPI
# =========================================================

def format_salary_k(
        value
):
    if (
            value is None
            or pd.isna(
        value
    )
    ):

        return "-"

    return (
        f"{value / 1000:.1f}K"
    )


def render_kpis(
        filtered_df
):
    total_jobs = len(
        filtered_df
    )

    negotiable_count = (
        filtered_df[
            "salary_type"
        ]
        .eq(
            "待遇面議"
        )
        .sum()
    )

    monthly_df = (
        filtered_df[
            (
                    filtered_df[
                        "salary_type"
                    ]
                    == "月薪"
            )
            &
            (
                filtered_df[
                    "salary_min"
                ].notna()
            )
            ]
    )

    explicit_monthly_count = (
        len(
            monthly_df
        )
    )

    negotiable_percentage = (
        negotiable_count
        / total_jobs
        * 100
        if total_jobs
        else 0
    )

    average_minimum_salary = (
        monthly_df[
            "salary_min"
        ].mean()
        if not monthly_df.empty
        else None
    )

    col1, col2, col3, col4 = (
        st.columns(
            4
        )
    )

    col1.metric(
        "職缺數",
        f"{total_jobs:,}"
    )

    col2.metric(
        "待遇面議",
        f"{negotiable_percentage:.1f}%"
    )

    col3.metric(
        "明確月薪",
        f"{explicit_monthly_count:,}"
    )

    col4.metric(
        "平均最低月薪",
        format_salary_k(
            average_minimum_salary
        )
    )


# =========================================================
# Plotly 共用
# =========================================================

def apply_common_chart_layout(
        fig,
        height=430
):
    fig.update_layout(
        height=height,

        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20
        ),

        legend_title_text="",
    )

    return fig


# =========================================================
# 城市
# =========================================================

def create_city_chart(
        df
):
    data = (
        df[
            "city"
        ]
        .value_counts()
        .rename_axis(
            "城市"
        )
        .reset_index(
            name="職缺數"
        )
    )

    if data.empty:

        return None

    fig = px.bar(
        data,
        x="城市",
        y="職缺數",
        text="職缺數",
        title="職缺城市分布"
    )

    fig.update_traces(
        textposition="outside",
        cliponaxis=False
    )

    return (
        apply_common_chart_layout(
            fig
        )
    )


# =========================================================
# 行政區
# =========================================================

def create_district_chart(
        df
):
    data = (
        df[
            "district"
        ]
        .replace(
            {
                "其他":
                    pd.NA,

                "未取得":
                    pd.NA,
            }
        )
        .dropna()
        .value_counts()
        .head(
            DISTRICT_TOP_N
        )
        .sort_values(
            ascending=True
        )
        .rename_axis(
            "行政區"
        )
        .reset_index(
            name="職缺數"
        )
    )

    if data.empty:

        return None

    fig = px.bar(
        data,
        x="職缺數",
        y="行政區",
        orientation="h",
        text="職缺數",
        title=(
            f"行政區職缺排行 "
            f"Top {DISTRICT_TOP_N}"
        )
    )

    fig.update_traces(
        textposition="outside",
        cliponaxis=False
    )

    height = max(
        430,
        len(data) * 32
    )

    return (
        apply_common_chart_layout(
            fig,
            height
        )
    )


# =========================================================
# 學歷
# =========================================================

def create_education_chart(
        df
):
    data = (
        df[
            "education_normalized"
        ]
        .value_counts()
        .rename_axis(
            "學歷"
        )
        .reset_index(
            name="職缺數"
        )
    )

    if data.empty:

        return None

    fig = px.pie(
        data,
        names="學歷",
        values="職缺數",
        hole=0.55,
        title="學歷要求分布"
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent+label"
    )

    return (
        apply_common_chart_layout(
            fig
        )
    )


# =========================================================
# 技術排行
# =========================================================

def create_technology_chart(
        df
):
    counts = (
        get_technology_counts(
            df
        )
        .head(
            TECHNOLOGY_TOP_N
        )
        .sort_values(
            ascending=True
        )
    )

    if counts.empty:

        return None

    data = (
        counts
        .rename_axis(
            "技術"
        )
        .reset_index(
            name="職缺數"
        )
    )

    fig = px.bar(
        data,
        x="職缺數",
        y="技術",
        orientation="h",
        text="職缺數",
        title=(
            f"職缺技術需求 "
            f"Top {TECHNOLOGY_TOP_N}"
        )
    )

    fig.update_traces(
        textposition="outside",
        cliponaxis=False
    )

    height = max(
        500,
        len(data) * 32
    )

    return (
        apply_common_chart_layout(
            fig,
            height
        )
    )


# =========================================================
# 薪資類型
# =========================================================

def create_salary_type_chart(
        df
):
    data = (
        df[
            "salary_type"
        ]
        .value_counts()
        .rename_axis(
            "薪資類型"
        )
        .reset_index(
            name="職缺數"
        )
    )

    if data.empty:

        return None

    fig = px.pie(
        data,
        names="薪資類型",
        values="職缺數",
        hole=0.55,
        title="薪資揭露類型"
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent+label"
    )

    return (
        apply_common_chart_layout(
            fig
        )
    )


# =========================================================
# 月薪區間
# =========================================================

def create_monthly_salary_chart(
        df
):
    order = [
        "40K 以下",
        "40K ~ 50K",
        "50K ~ 60K",
        "60K ~ 70K",
        "70K ~ 80K",
        "80K ~ 100K",
        "100K+",
    ]

    monthly_df = (
        df[
            df[
                "salary_type"
            ]
            == "月薪"
            ]
    )

    data = (
        monthly_df[
            "salary_bucket"
        ]
        .dropna()
        .value_counts()
        .reindex(
            order,
            fill_value=0
        )
        .rename_axis(
            "薪資區間"
        )
        .reset_index(
            name="職缺數"
        )
    )

    data = (
        data[
            data[
                "職缺數"
            ] > 0
            ]
    )

    if data.empty:

        return None

    fig = px.bar(
        data,
        x="薪資區間",
        y="職缺數",
        text="職缺數",
        title=(
            "明確月薪職缺－"
            "最低薪資區間"
        ),
        category_orders={
            "薪資區間":
                order
        }
    )

    fig.update_traces(
        textposition="outside",
        cliponaxis=False
    )

    return (
        apply_common_chart_layout(
            fig
        )
    )


# =========================================================
# 重複職缺
# =========================================================

def create_duplicate_chart(
        raw_df
):
    counts = (
        raw_df[
            "job_no"
        ]
        .value_counts()
    )

    counts = (
        counts[
            counts > 1
            ]
    )

    if counts.empty:

        return None

    records = []

    for job_no, count in (
            counts
                    .head(
                DUPLICATE_TOP_N
            )
                    .items()
    ):

        matched = (
            raw_df[
                raw_df[
                    "job_no"
                ]
                == job_no
                ]
        )

        if matched.empty:

            continue

        job_name = (
            matched
            .iloc[0][
                "job_name"
            ]
        )

        if not job_name:

            job_name = job_no

        if len(job_name) > 40:

            job_name = (
                    job_name[:40]
                    + "..."
            )

        records.append(
            {
                "職缺":
                    job_name,

                "職缺編號":
                    job_no,

                "出現次數":
                    count,
            }
        )

    if not records:

        return None

    data = (
        pd.DataFrame(
            records
        )
        .sort_values(
            "出現次數",
            ascending=True
        )
    )

    fig = px.bar(
        data,
        x="出現次數",
        y="職缺",
        orientation="h",
        text="出現次數",
        hover_data=[
            "職缺編號"
        ],
        title=(
            f"重複出現職缺 "
            f"Top {DUPLICATE_TOP_N}"
        )
    )

    fig.update_traces(
        textposition="outside",
        cliponaxis=False
    )

    height = max(
        450,
        len(data) * 40
    )

    return (
        apply_common_chart_layout(
            fig,
            height
        )
    )


# =========================================================
# Chart Render
# =========================================================

def render_chart(
        fig,
        key
):
    if fig is None:

        st.info(
            "目前沒有足夠資料。"
        )

        return

    st.plotly_chart(
        fig,
        width="stretch",
        key=key
    )


# =========================================================
# 明細
# =========================================================

def render_job_table(
        df
):
    st.subheader(
        "職缺明細"
    )

    display_df = (
        df[
            [
                "job_no",
                "job_name",
                "city",
                "district",
                "technologies",
                "education",
                "salary",
                "href",
            ]
        ].copy()
    )

    display_df.columns = [
        "職缺編號",
        "職缺名稱",
        "城市",
        "行政區",
        "需要技術",
        "學歷限制",
        "薪資範圍",
        "職缺網址",
    ]

    st.dataframe(
        display_df,
        width="stretch",
        height=600,
        hide_index=True,

        column_config={
            "職缺網址":
                st.column_config.LinkColumn(
                    "職缺網址",
                    display_text=
                    "開啟 求職網"
                ),
        }
    )


# =========================================================
# CSV
# =========================================================

def render_download_button(
        df
):
    csv_data = (
        df.to_csv(
            index=False
        )
        .encode(
            "utf-8-sig"
        )
    )

    st.download_button(
        "下載目前篩選結果 CSV",
        data=csv_data,
        file_name=
        "jobs_analysis.csv",
        mime=
        "text/csv"
    )


# =========================================================
# Dashboard
# =========================================================

def render_dashboard(
        raw_df,
        unique_df
):
    filters = render_filters(
        unique_df
    )

    filtered_df = apply_filters(
        unique_df,
        **filters
    )

    st.title(
        "職缺市場分析"
    )

    if filtered_df.empty:

        st.warning(
            "目前篩選條件沒有符合的職缺。"
        )

        return

    render_kpis(
        filtered_df
    )

    st.divider()

    col1, col2 = (
        st.columns(
            2
        )
    )

    with col1:

        render_chart(
            create_city_chart(
                filtered_df
            ),
            "city_chart"
        )

    with col2:

        render_chart(
            create_education_chart(
                filtered_df
            ),
            "education_chart"
        )

    col1, col2 = (
        st.columns(
            2
        )
    )

    with col1:

        render_chart(
            create_salary_type_chart(
                filtered_df
            ),
            "salary_type_chart"
        )

    with col2:

        render_chart(
            create_monthly_salary_chart(
                filtered_df
            ),
            "monthly_salary_chart"
        )

    st.divider()

    render_chart(
        create_technology_chart(
            filtered_df
        ),
        "technology_chart"
    )

    st.divider()

    render_chart(
        create_district_chart(
            filtered_df
        ),
        "district_chart"
    )

    st.divider()

    st.subheader(
        "重複刊登分析"
    )

    render_chart(
        create_duplicate_chart(
            raw_df
        ),
        "duplicate_chart"
    )

    st.divider()

    render_job_table(
        filtered_df
    )

    render_download_button(
        filtered_df
    )


# =========================================================
# MAIN
# =========================================================

def main():
    st.sidebar.title(
        "職缺分析"
    )

    selected_log_files = (
        render_log_selector()
    )

    selected_paths = tuple(
        str(
            path.resolve()
        )
        for path
        in selected_log_files
    )

    with st.spinner(
            "正在解析 LOG..."
    ):

        jobs = parse_logs(
            selected_paths
        )

    if not jobs:

        st.error(
            "沒有解析到任何職缺。"
        )

        st.stop()

    raw_df = create_dataframe(
        jobs
    )

    unique_df = (
        get_unique_job_dataframe(
            raw_df
        )
    )

    st.sidebar.divider()

    st.sidebar.caption(
        f"LOG："
        f"{len(selected_log_files):,} 個"
    )

    st.sidebar.caption(
        f"總紀錄："
        f"{len(raw_df):,} 筆"
    )

    st.sidebar.caption(
        f"不重複職缺："
        f"{len(unique_df):,} 筆"
    )

    st.sidebar.caption(
        f"重複紀錄："
        f"{len(raw_df) - len(unique_df):,} 筆"
    )

    render_dashboard(
        raw_df,
        unique_df
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    main()
