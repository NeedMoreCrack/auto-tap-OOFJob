from pathlib import Path

import importlib
import re
import subprocess
import sys


# =========================================================
# 基本路徑
# =========================================================

SCRIPT_DIR = Path(__file__).resolve().parent

REQUIREMENTS_PATH = (
    SCRIPT_DIR
    / "requirements.txt"
)

REPORT_PATH = (
    SCRIPT_DIR
    / "report.py"
)


# =========================================================
# 套件名稱對應
# =========================================================

PACKAGE_IMPORT_MAPPING = {
    "PyYAML": "yaml",
    "playwright": "playwright",
    "selenium": "selenium",
    "pandas": "pandas",
    "plotly": "plotly",
    "streamlit": "streamlit",
}


# =========================================================
# requirements.txt
# =========================================================

def read_requirements():
    """
    讀取 requirements.txt。

    忽略：
        - 空白行
        - # 註解
    """

    if not REQUIREMENTS_PATH.exists():

        raise RuntimeError(
            f"找不到 requirements.txt："
            f"{REQUIREMENTS_PATH}"
        )

    requirements = []

    with open(
            REQUIREMENTS_PATH,
            "r",
            encoding="utf-8"
    ) as file:

        for raw_line in file:

            line = raw_line.strip()

            if not line:
                continue

            if line.startswith("#"):
                continue

            requirements.append(
                line
            )

    return requirements


# =========================================================
# 套件名稱解析
# =========================================================

def get_package_name(requirement):
    """
    從 requirements 格式取出套件名稱。

    支援：

        pandas
        pandas==2.3.0
        pandas>=2.0
        plotly~=6.0
        streamlit[extras]

    回傳：

        pandas
        plotly
        streamlit
    """

    package_name = requirement.strip()

    # 移除 environment marker
    package_name = package_name.split(
        ";",
        1
    )[0].strip()

    # 移除 extras
    package_name = re.split(
        r"\[",
        package_name,
        maxsplit=1
    )[0]

    # 移除版本條件
    package_name = re.split(
        r"(==|>=|<=|~=|!=|>|<)",
        package_name,
        maxsplit=1
    )[0]

    return package_name.strip()


# =========================================================
# 套件檢查
# =========================================================

def get_import_name(
        requirement
):
    package_name = get_package_name(
        requirement
    )

    return PACKAGE_IMPORT_MAPPING.get(
        package_name,
        package_name
    )


def is_package_installed(
        requirement
):
    """
    嘗試 import 套件判斷是否已安裝。
    """

    import_name = get_import_name(
        requirement
    )

    try:

        importlib.import_module(
            import_name
        )

        return True

    except ImportError:

        return False


# =========================================================
# 自動安裝
# =========================================================

def ensure_requirements():
    """
    requirements.txt 中缺少的套件才會安裝。
    """

    requirements = read_requirements()

    missing_packages = []

    print(
        "=" * 100
    )

    print(
        "檢查 Python 套件"
    )

    print(
        "=" * 100
    )

    for requirement in requirements:

        package_name = get_package_name(
            requirement
        )

        if is_package_installed(
                requirement
        ):

            print(
                f"[OK] {package_name}"
            )

        else:

            print(
                f"[缺少] {package_name}"
            )

            missing_packages.append(
                requirement
            )

    if not missing_packages:

        print()
        print(
            "所有必要套件皆已安裝。"
        )

        return

    print()
    print(
        "開始安裝缺少的套件..."
    )

    print()

    for requirement in missing_packages:

        print(
            f"安裝：{requirement}"
        )

        try:

            subprocess.check_call(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    requirement
                ]
            )

        except subprocess.CalledProcessError as e:

            raise RuntimeError(
                f"套件安裝失敗："
                f"{requirement}"
            ) from e

        print(
            f"安裝完成：{requirement}"
        )

        print()

    # -----------------------------------------------------
    # 再驗證一次
    # -----------------------------------------------------

    failed_packages = []

    for requirement in missing_packages:

        if not is_package_installed(
                requirement
        ):

            failed_packages.append(
                requirement
            )

    if failed_packages:

        raise RuntimeError(
            "以下套件安裝完成後仍無法 import："
            + ", ".join(
                failed_packages
            )
        )

    print(
        "所有套件安裝完成。"
    )


# =========================================================
# report.py 檢查
# =========================================================

def check_report_file():
    if not REPORT_PATH.exists():

        raise RuntimeError(
            f"找不到 report.py："
            f"{REPORT_PATH}"
        )


# =========================================================
# 啟動 Streamlit
# =========================================================

def start_streamlit():
    """
    使用目前 Python 環境啟動 Streamlit。

    等同：

        python -m streamlit run report.py
    """

    print()

    print(
        "=" * 100
    )

    print(
        "啟動職缺分析 Dashboard"
    )

    print(
        "=" * 100
    )

    print(
        f"Report：{REPORT_PATH}"
    )

    print()

    try:

        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(
                    REPORT_PATH
                ),
            ],
            cwd=str(
                SCRIPT_DIR
            ),
            check=True
        )

    except KeyboardInterrupt:

        print()
        print(
            "Dashboard 已停止。"
        )

    except subprocess.CalledProcessError as e:

        raise RuntimeError(
            "Streamlit 啟動失敗。"
        ) from e


# =========================================================
# MAIN
# =========================================================

def main():
    try:

        check_report_file()

        ensure_requirements()

        start_streamlit()

    except Exception as e:

        print()
        print(
            "=" * 100
        )

        print(
            "啟動失敗"
        )

        print(
            "=" * 100
        )

        print(
            f"{type(e).__name__}: {e}"
        )

        sys.exit(
            1
        )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    main()